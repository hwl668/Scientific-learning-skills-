# 已评审的 Bench 聚合报告

本目录只存放**已评审的聚合报告**（`report.md` / `report.json`），由
`python -m learning_agent.bench.report --run-id <id> --copy-to evals/bench/results` 生成。

原始输出（模型回复、judge 逐条标注）保留在 `artifacts/bench/<run-id>/`，
该目录被 gitignore，不入库；发布时可另行打包。

| 报告 | 内容 | 注意 |
|---|---|---|
| `pilot20-v1.md` | 首次真实模型三条件对照：20 case（dev 集带 gold 标注子集）× Base / Generic tutor / Skills，Level 2 judge 七维 + TER + Level 3 模拟学习者后测（两轮协议） | judge 与被测同源（self-judge 已披露）；`simulated-learner` ≠ 真实学习效果；样本量小，方向性信号 |
