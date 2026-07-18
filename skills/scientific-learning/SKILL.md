---
name: scientific-learning
description: 学习请求的兜底路由入口。仅在用户显式要求使用 scientific-learning/统一学习入口，或请求意图确实模糊、有多个子 skill 同时合理而需要先分流时使用。不要用于已能直接匹配 zero-base-learning、fuzzy-understanding、deepening-learning、problem-solving、mistake-review、word-deep-dive、text-memorizer 或 study-plan-builder 的普通学习请求；这类请求应直接使用对应子 skill。
---

# 目标

作为 Scientific Learning Skills 的轻量兜底入口，仅在显式调用或无法直接确定子 skill 时分流。不要把它当成所有学习请求的前置层，也不要在父 skill 里抢先长篇讲解。

# 路由原则

1. 用户显式点名子 skill 时，直接使用该子 skill，不经过本入口。
2. 请求已能直接匹配某个子 skill 时，直接使用子 skill，不要额外加载本 skill。
3. 只有在用户显式调用本入口，或多个意图无法靠已有上下文区分时，才用下面的路由表。
4. 如果平台支持显式 Skill 调用，调用对应子 skill。
5. 如果没有显式 Skill 调用但能访问本地 skill 文件，打开并遵循对应 sibling skill 的 `SKILL.md`：
   - `../zero-base-learning/SKILL.md`
   - `../fuzzy-understanding/SKILL.md`
   - `../deepening-learning/SKILL.md`
   - `../problem-solving/SKILL.md`
   - `../mistake-review/SKILL.md`
   - `../word-deep-dive/SKILL.md`
   - `../text-memorizer/SKILL.md`
   - `../study-plan-builder/SKILL.md`
6. 如果不能调用或访问子 skill，按本文件的简版流程执行，保持"诊断先于讲解"。

# 路由表

| 用户输入特征 | 路由到 |
|-------------|--------|
| "是什么"、"从零讲"、"第一次学"、"完全不懂"、"入门" | `zero-base-learning` |
| "学过但不懂"、"云里雾里"、"分不清"、"不会用"、"看不懂符号"、"感觉懂了但..." | `fuzzy-understanding` |
| "讲透"、"本质"、"为什么"、"多角度"、"证明/推导"、"和 X 有什么联系" | `deepening-learning` |
| "这题怎么做"、"求解"、"证明题"、"卡住了"、"不会做题" | `problem-solving` |
| "做错了"、"错题"、"答案不一样"、"为什么我错"、"粗心" | `mistake-review` |
| 单个英语单词、`!word`、"查词"、"这个词什么意思"、"复习单词" | `word-deep-dive` |
| 一段需要背的文字、"帮我背"、"抽背"、"出题"、"复习薄弱点" | `text-memorizer` |
| "学习计划"、"复习安排"、"路线图"、"多久学完"、"怎么备考" | `study-plan-builder` |

# 冲突处理

- 有题目且用户说"错了"：优先 `mistake-review`。
- 有题目但没有错误解答：优先 `problem-solving`。
- 问"是什么"但显然已经学过并表达困惑：优先 `fuzzy-understanding`。
- 问"为什么/本质"但基础不牢：先用 `fuzzy-understanding` 修基础，再深化。
- 粘贴长文本并要求记忆/背诵：优先 `text-memorizer`，不是普通总结。
- 输入一个英语词或带 `!` 的词：优先 `word-deep-dive`。

# 执行流程

```
识别意图 -> 选择子 skill -> 必要时追问 1-2 个诊断问题 -> 按子 skill 输出
```

## 1. 识别意图

用一句话说明当前应使用哪个子 skill。例如：

> 我会按 `fuzzy-understanding` 处理：你不是零基础，而是学过后卡在概念/符号/迁移中的某一处。

如果用户已经明确说"直接回答，不要诊断"，可以简化诊断，但仍保留最小校准。

## 2. 调用/模拟子 skill

优先加载对应子 skill 的完整说明。无法加载时使用以下最小行为：

- `zero-base-learning`：从问题背景、直觉、最小定义、例题、误区、自测开始。
- `fuzzy-understanding`：先定位卡点，再只修卡住的部分，最后验证和变式。
- `deepening-learning`：确认基础后选 2-4 个维度：多视角、证明、反例、联系、应用。
- `problem-solving`：识别题型、找关键条件、建模、分步推演、总结方法、给变式。
- `mistake-review`：重现错误、归类错因、指出分叉口、给检查清单、给变式。
- `word-deep-dive`：解析单词/考试/是否记忆，输出义项、搭配、辨析、考法、误区。
- `text-memorizer`：拆结构、给思维导图、关键词压缩、生成抽背题、追踪薄弱点。
- `study-plan-builder`：收集目标、基础、时间、资源、截止日期，再排阶段和检测标准。

无法加载子 Skill 而使用上述简版行为时，最终输出仍必须包含至少 2 条真实数据行的“常见误区”表，以及 1-2 道自测/变式题。

# 禁止行为

- 不要把父 skill 当成第九个讲解模板。
- 不要抢占已有明确触发语义的子 skill；普通且意图明确的学习请求应直接进入子 skill。
- 不要父 skill 解释一大段后才想起路由。
- 不要在需要错题复盘时只给正确答案。
- 不要在需要背诵时只做摘要。

# 测试样例

**输入**：矩阵乘法是什么？

**期望**：如果平台在选择 Skill，不触发本入口；没有学习背景时直接使用 `zero-base-learning`，上下文显示用户学过但不理解意义时直接使用 `fuzzy-understanding`。

**输入**：这题我答案和标准答案不一样，帮我看看为什么错。

**期望**：不触发本入口；直接使用 `mistake-review`，要求原题、错误解答、标准答案、当时思路。

**输入**：用一个大的 skill 帮我处理学习问题。

**期望**：使用本父 skill 先路由，再调用最合适的子 skill。
