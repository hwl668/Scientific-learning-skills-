# LearningSkillBench v0.1 — 设计方案

> 目标：把 README 的核心证据从「静态结构 17/20」升级为「真实模型加载 Skill 后是否真的更会教」。回答一个问题：**Skill 到底有没有使模型更会教？**
>
> 状态：**v0.1 已实施**（2026-10）。runner / judge / report 三件套在 `learning_agent/bench/`，数据集在 `evals/bench/`，运行协议见本文件末尾。模拟学习者结果不能替代真人实验；mock 运行不构成任何证据。本文件整合自 2026-10 的项目评审讨论。

---

## 0. 实施状态

> **v2 协议（2026-10-06）**：针对 pilot20-v1 暴露的两个问题做了修订——
> ① Skills 条件在 Relevance（4.20 vs 4.65）与 Cognitive load（3.75 vs 4.55）上输给
> generic tutor，诊断成了「前置税」→ 修 SKILL.md/RULES.md（诊断预算：最多 1 个带假设的
> 问题；初学者信号出现则 0 个；输出只服务当前卡点）后重跑；
> ② Level 3 三条件后测全 100%（天花板）→ 后测全部加难为多步应用/预测题 +
> 模拟学习者换用更弱模型（`--learner-model deepseek-chat`，教学轮仍为被测模型）。
> 同时吸收调研的 MRBench 维度：judge V2 新增 **Mistake Location** 与 **No-reveal**，
> 并引入 `student_level`（low/mid/high）**分层报告**——同一诊断对初学者有害的风险
> （McMiner：+15.9pp / −12.2pp）不允许被平均分掩盖。

| 组件 | 状态 | 位置 |
|---|---|---|
| 三条件对照设计 | ✅ 定稿（v2 协议） | 本文件 §1/§3 |
| dev 集（100 synthetic，兼 router 回归集） | ✅ | `evals/bench/dev.synthetic.jsonl` |
| public test 集（50 half-real，源自 MathDial CC BY-SA 4.0） | ✅ | `evals/bench/test.public.jsonl`（生成器 `scripts/build_test_public.py`） |
| private holdout | ⬜ 保留位（不入库） | 见 §2 末尾 |
| schema + 路由一致性门禁（CI） | ✅ | `python -m learning_agent.bench.validate_cases` |
| gold 标注（20 条 pilot：诊断 / must_address / must_not_do；其中 17 条含加难后测） | ✅ v2 | dev 文件 `gold` / `post_test` / `student_level` 字段 |
| runner（三条件生成；独立学习者模型；断点续跑；mock 模式） | ✅ | `learning_agent/bench/runner.py` |
| judge（Level 2 九维 1–5 + TER 原子单元标注 + Level 3 后测判分） | ✅ V2 | `learning_agent/bench/judge.py` |
| report（聚合表 + student_level 分层 + 诚实边界声明） | ✅ | `learning_agent/bench/report.py` |
| 冻结 prompt（generic-tutor / judge V2 / learner，sha256 指纹随 run.json 发布） | ✅ | `learning_agent/bench/prompts.py` |
| 首次真实 pilot（pilot20-v1，存档对照） | ✅ | `evals/bench/results/pilot20-v1.md` |
| v2 pilot（诊断预算修复验证） | ✅ provisional | `evals/bench/results/pilot20-v2.md`——judge 为作者 inline 判分（非盲/不可复现），API judge 复核待授权；learner 中断于 10/60，Level 3 仅局部覆盖 |

### 数据分层与防污染

```text
evals/bench/
├── dev.synthetic.jsonl    100 synthetic —— 开发 + router 回归集（调 Skill 只允许用它）
├── test.public.jsonl       50 half-real —— 公开测试集（MathDial 派生，教师标注混淆作 gold）
└── results/                已评审聚合报告（report.md/json）；原始输出不入库
```

test.private holdout 刻意**不入库**：由维护者单独保存，在 dev/public 上停止调参后再解锁，避免 benchmark contamination。MathDial 的学生侧为 LLM 生成、真人教师把关，题目与教学对话为真人产出，故派生案例一律标 `half-real`（不标 `real`）；`gold.diagnosis` 直接复用 MathDial 教师标注的混淆描述。

---

## 1. 实验设计：三条件对照

不只对比「裸模型 vs 加载 Skill」，增加一个 generic tutor 提示词作为第三条件，才能证明收益来自**结构化的学习工作流**而不是「你加了句你是个好老师」：

| 条件 | 内容 |
|------|------|
| **A. Base** | 裸模型，不加任何教学提示 |
| **B. Generic tutor** | 一段通用提示：「你是一位耐心、擅长讲解的好老师，请把概念讲清楚」（长度与 SKILL.md 相当，排除「提示更长所以更好」的混淆变量） |
| **C. Scientific Learning Skills** | 加载对应子 skill（按 router 分流后的 SKILL.md + RULES.md） |

## 2. 数据集：100 个真实/半真实学习问题

按 skill 分布（与真实学习请求的分布近似）：

```text
20 zero-base · 20 fuzzy-understanding · 20 problem-solving · 15 mistake-review
10 deepening · 5 word · 5 text-memorizer · 5 study-plan
```

学科覆盖：微积分、线性代数、概率、数据结构、操作系统、物理、机器学习、英语词汇。

**来源分三档，并在数据集中标注**：
- `real`：真实学生提问（论坛、答疑记录，脱敏）
- `half-real`：真实问题改写（换数字/换概念）
- `synthetic`：按卡点类型模板生成

题目带元数据：`subject` / `intended_skill` / `intended_gap_type`（六类卡点之一）/ `source`。

## 3. 三层评测

### Level 1 — 指令遵循（已有，deterministic）

现有 10 维 rubric / validate 逻辑继续用，但**降级为门槛检查**，不作为主要证据。

### Level 2 — 回答质量（LLM-as-judge，1–5 分，V2 九维）

judge 模型应与被测模型不同源（v2 pilot 受限于单一可用端点为同源自评，已披露），
输出结构化 JSON。V2 维度（**加粗**为 v2 依据调研吸收的 MRBench 维度）：

```text
correctness             学科事实是否正确（judge 需给理由）
diagnostic_precision    诊断是否命中最可能的卡点（对照 gold；= MRBench Mistake ID）
mistake_location        **是否指明理解断裂的具体位置（哪一步/哪个表征）**
explanation_relevance   解释是否针对卡点，而非泛泛而谈
no_reveal               **是否在学生产出推理前不交出最终答案；纯解释类计 3（中性）**
cognitive_load          是否塞入无关内容或堆叠超出单一卡点所需的结构
hint_quality            解题类：引导 vs 直接给答案
misconception_handling  误区表是否真实、具体、可操作
transfer_quality        变式题是否真正改变条件/场景而非换数字
```

judge prompt 需冻结、入库、随结果一起发布（V2 含按 `student_level` 的校准指令：
对 low 水平，「只追问不教学」在 cognitive_load / no_reveal 上扣分）；对同一批输出跑
judge 一致性（同 judge 两次 + 第二 judge 抽样）仍为 v0.5 待办。

### Level 3 — 学习增益（本项目差异化的核心）

用另一个模型**模拟学习者**做前后测，采用**两轮教学协议**：

```text
1. 模拟学生带着 intended_gap_type 对应的误解提问
2. 被测条件生成教学回复（第一轮；Skills 条件按其规范可能只输出诊断性提问）
3. 模拟学生以人设回答教师的诊断问题 → 教师用同一条件 prompt 完成第二轮针对性教学
4. 模拟学生（保持人设与初始误解）学习两轮内容后作答后测：
   Q1 同构题（数字不同）  Q2 near-transfer（换场景）  Q3 far-transfer（换概念域）
5. 判分：judge 按标准答案 + 误解是否被纠正打分
```

> 为什么两轮：Skills 条件被规范要求「先诊断再讲解」，单轮协议会惩罚诊断优先行为（第一轮只提问不教学，后测无从谈起）。两轮协议测量的是方法论的**部署形态**：诊断 →（拿到学习者回答）→ 针对性教学。judge 对 Level 2 也评完整两轮 transcript，三条件协议一致。

**报告指标**：后测正确率（分 Q1/Q2/Q3）、误解纠正率、以及在模拟学生明确要求下「直接给答案」的比率。

⚠️ 诚实边界：模拟学生≠真实学生。它测的是「教学输出是否足以让一个有初始误解的强模型纠正并迁移」，不能替代真人实验。发布结果时必须带上这个限制，标注 `simulated-learner`。

## 4. 核心指标：TER（Targeted Explanation Ratio）

项目的 story 是「**不是讲更多，是诊断更准**」，所以要测讲解的靶向率。为保证两个 judge 能得到可比的数字，「解释单元」采取**原子教学主张**（atomic teaching claim）操作化定义，由 judge 按冻结规则切分：

```text
解释单元 = 一条最小、自足的教学断言（一个定义 / 一个步骤 / 一个类比 / 一个告警）。
切分规则（冻结在 judge prompt 中）：
- 按出现顺序编号 E1, E2, ...；每个单元一句话或一个紧邻的句子群
- 复合句含两个独立教学断言 → 拆成两个单元
- 空泛鼓励、寒暄、跑题的拓展、与卡点无关的通用学习建议 → 计入单元但 addresses_gap=false

TER = Σ I(E_i 针对已诊断卡点) / N        （N = 全部解释单元数）
```

判定「针对卡点」的锚：反事实测试——**删掉这个单元后，对本 case 已诊断卡点的处理是否明显变弱**；变弱则 relevant。预期：Base 条件讲 8 件事命中 3 件，Skill 条件讲 4-5 件命中 3 件 → **更少 token，更多有效教学**。报告同时给出每条件平均输出 token 数与平均单元数（TER 的分母透明化，防止「少说话刷 TER」）。

TODO（v0.2）：人工在 30–50 条输出上标注单元切分与 relevant 判定，计算 judge 与人工的 agreement（切分 F1 ≥ 0.7、relevant κ ≥ 0.6 方可固化为 headline 指标）。

## 5. 运行协议（最小可行）

- 每条件 × 每题跑 1 次（温度 0 或厂商默认），冻结全部原始输出到 `artifacts/bench/<run-id>/`（gitignore，只入库聚合结果）
- 先跑 10 题试点校准 judge prompt，再放量到 100
- 每次运行产出 `report.json` + `report.md`（聚合表 + 逐题明细引用）

## 6. README 结果表格式（目标形态）

| Method | Diagnosis 准确率 | 后测 Q1/Q2/Q3 | TER | Tokens |
|--------|----------------|---------------|-----|--------|
| Base | … | … | … | 100% |
| Generic tutor | … | … | … | … |
| **Scientific Learning Skills** | … | … | … | … |

## 7. 实施顺序与运行协议

1. ✅ `evals/bench/dev.synthetic.jsonl`（100 题；20 条 pilot 子集含 gold/post_test）
2. ✅ `learning_agent/bench/runner.py`：读题 → 调 API（Anthropic/OpenAI 兼容，key 走环境变量）→ 原始输出冻结到 `artifacts/bench/<run-id>/`
3. ✅ `learning_agent/bench/judge.py`：Level 2/3 判分 + TER 统计
4. ✅ `learning_agent/bench/report.py`：聚合出 README 目标形态表
5. ✅ 20 题真实 pilot → `evals/bench/results/pilot20-v1.md`（含 judge 一致性注记）；放量到 100 题与 public test 放到 v0.5

### 命令（pilot20-v2 实际使用的协议）

> 推理型模型（如 deepseek-v4-pro）会把输出预算花在思考上，教学与判分调用都需要大预算；
> 4096 及以下会出现空响应/截断（pilot20-v1 中已实际发生并全部重跑修正）。
> `--learner-model deepseek-chat` 让模拟学习者用更弱的非推理模型（Level 3 更有区分度），
> 教学轮仍由被测模型完成。

```bash
# 0. 数据门禁（CI 同款）
python -m learning_agent.bench.validate_cases

# 1. 生成三条件教学回复（--with-learner 同时跑 Level 3 两轮教学 + 后测）
python -m learning_agent.bench.runner \
  --cases evals/bench/dev.synthetic.jsonl --run-id pilot20-v2 --with-learner --max-tokens 16384 \
  --judge-model deepseek-v4-pro --learner-model deepseek-chat \
  --ids zb-001,zb-008,zb-014,fz-001,fz-006,fz-012,fz-019,ps-001,ps-006,ps-011, \
        ps-020,mr-001,mr-003,mr-008,mr-015,dp-001,dp-005,wd-001,tm-001,sp-001

# 2. judge 判分（judge 模型与被测模型不同源时在 --judge-model 记录）
python -m learning_agent.bench.judge --run-id pilot20-v2

# 3. 聚合报告（--copy-to 把聚合结果入库，原始输出留在 gitignore 的 artifacts/bench/）
python -m learning_agent.bench.report --run-id pilot20-v1 --copy-to evals/bench/results
```

### pilot20-v1 结果解读（诚实版）

完整数字见 [`../evals/bench/results/pilot20-v1.md`](../evals/bench/results/pilot20-v1.md)。要点：

- **Transfer 变式迁移是 skills 条件唯一明确的赢面**（4.75 vs generic 4.45 vs base 4.00）——恰好是方法论的核心主张（「换条件还会做才算真懂」）。
- **输出更省**：skills 0.82× base 的输出 token（generic 0.65×）。
- **大部分 Level 2 维度被 judge 天花板压缩**（correctness 4.9、misconceptions 5.0、TER 0.93–0.96）：强模型 + 自评 + 反事实相关锚过松，区分度不足；**Cognitive load 反而 skills 最低（3.75）**，与结构化输出较长有关。
- **两轮协议的副作用**：模拟学习者在第一轮如实回答诊断问题后，三个条件都拿到了卡点信号——「先诊断」的优势不再体现在 diagnosis 分数上，而是转移到 transfer 与 token 效率上。这是协议本身的发现，不是噪声。
- **Level 3 天花板**：后测对强模型模拟学习者太容易，三条件全 100%，无区分度。
- **v0.5 评测改进清单**：① paired comparative judging（同题 A/B 对比判分替代绝对打分）② 第二 judge 交叉 ③ TER 锚点收紧 + 30–50 条人工 agreement 标注 ④ 提高后测难度 / 换弱一点的模拟学习者 ⑤ 换异源 judge。

凭据：`ANTHROPIC_BASE_URL` + `ANTHROPIC_AUTH_TOKEN`（Anthropic 协议）或 `OPENAI_BASE_URL` + `OPENAI_API_KEY`；模型用 `BENCH_MODEL` 或 `--model` 指定。中断后重跑同一 `--run-id` 会跳过已完成的 (case, condition)，不会重复计费。`--mock` 只用于流水线自检，报告会标注 MOCK 并省略数字表。

## 8. 明确不做的事

- 不为了 bench 扩充更多 skill / 不换更好的 router 模型（9 分类下路由不是瓶颈，见 roadmap）
- 不在拿到真实数据前把任何预填数字写进 README
- 不宣称模拟学习者结果等同真实学习效果
