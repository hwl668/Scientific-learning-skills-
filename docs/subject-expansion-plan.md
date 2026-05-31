# 学科扩展方案

目标：扩展项目的学科吸引力，但不把核心 Skill 拆成一堆难维护的学科专用 prompt。

## 核心判断

当前 8 个 Skill 解决的是学习过程中的通用动作：

- 零基础入门
- 模糊理解诊断
- 深化理解
- 解题
- 错题复盘
- 单词深挖
- 文本记忆
- 学习计划

扩展学科时，优先增加 **examples / demo / eval cases**，而不是马上新增 `skills/<subject>/`。

原因：

- 学科覆盖能吸引更多人，但 Skill 数量过多会稀释定位。
- 现阶段最需要证明的是“同一套诊断式学习方法可迁移到多个学科”。
- examples 和 demo 的维护成本低，更适合开源早期吸引贡献。

## 扩展优先级

### P0：最能展示项目价值的 5 个学科

| 学科 | 为什么优先 | 推荐 demo |
|------|------------|-----------|
| 线性代数 | 抽象概念多，适合展示“会算但不懂”的诊断 | 矩阵、秩、特征值 |
| 高等数学/数学分析 | 大一学生高频痛点 | 极限、导数、泰勒、级数 |
| 数据结构与算法 | GitHub 用户容易共鸣 | Dijkstra、KMP、并查集、DP |
| 机器学习入门 | AI 社区传播友好 | softmax、batch size、ResNet、梯度 |
| 英语四六级/考研英语 | 学生群体大，记忆系统价值明显 | 形近词辨析、词根、选词填空 |

### P1：增强专业感的工程和理工科

| 学科 | 适合 Skill | 推荐案例 |
|------|------------|----------|
| CSAPP/计算机系统 | zero-base, fuzzy, problem-solving | cache locality、栈帧、静态变量 |
| 概率论与统计 | fuzzy, problem-solving, mistake-review | 条件概率、贝叶斯、中心极限定理 |
| 物理 | zero-base, fuzzy, mistake-review | 牛顿定律、动量守恒、电场 |
| 信号与系统 | fuzzy, deepening | 傅里叶变换、卷积、频域 |
| 数学建模/优化 | problem-solving, study-plan-builder | 变量、目标函数、约束 |

### P2：社区贡献型方向

- 化学
- 生物
- 医学基础
- 法学/政治背诵
- 历史
- 日语/其他语言

这些方向可以先作为 `good first issue`，让用户贡献案例，不急着写官方 Skill。

## 每个学科案例的标准格式

每新增一个 `examples/<subject>.md`，至少包含：

```markdown
# <Subject> 示例

## 零基础

**输入**：...
**适用 Skill**：`zero-base-learning`
**期望输出方向**：诊断起点 → 直觉 → 最小例题 → 自测

## 模糊理解

**输入**：...
**适用 Skill**：`fuzzy-understanding`
**期望输出方向**：卡点类型 → 修复策略 → 验证题 → 变式

## 解题/应用

**输入**：...
**适用 Skill**：`problem-solving`
**期望输出方向**：题型识别 → 关键条件 → 分步推演 → 方法总结

## 错题复盘

**输入**：...
**适用 Skill**：`mistake-review`
**期望输出方向**：错因归类 → 正确理解 → 检查清单 → 变式
```

## Demo 选择规则

每个 release 只新增 2-3 个高质量 demo，不追求数量。

优先选择满足以下条件的题：

- 用户痛点一眼能懂。
- 普通 AI 容易百科式回答。
- Skill 的“诊断先于讲解”能明显胜出。
- 可以在 80-120 行内展示完整对话。
- 有明确验证题或变式题。

## 近期执行计划

### v0.1.x：补齐高传播案例

- `demo/fuzzy-understanding-epsilon-n.md`
- `demo/problem-solving-dijkstra.md`
- `demo/word-deep-dive-complimentary.md`
- `examples/machine-learning.md`
- `examples/probability-statistics.md`

### v0.2：建立学科案例矩阵

每个 P0 学科至少覆盖：

- 2 个零基础案例
- 3 个模糊理解案例
- 2 个解题案例
- 1 个错题复盘案例

### v0.3：再考虑学科专用 Skill

只有当某个学科出现稳定、重复、通用的流程差异时，才新增学科专用 Skill。

新增条件：

- 至少 10 个真实案例证明通用 Skill 不够用。
- 有明确的专用诊断框架。
- 能写出独立测试集。
- 不与现有 8 个 Skill 大量重叠。

## 不建议做的事

- 不要为了“覆盖多”而新增一堆空泛学科 Skill。
- 不要把每个课程都做成一个 Skill。
- 不要在 README 首屏堆学科列表，核心卖点仍是诊断式学习。
- 不要让案例只剩“题目 → 答案”，必须保留卡点诊断和变式验证。
