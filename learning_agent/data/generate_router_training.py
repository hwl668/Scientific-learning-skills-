#!/usr/bin/env python3
"""Generate router training data for the learning-agent skill classifier.

The generated dataset is synthetic but grounded in the project's existing
labels and public course-topic taxonomies. It is intended for router model
training, not as a replacement for human-reviewed eval cases.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "learning_agent"
    / "resources"
    / "data"
    / "training"
    / "router_training_v0.3.jsonl"
)


@dataclass(frozen=True)
class Topic:
    subject: str
    topic: str
    simple: str
    pair: str
    problem: str
    mistake: str
    prerequisite: str
    difficulty: str = "undergraduate"


TOPICS: tuple[Topic, ...] = (
    Topic("calculus", "极限", "极限", "极限和函数值", "求 lim(x→0)(sin x)/x", "把极限值当成函数值", "函数与趋近"),
    Topic("calculus", "导数", "导数", "导数和变化率", "求 f(x)=x^3 在 x=2 的导数", "把割线斜率当成切线斜率", "函数图像"),
    Topic("calculus", "积分", "定积分", "面积和累积量", "计算 ∫_0^1 x^2 dx", "忘记积分上下限含义", "求和与面积"),
    Topic("calculus", "泰勒公式", "泰勒展开", "泰勒展开和等价无穷小", "求 lim(x→0)(e^x-1-x)/x^2", "展开阶数不够", "多项式近似"),
    Topic("calculus", "级数", "无穷级数", "收敛和发散", "判断 ∑1/n^2 是否收敛", "把项趋近 0 当成级数收敛", "数列极限"),
    Topic("calculus", "多元函数偏导", "偏导数", "偏导和全导", "求 z=x^2y 在 (1,2) 的偏导", "把另一个变量也一起变了", "一元导数"),
    Topic("linear_algebra", "矩阵乘法", "矩阵乘法", "行乘列和线性变换复合", "计算 AB 并解释维度条件", "矩阵乘法顺序写反", "向量与坐标"),
    Topic("linear_algebra", "向量空间", "向量空间", "集合和空间", "判断多项式集合是否构成向量空间", "漏检查数乘封闭", "集合与运算"),
    Topic("linear_algebra", "线性变换", "线性变换", "矩阵和线性变换", "证明 T(x+y)=T(x)+T(y)", "把任意函数都当线性变换", "函数映射"),
    Topic("linear_algebra", "秩与零空间", "矩阵的秩", "列空间和零空间", "求 A 的 rank 和 nullity", "把行数当成秩", "线性方程组"),
    Topic("linear_algebra", "特征值", "特征值和特征向量", "特征值和对角化", "求 [[2,0],[0,3]] 的特征值", "把特征向量算成零向量", "矩阵乘向量"),
    Topic("linear_algebra", "基变换", "基变换", "坐标和向量本身", "求向量在新基下的坐标", "把基向量顺序写反", "线性组合"),
    Topic("probability_statistics", "条件概率", "条件概率", "P(A|B) 和 P(B|A)", "计算抽到红球后来自哪个箱子的概率", "把条件写反", "集合概率"),
    Topic("probability_statistics", "贝叶斯公式", "贝叶斯公式", "先验和后验", "用贝叶斯公式更新概率", "忽略全概率分母", "条件概率"),
    Topic("probability_statistics", "概率密度", "概率密度函数", "概率密度和概率", "求连续变量落在区间的概率", "把某点密度当概率", "积分"),
    Topic("probability_statistics", "期望方差", "期望和方差", "平均值和波动", "计算离散随机变量的期望", "把 E(X^2) 写成 E(X)^2", "随机变量"),
    Topic("probability_statistics", "假设检验", "p 值", "p 值和显著性水平", "判断一次检验是否拒绝原假设", "把 p 值当原假设为真的概率", "抽样分布"),
    Topic("probability_statistics", "中心极限定理", "中心极限定理", "大数定律和中心极限定理", "判断样本均值近似分布", "样本量不够也硬套正态", "期望方差"),
    Topic("algorithms", "Dijkstra", "Dijkstra 算法", "Dijkstra 和 Bellman-Ford", "求带权图从 s 到各点最短路", "在负权边上使用 Dijkstra", "图和优先队列"),
    Topic("algorithms", "KMP", "KMP next 数组", "前缀函数和 next 数组", "手算模式串 ababaca 的 next", "next 数组下标偏移搞错", "字符串匹配"),
    Topic("algorithms", "并查集", "并查集", "路径压缩和按秩合并", "判断一组边是否形成连通分量", "find 后忘记路径压缩", "树结构"),
    Topic("algorithms", "动态规划", "动态规划", "DP 和贪心", "求最长递增子序列长度", "状态定义不清", "递推关系"),
    Topic("algorithms", "贪心算法", "贪心", "局部最优和全局最优", "判断区间调度能否贪心", "没证明交换论证", "排序与选择"),
    Topic("algorithms", "图遍历", "BFS 和 DFS", "BFS 和 DFS", "判断网格最短步数该用什么", "用 DFS 求无权最短路", "图结构"),
    Topic("csapp", "Cache", "Cache", "时间局部性和空间局部性", "判断一段循环的 cache miss", "把 block offset 和 set index 搞反", "二进制地址"),
    Topic("csapp", "CPI", "CPI", "CPI 和 GIPS", "根据 CPI 和频率估算运行时间", "单位换算漏掉 10^9", "处理器周期"),
    Topic("csapp", "虚拟内存", "虚拟内存", "虚拟地址和物理地址", "手算页号和页内偏移", "把页号当物理地址", "地址空间"),
    Topic("csapp", "机器级程序", "汇编寄存器", "寄存器和内存", "读一段 mov/add 指令含义", "把地址和地址里的值混淆", "C 指针"),
    Topic("csapp", "链接", "链接与重定位", "静态链接和动态链接", "判断符号解析结果", "把声明当定义", "编译流程"),
    Topic("operating_systems", "进程线程", "进程和线程", "进程和线程", "判断多线程共享哪些资源", "把线程当独立地址空间", "程序执行"),
    Topic("operating_systems", "死锁", "死锁", "死锁和饥饿", "判断资源分配图是否死锁", "只看一个条件就判死锁", "锁和资源"),
    Topic("operating_systems", "调度", "进程调度", "周转时间和响应时间", "计算 FCFS/SJF 的平均等待时间", "把等待时间和周转时间混淆", "队列"),
    Topic("operating_systems", "分页", "分页机制", "页表和 TLB", "计算虚拟地址翻译过程", "忽略 TLB miss 后查页表", "内存地址"),
    Topic("computer_networks", "TCP UDP", "TCP 和 UDP", "可靠传输和无连接", "判断视频通话适合 TCP 还是 UDP", "把 UDP 当成一定不可靠不能用", "端口和报文"),
    Topic("computer_networks", "拥塞控制", "TCP 拥塞控制", "拥塞控制和流量控制", "解释慢启动窗口变化", "把 rwnd 和 cwnd 混在一起", "TCP 连接"),
    Topic("computer_networks", "DNS", "DNS 查询", "递归查询和迭代查询", "画出域名解析流程", "把本地 DNS 和根 DNS 作用混淆", "IP 地址"),
    Topic("computer_networks", "HTTP", "HTTP 状态码", "GET 和 POST", "分析一次 HTTP 请求响应", "把 301 和 302 混用", "客户端服务器"),
    Topic("machine_learning", "softmax", "softmax", "softmax 和 sigmoid", "计算三个 logits 的 softmax", "以为 softmax 改变排序", "指数函数"),
    Topic("machine_learning", "交叉熵", "交叉熵损失", "交叉熵和 MSE", "判断分类任务该用什么 loss", "把 loss 小当准确率一定高", "概率分布"),
    Topic("machine_learning", "梯度下降", "梯度下降", "学习率和梯度", "分析学习率过大的现象", "把梯度方向当上升方向", "导数"),
    Topic("machine_learning", "batch size", "batch size", "batch size 和学习率", "判断 batch size 变大对训练的影响", "只看显存不看泛化", "随机梯度"),
    Topic("machine_learning", "过拟合", "过拟合", "训练误差和测试误差", "判断曲线是否过拟合", "只加大模型不看验证集", "模型评估"),
    Topic("machine_learning", "ResNet", "残差连接", "残差连接和恒等映射", "解释残差块为什么帮助训练", "把残差当简单拼接", "神经网络层"),
    Topic("signals_systems", "傅里叶变换", "傅里叶变换", "时域和频域", "判断一个信号的频率成分", "把频谱峰值当时间位置", "三角函数"),
    Topic("signals_systems", "卷积", "卷积", "卷积和乘法", "手算两个短序列的卷积", "翻转平移步骤搞错", "函数与序列"),
    Topic("signals_systems", "拉普拉斯变换", "拉普拉斯变换", "拉普拉斯和傅里叶", "求简单系统传递函数", "忽略收敛域", "复数"),
    Topic("automatic_control", "反馈控制", "负反馈", "负反馈和正反馈", "解释温控系统为什么稳定", "把反馈都当成延迟", "系统输出"),
    Topic("automatic_control", "PID", "PID 控制", "P、I、D 三项作用", "判断超调该调哪个参数", "只背 P/I/D 不会调参", "误差函数"),
    Topic("automatic_control", "稳定性", "系统稳定性", "极点和稳定性", "判断一阶系统是否稳定", "只看增益不看极点", "微分方程"),
    Topic("circuits", "KCL KVL", "KCL 和 KVL", "节点电流和回路电压", "列节点电压方程", "电流方向假设变了就慌", "电压电流"),
    Topic("circuits", "运放", "运放虚短虚断", "虚短和虚断", "分析反相放大器增益", "把虚短当真的短路", "电路模型"),
    Topic("circuits", "RC 电路", "RC 暂态", "时间常数和稳态", "求电容充电曲线", "初始条件忘记连续性", "微分方程"),
    Topic("physics", "牛顿定律", "牛顿第二定律", "力和加速度", "分析斜面上物体受力", "把速度方向当合力方向", "向量分解"),
    Topic("physics", "能量守恒", "机械能守恒", "功和能量", "判断滑块是否能到达最高点", "有摩擦还硬套机械能守恒", "功"),
    Topic("physics", "电磁感应", "法拉第电磁感应", "磁通量和感应电动势", "判断线圈中感应电流方向", "楞次定律方向判断反了", "磁场"),
    Topic("mathematical_modeling", "变量约束", "变量、目标函数和约束", "变量和参数", "把排班问题建模成整数规划", "把约束写成目标函数", "函数建模"),
    Topic("mathematical_modeling", "优化模型", "优化目标", "目标函数和评价指标", "给配送问题设计目标函数", "目标太多没有主次", "线性规划"),
    Topic("research_competition", "读论文", "读论文", "摘要和贡献", "给一篇论文拆贡献和方法", "从头翻译到尾不抓问题", "学术论文结构"),
    Topic("research_competition", "复现 baseline", "复现 baseline", "baseline 和 proposed method", "制定 baseline 复现步骤", "没固定数据划分就比较结果", "实验设置"),
    Topic("research_competition", "消融实验", "消融实验", "消融和对比实验", "设计模块消融表", "一次改多个变量", "控制变量"),
)


DIAGNOSIS_BY_LABEL = {
    "zero-base-learning": "missing_prerequisite",
    "fuzzy-understanding": "formula_without_understanding",
    "deepening-learning": "concept_confusion",
    "problem-solving": "derivation_gap",
    "mistake-review": "concept_confusion",
    "study-plan-builder": "missing_prerequisite",
}


TEMPLATES: dict[str, tuple[tuple[str, str], ...]] = {
    "zero-base-learning": (
        ("{simple}是什么？我第一次接触，想先知道它解决什么问题。", "zero"),
        ("从零讲一下{simple}，不要一上来就给公式。", "zero"),
        ("我完全没学过{topic}，能不能用直觉解释一下？", "zero"),
        ("刚开始学{topic}，{simple}到底在研究什么？", "zero"),
    ),
    "fuzzy-understanding": (
        ("我学过{topic}，但{pair}总是分不清。", "concept_confusion"),
        ("{simple}我会算一点，但不知道它到底在干什么。", "formula_without_understanding"),
        ("老师讲到{simple}时我能跟着做，自己一换题就不会用了。", "rote_no_transfer"),
        ("我看得懂{topic}的例题，但不理解为什么可以这样做。", "formula_without_understanding"),
        ("{simple}相关符号一多我就懵，尤其是{pair}。", "symbol_not_understood"),
    ),
    "deepening-learning": (
        ("讲透{simple}的本质，别只给定义。", "concept_confusion"),
        ("为什么{simple}在{subject_cn}里这么重要？想从多个角度理解。", "concept_confusion"),
        ("{simple}背后的证明思路是什么？有没有反例能说明条件不能少？", "derivation_gap"),
        ("{topic}和{pair}之间有什么更深的联系？", "concept_confusion"),
        ("{simple}为什么不能随便套模板？想理解它的适用条件。", "rote_no_transfer"),
        ("为什么{simple}在某些条件下会失效？", "derivation_gap"),
        ("{simple}为什么可以成立？核心证明直觉是什么？", "derivation_gap"),
    ),
    "problem-solving": (
        ("这题怎么做：{problem}。我不知道第一步该想什么。", "derivation_gap"),
        ("我卡在一道{topic}题上，题目是：{problem}。求思路。", "derivation_gap"),
        ("帮我分析这道题的解题模型：{problem}。不要直接给答案。", "derivation_gap"),
        ("遇到{topic}题时怎么判断该用哪个方法？比如：{problem}。", "concept_confusion"),
    ),
    "mistake-review": (
        ("这题我做错了：{problem}，我可能是{mistake}，帮我复盘。", "concept_confusion"),
        ("我的答案和标准答案不一样，题目是{problem}，我想知道错因。", "concept_confusion"),
        ("错题复盘：{topic}这里我总是{mistake}，怎么避免？", "rote_no_transfer"),
        ("我以为{simple}题这样做就行，但答案说不对，可能哪里错了？", "concept_confusion"),
    ),
    "study-plan-builder": (
        ("我想两周内补{topic}，每天 1 小时，怎么安排？", "plan"),
        ("期末要考{topic}，我基础是{prerequisite}不太稳，给我排个复习计划。", "plan"),
        ("如果目标是能做{topic}的中等题，应该怎么学{simple}？", "plan"),
    ),
}


SUBJECT_CN = {
    "calculus": "高等数学",
    "linear_algebra": "线性代数",
    "probability_statistics": "概率统计",
    "algorithms": "算法",
    "csapp": "计算机系统",
    "operating_systems": "操作系统",
    "computer_networks": "计算机网络",
    "machine_learning": "机器学习",
    "signals_systems": "信号与系统",
    "automatic_control": "自动控制",
    "circuits": "电路",
    "physics": "大学物理",
    "mathematical_modeling": "数学建模",
    "research_competition": "科研竞赛",
}


WORD_CASES = (
    ("undermine", "underestimate"),
    ("meticulous", "careful"),
    ("resilient", "resistant"),
    ("ambiguous", "vague"),
    ("derive", "deduce"),
    ("assume", "presume"),
    ("constraint", "restriction"),
    ("objective", "goal"),
    ("significant", "important"),
    ("complementary", "complimentary"),
    ("robust", "stable"),
    ("subtle", "slight"),
    ("empirical", "experimental"),
    ("baseline", "benchmark"),
    ("ablation", "comparison"),
    ("converge", "approach"),
    ("diverge", "deviate"),
    ("approximate", "estimate"),
    ("rigorous", "strict"),
    ("criterion", "standard"),
    ("hypothesis", "assumption"),
    ("distribution", "allocation"),
    ("variance", "variation"),
    ("gradient", "slope"),
    ("residual", "remainder"),
    ("thread", "process"),
    ("cache", "buffer"),
    ("latency", "delay"),
    ("verify", "validate"),
    ("infer", "imply"),
)


TEXT_TOPICS = (
    "实践是检验真理的唯一标准，这是由真理的本性和实践的特点决定的",
    "新民主主义革命的总路线包括无产阶级领导、人民大众、反帝反封建",
    "TCP 拥塞控制包括慢启动、拥塞避免、快重传和快恢复",
    "操作系统死锁产生需要互斥、占有并等待、不可剥夺和循环等待四个条件",
    "机器学习中过拟合表现为训练误差低但测试误差高",
    "线性代数中基是一组线性无关并张成整个空间的向量",
    "电路中的基尔霍夫电流定律说明流入节点的电流代数和为零",
    "科研论文通常包括问题、方法、实验、结果和局限性",
    "马克思主义认为矛盾具有普遍性和特殊性，二者是辩证统一的关系",
    "中国近代史的主线包括民族独立、人民解放、国家富强和人民幸福",
    "数据库事务的 ACID 特性包括原子性、一致性、隔离性和持久性",
    "编译过程通常包括词法分析、语法分析、语义分析、中间代码生成、优化和目标代码生成",
    "神经网络训练通常包括前向传播、损失计算、反向传播和参数更新",
    "概率论中的随机变量是把随机试验结果映射为数值的函数",
    "自动控制系统通常由被控对象、控制器、反馈通道和给定输入组成",
    "软件工程中的单元测试关注函数级行为，集成测试关注模块协作",
    "线性规划模型通常包括决策变量、目标函数、约束条件和非负条件",
    "科研选题需要同时考虑问题价值、可行性、创新点和评价方式",
)


NON_LEARNING_CASES = (
    "你是什么模型？",
    "你是什么 LLM？",
    "你是 goose agent 吗？",
    "这个平台为什么登录后对话失败？",
    "Request failed: No endpoints found that support image input 是什么意思？",
    "这个入口需要付费或者 credits 吗？",
    "帮我写一封邮件问对方平台怎么接入 skill。",
    "GitHub bio 怎么写？",
    "这个 issue 要不要回复？",
    "怎么邀请别人加入 organization？",
    "帮我润色这段项目介绍。",
    "把这段中文翻译成英文。",
    "这个 socialistic.ai 是框架还是服务器？",
    "我想知道 creator 收 token 是怎么结算的。",
    "这个仓库现在有没有未提交文件？",
    "你能看到我上传的图片吗？",
    "这个链接为什么打不开？",
    "帮我写一段 GitHub README 介绍。",
    "这个项目要不要加 LICENSE？",
    "怎么回复别人发来的 issue？",
    "你现在能不能联网搜索？",
    "这个页面的 UI 是用什么框架做的？",
    "如果 creator 收 token，钱到谁的钱包？",
    "帮我把这句话说得没那么正式。",
    "我想邀请他进组织，消息怎么写自然一点？",
    "当前分支推到 GitHub 了吗？",
    "这个功能是不是应该先别 push？",
    "帮我检查一下仓库状态。",
    "你能把这个文件复制到 home 目录吗？",
    "这个 socialistic 入口算官方的吗？",
    "模型 endpoint 不支持 image input 怎么办？",
    "我用 GitHub 登录才成功，这是平台 bug 吗？",
    "这个在线入口背后是不是 OpenRouter？",
    "这个 creator 钱包是什么意思？",
    "帮我写一个不太正式的微信回复。",
    "这句话英文怎么说更自然？",
    "帮我起一个 GitHub repo 名字。",
    "这个文件应该提交吗？",
    "刚才那个 commit hash 是多少？",
    "你能不能帮我查一下网页用了什么技术栈？",
    "这个 Vercel 响应头说明什么？",
    "OpenRouter 的 deepseek-flash 是什么定位？",
    "qwen3-vl-32b-instruct 支持图片吗？",
    "怎么跟别人说先保持免费？",
    "这个在线入口要不要写进 README？",
    "这段 issue 回复会不会太冲？",
    "帮我把邮件语气放软一点。",
    "这个链接是别人发的推广吗？",
    "怎么判断对方是不是批量爬开源项目？",
    "这个 UI 看起来像 Tailwind 吗？",
    "登录状态丢了会导致 401 吗？",
    "这是不是他们后端的 endpoint 配错了？",
    "你觉得这个合作要不要继续？",
    "给我写一个简短的 bio。",
    "CS learner · Agent developer 这句可以吗？",
    "帮我检查英文语法。",
    "这段 Markdown 表格怎么排版？",
    "我想把本地文件复制到另一个目录。",
    "运行 git status 看一下。",
    "这个模型训练要不要 push？",
    "数据集文件要不要单独 commit？",
    "我想知道现在有哪些未跟踪文件。",
    "别查了，先停下。",
    "这个命令为什么需要权限？",
    "pip install 成功了吗？",
    "scikit-learn 版本是多少？",
    "这个报错是 solver 不支持多分类吗？",
    "帮我解释一下 macro-F1。",
    "这个 accuracy 会不会虚高？",
    "训练报告保存在哪里？",
    "模型文件能不能直接上传？",
    "这个 artifact 要不要加入 git？",
    "怎么写 release note？",
    "这段话帮我改得像正常聊天。",
    "我要怎么邀请他加入组织？",
    "这个 creator 权限能不能转移？",
    "socialistic 是不是自己出 token？",
    "图片上传失败应该怎么跟用户解释？",
    "这个平台是不是 Next.js 做的？",
    "Vercel 和服务器有什么区别？",
    "这个 issue 先不要关可以吗？",
    "帮我总结一下刚才的对话。",
    "把这些上下文压缩一下。",
    "现在项目算什么水平？",
    "这能写进简历吗？",
    "实习一般做什么？",
    "下一步工程优化点是什么？",
    "这个训练路线怎么安排？",
    "现在先别 push。",
    "先看一下文件结构。",
    "帮我写中文，不要太正式。",
    "把版权问题先别提。",
    "这个链接需要登录才能看吗？",
    "DeepSeek 分享页能抓到吗？",
    "ChatGPT 项目链接能直接读取吗？",
)


def _format(template: str, topic: Topic) -> str:
    return template.format(
        subject_cn=SUBJECT_CN.get(topic.subject, topic.subject),
        subject=topic.subject,
        topic=topic.topic,
        simple=topic.simple,
        pair=topic.pair,
        problem=topic.problem,
        mistake=topic.mistake,
        prerequisite=topic.prerequisite,
    )


def _record(
    idx: int,
    text: str,
    label: str,
    category: str,
    *,
    subject: str = "general",
    topic: str = "",
    diagnosis: str | None = None,
    difficulty: str = "undergraduate",
    source: str = "synthetic_topic_template",
    hard_negative: bool = False,
    review_required: bool = False,
) -> dict:
    return {
        "id": f"router-train-v03-{idx:04d}",
        "text": text,
        "label": label,
        "category": category,
        "subject": subject,
        "topic": topic,
        "diagnosis": diagnosis,
        "difficulty": difficulty,
        "source": source,
        "quality": "silver",
        "hard_negative": hard_negative,
        "review_required": review_required,
    }


def generate_records() -> list[dict]:
    records: list[dict] = []
    seen: set[str] = set()

    def add(text: str, label: str, category: str, **kwargs) -> None:
        normalized = text.strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        records.append(_record(len(records) + 1, normalized, label, category, **kwargs))

    for topic in TOPICS:
        for label, templates in TEMPLATES.items():
            for template, category in templates:
                diagnosis = category if category in {
                    "concept_confusion",
                    "symbol_not_understood",
                    "derivation_gap",
                    "missing_prerequisite",
                    "rote_no_transfer",
                    "formula_without_understanding",
                } else DIAGNOSIS_BY_LABEL.get(label)
                add(
                    _format(template, topic),
                    label,
                    category,
                    subject=topic.subject,
                    topic=topic.topic,
                    diagnosis=diagnosis,
                    difficulty=topic.difficulty,
                    source="synthetic_from_public_course_topic",
                )

        # Hard negatives around common router boundaries.
        add(
            f"{topic.simple}是什么？我不是要做题，只想先入门。",
            "zero-base-learning",
            "zero",
            subject=topic.subject,
            topic=topic.topic,
            diagnosis="missing_prerequisite",
            source="synthetic_hard_negative",
            hard_negative=True,
        )
        add(
            f"我会做{topic.simple}的基本题，但{topic.pair}还是分不清。",
            "fuzzy-understanding",
            "concept_confusion",
            subject=topic.subject,
            topic=topic.topic,
            diagnosis="concept_confusion",
            source="synthetic_hard_negative",
            hard_negative=True,
        )
        add(
            f"{topic.problem}，这是我错题里的题，我的错误是{topic.mistake}。",
            "mistake-review",
            "mistake",
            subject=topic.subject,
            topic=topic.topic,
            diagnosis="concept_confusion",
            source="synthetic_hard_negative",
            hard_negative=True,
        )
        add(
            f"为什么{topic.simple}不能只靠背模板？我想理解适用条件。",
            "deepening-learning",
            "deep",
            subject=topic.subject,
            topic=topic.topic,
            diagnosis="rote_no_transfer",
            source="synthetic_hard_negative",
            hard_negative=True,
        )

    for word, comparison in WORD_CASES:
        add(f"{word}", "word-deep-dive", "word", subject="english", topic=word, source="synthetic_word_cases")
        add(f"!{word} 六级", "word-deep-dive", "word", subject="english", topic=word, source="synthetic_word_cases")
        add(f"查词：{word}", "word-deep-dive", "word", subject="english", topic=word, source="synthetic_word_cases")
        add(f"{word} 和 {comparison} 有什么区别？", "word-deep-dive", "word", subject="english", topic=word, source="synthetic_word_cases")
        add(f"{word} 这个词在考研阅读里怎么考？", "word-deep-dive", "word", subject="english", topic=word, source="synthetic_word_cases")

    for text in TEXT_TOPICS:
        short = text[:18]
        add(f"帮我背这段：{text}。", "text-memorizer", "text", subject="memorization", topic=short, source="synthetic_text_memory")
        add(f"针对这段出题抽背：{text}。", "text-memorizer", "text", subject="memorization", topic=short, source="synthetic_text_memory")
        add(f"关键词触发：{short}，帮我复习薄弱点。", "text-memorizer", "text", subject="memorization", topic=short, source="synthetic_text_memory")
        add(f"把这段整理成填空题和问答题：{text}。", "text-memorizer", "text", subject="memorization", topic=short, source="synthetic_text_memory")
        add(f"我需要默写这段：{text}。请帮我做梯度挖空。", "text-memorizer", "text", subject="memorization", topic=short, source="synthetic_text_memory")
        add(f"围绕这段材料出 5 道抽背题：{text}。", "text-memorizer", "text", subject="memorization", topic=short, source="synthetic_text_memory")
        add(f"这段我总背混：{text}。帮我列常见记忆误区。", "text-memorizer", "text", subject="memorization", topic=short, source="synthetic_text_memory")

    for text in NON_LEARNING_CASES:
        add(
            text,
            "non-learning",
            "out_of_scope",
            subject="platform",
            topic="non-learning request",
            diagnosis=None,
            difficulty="general",
            source="visible_conversation_or_platform_pattern",
            hard_negative=True,
        )

    return records


def validate_records(records: list[dict]) -> dict:
    texts = [record["text"] for record in records]
    duplicate_count = len(texts) - len(set(texts))
    return {
        "total": len(records),
        "duplicates": duplicate_count,
        "labels": dict(sorted(Counter(record["label"] for record in records).items())),
        "categories": dict(sorted(Counter(record["category"] for record in records).items())),
        "subjects": dict(sorted(Counter(record["subject"] for record in records).items())),
        "hard_negative": sum(1 for record in records if record["hard_negative"]),
        "review_required": sum(1 for record in records if record["review_required"]),
    }


def write_jsonl(records: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate router training JSONL.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="output JSONL path")
    parser.add_argument("--summary", action="store_true", help="print dataset summary")
    args = parser.parse_args(argv)

    records = generate_records()
    write_jsonl(records, Path(args.output))
    if args.summary:
        print(json.dumps(validate_records(records), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
