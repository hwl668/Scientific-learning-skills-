# Scientific Learning Skills

> Turns AI from answer machine into diagnostic tutor. Student-facing Agent Skills — diagnosis before explanation.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Platforms](https://img.shields.io/badge/Platform-Claude%20Code%20|%20Codex%20|%20OpenClaw%20|%20GPTs%20|%20Generic-lightgrey)]()
[![Try 诊断式学习 Agent on Socialistic](https://socialistic.ai/api/embed/scientific-learning-agent-a8f23b?lang=zh)](https://socialistic.ai/zh/skill/scientific-learning-agent-a8f23b?utm_source=github&utm_medium=readme&utm_campaign=20260601-gaokao-ai-study-workflows&utm_content=badge)

[Quick Start](#快速开始) · [Demo](./demo/) · [Eval](#快速开始) · [对比实测](#有它-vs-没有它) · [Platforms](#安装到其他平台) · [English](./README.en.md)

---

## 它能做什么

**查一个单词，它给你的不只是翻译：**

```
> !undermine 六级

📌 已存入记忆（新词，明天复习）

含义：1. 逐渐削弱（六级中频） 2. 挖墙脚
词根：under（在下面）+ mine（挖）→ 在底下挖 → 掏空根基
形近词陷阱：undermine vs underline vs underestimate
考试怎么考：六级选词填空经典辨析，阅读同义替换（= weaken）
常见误区：和 underestimate 混用——前者是破坏，后者是低估
备考建议：被动识别即可。行动：① 抄下形近词对比表 ② 做 3 道选词填空真题
```

**"我懂了但做题不会"——它先诊断再修：**

```
> 我会算矩阵乘法，但不知道矩阵到底在算什么。

诊断：你的卡点是"线性变换"这个前置概念没建立直觉。
你不是不会算——你是把矩阵当成了一个静态表格，而不是一个动作。

修复：矩阵的每一列 = 基向量被映射后的新位置。
[2 0; 0 3] → 把 x 拉伸 2 倍，y 拉伸 3 倍。
[0 -1; 1 0] → 把整个平面旋转 90°。

验证：矩阵 [0,-1; 1,0] 对正方形做了什么？
变式：换成 [1,1; 0,1]，预测效果。
```

**背政治大题，它拆成思维导图，然后抽背：**

```
> 帮我背这段：实践是检验真理的唯一标准……

思维导图：
实践是检验真理的唯一标准
├── 真理的本性：主观认识与客观实际相符合
├── 实践的特点：直接现实性（能把主观变客观）
└── 为什么唯一：只有实践能连接主客观

> 出题

🔁 抽背（3 题）
Q1: [填空] 实践是检验真理的____标准。
Q2: 为什么说实践是检验真理的唯一标准？
Q3: 关键词"直接现实性"→ 请复述相关要点。
```

**9 个 Skill，覆盖学习的完整闭环：**

| 你在想什么 | 自动触发 |
|-----------|---------|
| "我不想选，直接用一个大的学习入口" | `scientific-learning` — 总入口，先路由再调用子 skill |
| "完全没学过，这是什么" | `zero-base-learning` — 从直觉出发，不堆公式 |
| "学过但云里雾里" | `fuzzy-understanding` — 诊断卡点，只修裂口 |
| "已经懂了，想更深入" | `deepening-learning` — 多视角/反例/跨知识联系 |
| "这道题不会做" | `problem-solving` — 分步推演，不直接给答案 |
| "这道题我做错了" | `mistake-review` — 错因归类 + 检查清单 + 变式 |
| 一个英语单词 | `word-deep-dive` — 全息词典 + 间隔复习 |
| "帮我背这段" | `text-memorizer` — 拆分/导图/抽背/薄弱追踪 |
| "两个月怎么学完线代" | `study-plan-builder` — 拆阶段/排任务/设检测 |

---

## 有它 vs 没有它

同一个问题，裸 AI 和加载 Skill 后的 AI 回复完全不同：

**用户**：我会算矩阵乘法，但不知道矩阵到底表示什么。

<table>
<tr><th>裸 AI（无 Skill）</th><th>加载 fuzzy-understanding</th></tr>
<tr><td width="50%">

> 矩阵有三种理解方式：
> 1. 对空间的变换——当作一台机器，输入向量输出向量
> 2. 线性方程组的系数——行乘列来自代入消元
> 3. 矩阵的列 = 基向量被变换后的位置
>
> 一句话：矩阵是空间中的一个动作。

</td><td width="50%">

> 诊断：你怎么理解矩阵？先确认两件事——
> 1. 矩阵 [1,2; 3,4] 乘以向量 [x,y]，你觉得这到底在对 [x,y] 做什么？
> 2. 你学矩阵是从解方程组切入，还是几何，还是直接给运算规则？
>
> （等你回答后再针对性修复）

</td></tr>
</table>

**裸 AI 直接给了三个视角**——但用户真正缺的可能只是其中一个视角的直觉。三个一起给 = 认知过载。

**Skill 先追问两个诊断问题**——判断是「直觉缺失」还是「概念混淆」，然后只讲用户缺失的那一块。不讲用户已经懂的内容，不讲用户暂时不需要的内容。

---

### 定量对比

基于 `evals/scoring_rubric.md` 的 10 维度打分（`python eval.py --quick` 实测）：

| 维度 | 裸 AI | 加载 Skill | 差异 |
|------|-------|-----------|------|
| 是否诊断卡点 | 0 | 2 | **诊断先于讲解** |
| 是否有直觉解释 | 1 | 2 | 针对性类比 vs 通用举例 |
| 是否有例题 | 1 | 1 | 均有 |
| 是否有变式迁移 | 0 | 2 | **Skill 强制要求** |
| 是否指出常见误区 | 0 | 2 | **Skill P0 强制** |
| 是否简洁清晰 | 2 | 2 | 均清晰 |
| **总分** | **11/20** | **17/20** | **+6 分** |

> **核心差异**：裸 AI 假设用户需要全部信息——结果给了用户不需要的 80%。Skill 先判断用户在哪，只给用户需要的 20%。

---

## 快速开始

```bash
git clone https://github.com/hwl668/Scientific-learning-skills-.git
cd scientific-learning-skills
./setup.sh    # 自动检测 AI 工具 + 创建软链接 + 初始化 memory
claude        # 启动，Skills 自动加载
```

然后直接说话：

```text
> 什么是极限？我第一次接触。
> 我会算矩阵乘法，但不知道矩阵到底表示什么。
> !undermine 六级
```

想先看看效果？→ [`demo/`](./demo/) 目录有 3 个完整对话实录，不用安装就能浏览。

想验证质量？→ `python eval.py --quick` 本地跑规则评测：

```
fuzzy-understanding-matrix  17/20 PASS
zero-base-learning-limit    18/20 PASS
word-deep-dive-undermine    17/20 PASS  [word rubric]
```

## v0.2: Learning Agent Framework

v0.2 将项目从 Skill Pack 升级为可运行的 Learning Agent Framework。Skill 仍然负责教学行为，框架模块负责路由、诊断、记忆调度、评测、部署编译和标准案例管理。

| 模块 | 作用 | 命令 |
|------|------|------|
| Skill Router | 将用户学习问题路由到合适的 skill | `python -m learning_agent.router "我会算矩阵乘法，但不知道矩阵到底表示什么"` |
| Cognitive Diagnosis | 识别 6 类学习卡点 | `python -m learning_agent.diagnosis "矩阵乘法我会算，但不知道为什么要行乘列"` |
| Memory Scheduler | 用 SM-2 风格算法计算间隔、掌握概率、遗忘风险、复习优先级 | `python -m learning_agent.memory.scheduler '{"id":"limit","correct_streak":2,"interval_days":6}' --quality 5 --json` |
| Eval Runner | 运行 demo / JSONL suite，输出 text、JSON 或 Markdown 报告 | `python -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report markdown` |
| Prompt Compiler | 按平台、skill 选择和 token budget 生成 system prompt | `python -m learning_agent.compile --target codex --skills fuzzy,problem,word --output prompt.md --metadata` |
| Subject Case Library | 管理大学专业课、算法、机器学习、系统课、建模和科研竞赛案例 | `python -m learning_agent.subjects --summary` |

核心数据集：

| 数据集 | 用途 |
|--------|------|
| `data/routing_cases.jsonl` | Router 标注评估 |
| `data/diagnosis_cases.jsonl` | 认知卡点诊断评估 |
| `data/subject_cases.jsonl` | 学科/科研场景覆盖 |
| `evals/cases/smoke.jsonl` | Eval Runner JSONL smoke suite |

当前回归验证：

```bash
python -B -m unittest discover -s tests
python -B -m learning_agent.router --eval
python -B -m learning_agent.diagnosis --eval
python -B eval.py --quick
python -B -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report json
```

更多 v0.2 设计和验证说明见 [`docs/v0.2-summary.md`](./docs/v0.2-summary.md)。

## 安装到其他平台

Skills 本质是结构化 Markdown 指令集，不依赖特定平台。将 RULES.md + skills/ 合成为系统提示注入即可。

| 平台 | 部署方式 | 说明 |
|------|---------|------|
| Claude Code | `.claude/skills/` 自动加载 | [详细说明](./deploy/claude-code.md) |
| OpenAI Codex / GPTs | 合成为 system message | [详细说明](./deploy/codex.md) |
| OpenClaw / OI | Skills 目录或系统提示 | [详细说明](./deploy/openclaw.md) |
| Cursor / Cline / Copilot | 规则文件或自定义指令 | [详细说明](./deploy/generic.md) |
| 任意智能体 | 系统提示注入 | [详细说明](./deploy/generic.md) |

Token 预算：全部 9 个 Skill 约 20K-30K tokens。可按需只加载总入口或 2-3 个子 skill。

### Memory 支持矩阵

不同平台对 Memory（间隔复习、薄弱追踪）的支持程度：

| 平台 | Memory 支持 | 说明 |
|------|-----------|------|
| Claude Code | 完整 | 原生文件系统读写 |
| Cursor / Cline | 有限 | 项目目录可写 |
| OpenClaw | 取决于运行时 | 需确认文件系统权限 |
| ChatGPT / GPTs | 无 | 需 Function Calling 连接外部存储 |
| Codex / API | 无 | 需外部存储 API |

无 Memory 的平台仍可使用全部诊断/讲解/解题能力，仅间隔复习功能不可用。

---

## 使用

不需要手动选 Skill，自然描述问题就行：

```text
# 零基础入门
> 什么是导数？我第一次接触。

# 模糊诊断
> 我会算极限，但不理解 ε-N 定义到底在干什么。

# 解题
> 求 lim(x→0) (e^x - 1 - x) / x²，我卡住了。

# 错题复盘
> f(x)=ln(x²-1)，我求定义域答了 x>1，答案却是 x<-1 或 x>1。

# 单词（加 ! 存入记忆，支持间隔复习）
> !complimentary 六级

# 背文本（存入后说"出题"开始抽背）
> 帮我背这段：实践是检验真理的唯一标准……

# 复习计划
> 两个月自学线代通过期末考，每天 1.5 小时，基础只会矩阵乘法。
```

也可以显式调用总入口：

```text
> /scientific-learning 矩阵乘法是什么？
> 用 scientific-learning 帮我处理这个学习问题：这题我卡住了……
```

**记忆管理：**

```text
> 复习单词         # 按间隔复习法抽取到期词汇
> 出题             # text-memorizer 抽背薄弱知识点
> 学习报告         # 跨 Skill 薄弱点汇总 + 掌握率 + 建议
> 清除全部记忆     # 清空所有 Skill 的记忆数据
```

**辅助工具：**

```bash
python review.py          # 终端彩色面板：到期复习数、掌握率、薄弱项 TOP 10
bash skill-creator.sh     # 交互式创建自定义 Skill 骨架
```

---

## 想了解更多

- 设计理念、认知科学依据、架构决策 → [DESIGN.md](./DESIGN.md)
- 贡献指南 → [CONTRIBUTING.md](./CONTRIBUTING.md)
- 后续规划 → [docs/roadmap.md](./docs/roadmap.md)
- 学科扩展方案 → [docs/subject-expansion-plan.md](./docs/subject-expansion-plan.md)

---

## 语言选择 / Language

- 🇨🇳 [中文版本](./README.md) (Chinese)
- 🇬🇧 [English Version](./README.en.md)

---

## License

MIT
