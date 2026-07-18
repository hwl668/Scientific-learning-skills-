# Scientific Learning Skills

> A student-facing Agent Skills prototype for diagnosis-before-explanation tutoring.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Platforms](https://img.shields.io/badge/Platform-Claude%20Code%20|%20Codex%20|%20OpenClaw%20|%20GPTs%20|%20Generic-lightgrey)

[Quick Start](#快速开始) · [Demo](./demo/) · [Evidence](#证据边界与本地验证) · [设计对比](#设计对比示例) · [Platforms](#安装到其他平台) · [English](./README.en.md)

---

## 它能做什么

> 下列内容是仓库中编写的行为示例，用于展示 Skill 期望的交互形式；不是受控对照实验、实时模型生成记录或真实用户学习证据。

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

**9 个 Skill，覆盖 9 类常见学习任务：**

| 你在想什么 | 典型匹配 |
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

## 设计对比示例

下表对比两个仓库内的手工编写示例，用来说明“先诊断、再讲解”的设计意图。它不是在同一模型、同一参数下的现场 A/B 测试。

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

**左侧示例直接给了三个视角**——但用户真正缺的可能只是其中一个视角的直觉，因此可能造成额外信息负担。

**Skill 先追问两个诊断问题**——判断是「直觉缺失」还是「概念混淆」，然后只讲用户缺失的那一块。不讲用户已经懂的内容，不讲用户暂时不需要的内容。

---

### 静态结构评分

下表是基于 `evals/scoring_rubric.md` 对两个**已签入仓库的静态 Markdown 示例**所做的启发式结构打分。`python eval.py --all` 可以复现该规则检查；`--quick` 会排除 baseline。评分只检查诊断问句、变式、误区表等可观察结构，不代表模型新生成输出的质量或学习效果。

| 维度 | 裸 AI | 加载 Skill | 差异 |
|------|-------|-----------|------|
| 是否诊断卡点 | 0 | 2 | **诊断先于讲解** |
| 是否有直觉解释 | 1 | 2 | 针对性类比 vs 通用举例 |
| 是否有例题 | 1 | 1 | 均有 |
| 是否有变式迁移 | 0 | 2 | **Skill 强制要求** |
| 是否指出常见误区 | 0 | 2 | **Skill P0 强制** |
| 是否简洁清晰 | 2 | 2 | 均清晰 |
| **总分** | **11/20** | **17/20** | **+6 分** |

> **设计目标**：先判断学习者的具体卡点，再提供针对性解释，减少与当前问题无关的信息。

---

## 快速开始

```bash
git clone https://github.com/hwl668/Scientific-learning-skills-.git scientific-learning-skills
cd scientific-learning-skills
bash setup.sh # 自动检测 AI 工具 + 创建软链接 + 初始化 memory
claude        # 启动，Skills 自动加载
```

`setup.sh` 支持 Linux、macOS，以及在 Linux 文件系统内完成 clone 的 WSL 环境。由于 Git for Windows 在 `core.symlinks=false` 时会把仓库符号链接检出为普通文件，当前不承诺 Git Bash 安装路径可用。脚本会为检测到的 Claude Code 创建 `.claude/skills/` 链接并初始化本地 `memory/`；它只检测 Codex CLI，不会为 Codex 自动安装 Skill。Codex 用法见 [`deploy/codex.md`](./deploy/codex.md)。

然后直接说话：

```text
> 什么是极限？我第一次接触。
> 我会算矩阵乘法，但不知道矩阵到底表示什么。
> !undermine 六级
```

想先看看设计形式？→ [`demo/`](./demo/) 目录包含仓库维护者编写的静态对话/输出示例，不用安装就能浏览。

想运行静态结构回归？→

```bash
python -B eval.py --quick
python -B -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report markdown
```

两条命令都对仓库内的静态文本做启发式规则检查，不会调用模型生成新回复。

## v0.2 / v0.3：实验性 Learning Agent 模块

项目目前是 **Skill Pack + 可独立运行的实验性 CLI 模块**。Skill 定义教学行为；路由、诊断、记忆调度、评测、提示编译和案例库可以分别通过命令行运行。这些模块尚未串成一个持久化、端到端的学习产品。v0.3 还包含一个 learned-router baseline，用合成训练数据学习 skill routing，并设置 `non-learning` 类与低置信度 fallback。

| 模块 | 作用 | 命令 |
|------|------|------|
| Skill Router | 将用户学习问题路由到合适的 skill | `python -m learning_agent.router "我会算矩阵乘法，但不知道矩阵到底表示什么"` |
| Cognitive Diagnosis | 识别 6 类学习卡点 | `python -m learning_agent.diagnosis "矩阵乘法我会算，但不知道为什么要行乘列"` |
| Memory Scheduler | 用 SM-2 风格的启发式规则更新间隔，并派生掌握/遗忘风险信号与复习优先级 | `python -m learning_agent.memory.scheduler '{"id":"limit","correct_streak":2,"interval_days":6}' --quality 5 --json` |
| Eval Runner | 运行 demo / JSONL suite，输出 text、JSON 或 Markdown 报告 | `python -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report markdown` |
| Prompt Compiler | 按平台、skill 选择和 token budget 生成 system prompt | `python -m learning_agent.compile --target codex --skills fuzzy,problem,word --output prompt.md --metadata` |
| Subject Case Library | 管理大学专业课、算法、机器学习、系统课、建模和科研竞赛案例 | `python -m learning_agent.subjects --summary` |
| Learned Router | TF-IDF char n-gram + Logistic Regression 路由基线，支持 top-k 和低置信度 fallback | `python -m learning_agent.ml_router predict "我会算矩阵乘法，但不知道它到底表示什么"` |

数据与回归样例：

| 文件 | 性质与用途 |
|------|-------------|
| `data/routing_cases.jsonl` | 仓库内编写并标签的规则路由回归案例；不是真实用户抽样或外部 holdout |
| `data/diagnosis_cases.jsonl` | 仓库内编写并标签的诊断回归案例；不是真实用户抽样或外部 holdout |
| `data/subject_cases.jsonl` | 用于检查学科/场景分布的覆盖目录，不是学习效果数据 |
| `learning_agent/resources/data/training/router_training_v0.3.jsonl` | 按模板程序生成的 synthetic/silver 路由训练数据，含 hard negatives 和 `non-learning`；不应当作独立测试证据 |
| `evals/cases/smoke.jsonl` | 手工编写的 8 个子 Skill 静态输出结构 smoke 案例；不调用模型，也不检验路由准确率或学科正确性 |

## 证据边界与本地验证

| 验证层 | 当前能说明什么 | 不能说明什么 |
|--------|------------------|------------------|
| `demo/` + `eval.py` | 已签入示例是否含某些教学结构 | 模型在新问题上会稳定遵循 Skill |
| 路由/诊断回归案例 | 当前规则在仓库内标签案例上是否回归 | 对新用户、新表达或新学科的泛化能力 |
| Learned-router 训练/分组优先的合成 holdout（含已披露 fallback） | 合成数据上的基线与管道健康状态 | 真实流量准确率或教学效果 |
| 真实用户研究 | **尚未提供** | 学习成绩提升、迁移效果或长期保持 |

Learned router 的训练报告应与数据集指纹、切分策略一起阅读。即使合成 holdout 上的指标很高，也不应写成“真实准确率 100%”或“已证明提升学习效果”。

安全模型格式、完整哈希、切分限制和适用边界见 [`artifacts/README.md`](./artifacts/README.md)。

当前回归验证：

```bash
# 全量回归需要可选的 ML 与 Skill YAML 校验依赖
python -m pip install -e ".[ml,validation]"

python -B -m unittest discover -s tests
python -B -m learning_agent.router --eval
python -B -m learning_agent.diagnosis --eval
python -B -m learning_agent.ml_router evaluate
python -B eval.py --quick
python -B -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report json
```

更多 v0.2 设计和验证说明见 [`docs/v0.2-summary.md`](./docs/v0.2-summary.md)。

## 安装到其他平台

Skills 本质是结构化 Markdown 指令集。在支持 Agent Skills 的宿主中可以加载 Skill 目录；其他平台可用 Prompt Compiler 合成指令。加载方式、模型能力与工具权限都会影响实际遵循效果。

| 平台 | 部署方式 | 说明 |
|------|---------|------|
| Claude Code | `.claude/skills/` 自动加载 | [详细说明](./deploy/claude-code.md) |
| OpenAI Codex / API / GPTs | 原生 Skill（宿主支持时）或合成指令 | [详细说明](./deploy/codex.md) |
| OpenClaw / OI | Skills 目录或系统提示 | [详细说明](./deploy/openclaw.md) |
| Cursor / Cline / Copilot | 规则文件或自定义指令 | [详细说明](./deploy/generic.md) |
| 任意智能体 | 系统提示注入 | [详细说明](./deploy/generic.md) |

Token 预算与选中 Skill 有关。用 `python -B -m learning_agent.compile --target generic --skills all --metadata` 查看当前版本的启发式估算；实际 token 数以目标模型的 tokenizer 为准。

### Memory 支持矩阵

不同平台对 Memory（间隔复习、薄弱追踪）的支持程度：

| 平台 | Memory 支持 | 说明 |
|------|-----------|------|
| Claude Code | 取决于权限 | 工作区可写时可用文件记忆 |
| Cursor / Cline | 有限 | 项目目录可写 |
| OpenClaw | 取决于运行时 | 需确认文件系统权限 |
| Codex（本地工作区） | 取决于沙箱 | `memory/` 在可写根目录中时才能持久化 |
| ChatGPT / GPTs | 需外部存储 | 需通过工具或 API 连接持久化存储 |
| OpenAI API | 需外部存储 | 调用方负责会话状态与数据库 |

本仓库未提供托管的用户记忆服务。无可写存储时，Skill 的单轮诊断/讲解/解题指令仍可加载，但跨会话复习状态不会持久化。

---

## 使用

在已加载子 Skill 且宿主支持 Skill 发现/匹配时，可以直接自然描述问题；匹配结果仍取决于宿主实现：

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

**记忆管理（对应 Skill 已加载且 `memory/` 可写时）：**

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
- 模型卡与安全制品说明 → [artifacts/README.md](./artifacts/README.md)
- 漏洞私下报告与数据边界 → [SECURITY.md](./SECURITY.md)
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
