# LearningSkillBench — run `pilot20-v2`

## 诚实边界（必须随结果一起展示）

- Subject model: `deepseek-v4-pro[1m]`（provider `anthropic`）；Judge model: `glm-inline-provisional (project author, non-blind, non-reproducible)`
- 被评判 case 数：60；case 文件：`evals\bench\dev.synthetic.jsonl`（sha256 `816adb2e3ae295d6`）
- Level 2/TER 为 LLM-as-judge 判分，judge prompt 已冻结并随 run.json 发布；
- 若含 Level 3：模拟学习者结果 ≠ 真实学习效果，标注 `simulated-learner`，不能替代真人实验；
- git rev: `72855ae`

## Level 2 — 回答质量（judge 1–5）与 TER

| 维度 | Base | Generic tutor | Scientific Learning Skills |
|---|---:|---:|---:|
| Correctness 学科正确性 | 5.00 | 5.00 | 5.00 |
| Diagnosis 诊断命中 (Mistake ID) | 3.65 | 3.70 | 4.90 |
| Mistake location 卡点定位 | 2.65 | 2.60 | 3.85 |
| Relevance 解释靶向 | 4.20 | 4.60 | 5.00 |
| No-reveal 不剧透 | 2.75 | 2.75 | 3.20 |
| Cognitive load 认知负荷 | 3.25 | 3.95 | 3.15 |
| Hint quality 引导质量 | 2.05 | 3.00 | 4.40 |
| Misconceptions 误区处理 | 2.00 | 2.15 | 4.70 |
| Transfer 变式迁移 | 1.25 | 2.05 | 4.00 |
| TER 靶向解释率 | 0.91 | 0.97 | 1.00 |
| TER 平均单元数 | 6.4 | 6.0 | 10.4 |
| 输出 tokens（base=1.00） | 1.00 | 0.69 | 1.19 |

> ⚠️ **天花板效应**：三条件后测均为满分——模拟学习者（强模型）在当前后测难度上已无提升空间，Level 3 正确率不构成条件间差异的证据；仅误解纠正率尚有参考价值，且需更大样本。v0.5 应提高后测难度或换用更弱/更真实的模拟学习者。

## Level 3 — 模拟学习者后测（simulated-learner）

| 条件 | 同构题 | near-transfer | far-transfer | 误解纠正率 |
|---|---:|---:|---:|---:|
| Base | 100% | 100% | 100% | 100% |
| Generic tutor | 100% | 100% | 100% | 100% |
| Scientific Learning Skills | 100% | 100% | 100% | 100% |

## 按学习者水平分层（case 标注的 student_level）

> 平均分会掩盖「同一诊断对初学者有害」的风险，此表必须与总体表一起阅读。

| 水平 | 条件 | n | Diagnosis | No-reveal | Cog. load | Relevance | Transfer | 后测均分 | 误解纠正 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 初学者 low | Base | 9 | 3.67 | 2.89 | 3.78 | 4.00 | 1.33 | 1.00 | 100% |
| 初学者 low | Generic tutor | 9 | 3.78 | 2.89 | 4.44 | 4.67 | 2.00 | 1.00 | 100% |
| 初学者 low | Scientific Learning Skills | 9 | 5.00 | 3.11 | 3.22 | 5.00 | 3.89 | 1.00 | 100% |
| 进阶 mid | Base | 9 | 3.56 | 2.56 | 3.00 | 4.22 | 1.22 | 1.00 | 100% |
| 进阶 mid | Generic tutor | 9 | 3.56 | 2.56 | 3.67 | 4.44 | 2.33 | — | — |
| 进阶 mid | Scientific Learning Skills | 9 | 4.78 | 3.33 | 3.11 | 5.00 | 4.11 | — | — |
| 高阶 high | Base | 2 | 4.00 | 3.00 | 2.00 | 5.00 | 1.00 | — | — |
| 高阶 high | Generic tutor | 2 | 4.00 | 3.00 | 3.00 | 5.00 | 1.00 | — | — |
| 高阶 high | Scientific Learning Skills | 2 | 5.00 | 3.00 | 3.00 | 5.00 | 4.00 | — | — |
