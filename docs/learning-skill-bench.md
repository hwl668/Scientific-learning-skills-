# LearningSkillBench v0.1 — 设计方案

> 目标：把 README 的核心证据从「静态结构 17/20」升级为「真实模型加载 Skill 后是否真的更会教」。回答一个问题：**Skill 到底有没有使模型更会教？**
>
> 状态：设计稿，未实施。运行需要真实模型 API（或人工复制粘贴协议）。本文件整合自 2026-10 的项目评审讨论。

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

### Level 2 — 回答质量（LLM-as-judge，1–5 分）

judge 模型与被测模型不同源（如被测用模型 X，judge 用模型 Y），输出结构化 JSON：

```text
correctness            学科事实是否正确（judge 需给理由）
diagnostic_precision   诊断是否命中最可能的卡点（对照 intended_gap_type）
explanation_relevance  解释是否针对卡点，而非泛泛而谈
cognitive_load         是否一次塞入过多无关内容
hint_quality           解题类：引导 vs 直接给答案
misconception_handling 误区表是否真实、具体、可操作
transfer_quality       变式题是否真正改变条件/场景而非换数字
```

judge prompt 需冻结、入库、随结果一起发布；对同一批输出跑 judge 一致性（同 judge 两次 + 第二 judge 抽样）。

### Level 3 — 学习增益（本项目差异化的核心）

用另一个模型**模拟学习者**做前后测：

```text
1. 模拟学生带着 intended_gap_type 对应的误解提问
2. 被测条件生成教学回复
3. 模拟学生（保持人设与初始误解）学习后作答后测：
   Q1 同构题（数字不同）  Q2 near-transfer（换场景）  Q3 far-transfer（换概念域）
4. 判分：judge 按标准答案 + 误解是否被纠正打分
```

**报告指标**：后测正确率（分 Q1/Q2/Q3）、误解纠正率、以及在模拟学生明确要求下「直接给答案」的比率。

⚠️ 诚实边界：模拟学生≠真实学生。它测的是「教学输出是否足以让一个有初始误解的强模型纠正并迁移」，不能替代真人实验。发布结果时必须带上这个限制，标注 `simulated-learner`。

## 4. 核心指标：TER（Targeted Explanation Ratio）

项目的 story 是「**不是讲更多，是诊断更准**」，所以要测讲解的靶向率：

```text
TER = 针对已诊断卡点的解释单元数 / 全部解释单元数
```

由 judge 标注每个解释段落「是否服务于诊断出的卡点」。预期：Base 条件讲 8 件事命中 3 件，Skill 条件讲 4-5 件命中 3 件 → **更少 token，更多有效教学**。报告同时给出每条件平均输出 token 数。

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

## 7. 实施顺序

1. `evals/bench/cases.v0.1.jsonl`（100 题，先 20 题试运行版）
2. `learning_agent/bench/runner.py`：读题 → 调 API（OpenAI 兼容接口，model/key 走环境变量）→ 存原始输出
3. `learning_agent/bench/judge.py`：Level 2/3 判分 + TER 统计
4. `learning_agent/bench/report.py`：聚合出 README 表
5. 试点 10 题 → 校准 → 全量 → 更新 README 证据段

## 8. 明确不做的事

- 不为了 bench 扩充更多 skill / 不换更好的 router 模型（9 分类下路由不是瓶颈，见 roadmap）
- 不在拿到真实数据前把任何预填数字写进 README
- 不宣称模拟学习者结果等同真实学习效果
