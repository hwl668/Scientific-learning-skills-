# LearningSkillBench — run `pilot20-v1`

## 诚实边界（必须随结果一起展示）

- Subject model: `deepseek-v4-pro[1m]`（provider `anthropic`）；Judge model: `deepseek-v4-pro`
- 被评判 case 数：60；case 文件：`evals\bench\dev.synthetic.jsonl`（sha256 `250cd4dd47e272e8`）
- Level 2/TER 为 LLM-as-judge 判分，judge prompt 已冻结并随 run.json 发布；
- 若含 Level 3：模拟学习者结果 ≠ 真实学习效果，标注 `simulated-learner`，不能替代真人实验；
- git rev: `e912824`

## Level 2 — 回答质量（judge 1–5）与 TER

| 维度 | Base | Generic tutor | Scientific Learning Skills |
|---|---:|---:|---:|
| Correctness 学科正确性 | 4.90 | 4.95 | 4.85 |
| Diagnosis 诊断命中 | 4.95 | 4.95 | 4.85 |
| Relevance 解释靶向 | 4.50 | 4.65 | 4.20 |
| Cognitive load 认知负荷 | 4.25 | 4.55 | 3.75 |
| Hint quality 引导质量 | 4.10 | 4.30 | 4.00 |
| Misconceptions 误区处理 | 5.00 | 4.95 | 4.95 |
| Transfer 变式迁移 | 4.00 | 4.45 | 4.75 |
| TER 靶向解释率 | 0.95 | 0.96 | 0.93 |
| TER 平均单元数 | 29.1 | 23.4 | 29.8 |
| 输出 tokens（base=1.00） | 1.00 | 0.65 | 0.82 |

> ⚠️ **天花板效应**：三条件后测均为满分——模拟学习者（强模型）在当前后测难度上已无提升空间，Level 3 正确率不构成条件间差异的证据；仅误解纠正率尚有参考价值，且需更大样本。v0.5 应提高后测难度或换用更弱/更真实的模拟学习者。

## Level 3 — 模拟学习者后测（simulated-learner）

| 条件 | 同构题 | near-transfer | far-transfer | 误解纠正率 |
|---|---:|---:|---:|---:|
| Base | 100% | 100% | 100% | 85% |
| Generic tutor | 100% | 100% | 100% | 85% |
| Scientific Learning Skills | 100% | 100% | 100% | 85% |
