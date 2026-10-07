# 已评审的 Bench 聚合报告

本目录只存放**已评审的聚合报告**（`report.md` / `report.json`），由
`python -m learning_agent.bench.report --run-id <id> --copy-to evals/bench/results` 生成。

原始输出（模型回复、judge 逐条标注）保留在 `artifacts/bench/<run-id>/`，
该目录被 gitignore，不入库；发布时可另行打包。

| 报告 | 内容 | 注意 |
|---|---|---|
| `pilot20-v1.md` | 首次真实模型三条件对照：20 case × Base / Generic / Skills，judge V1 七维 + TER + Level 3（单轮转两轮协议） | judge 与被测同源（deepseek 自评已披露）；Level 3 后测天花板；其中 21 条 skills 的第二轮教学因截断为空，对该条件的部分分数有拖累 |
| `pilot20-v2.md` | 诊断预算修复验证：judge V2 九维（+Mistake Location / No-reveal）+ student_level 分层 + 加难后测 + `--learner-model deepseek-chat` | **judge 为 inline provisional（项目作者本人判分：非盲、不可复现）**，授权 API 后应重跑正式 judge 对照；learner 阶段因 API 余额中断于 10/60，Level 3 仅覆盖低水平 zb 案 + 1 条 fz；v1→v2 的对比同时混杂了 prompt 修订、判分者更换、v1 数据缺陷三项因素，只能作方向性参考 |
