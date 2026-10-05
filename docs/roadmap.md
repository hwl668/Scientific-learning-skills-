# Roadmap

## M1: Demo & Eval（当前冲刺）

- [x] `setup.sh` 为 Claude Code 创建 Skill 链接并初始化本地 memory
- [x] `review.py` 复习进度面板
- [x] `eval.py` 规则检测评测脚本
- [x] `demo/` 仓库维护者编写的静态行为示例（非真实用户 transcript）
- [x] GitHub Actions CI（frontmatter + P0 + eval-quick + links）
- [x] `README.en.md` 英文版
- [x] `CONTRIBUTING.md` 贡献指南完善
- [x] 学科扩展方案（`docs/subject-expansion-plan.md`）
- [x] `plugin.json` 插件清单（`.claude-plugin/plugin.json` + `marketplace.json`，支持 `/plugin marketplace add` 一键安装）

## v0.4: 工程强化（进行中）

- [x] 确定性 Memory CLI `learning_agent.memory.cli`（add/due/grade/status/remove）：复习状态改由脚本读写，原子写 + `.bak` 备份 + 损坏报错；`review-engine.md` 与两个内容记忆 Skill 已同步「CLI 优先」
- [x] 路由三源一致性门禁 `learning_agent.validate_routing`：router 触发词 ↔ `scientific-learning` 路由表 ↔ `RULES.md` 决策树 ↔ 考试名单，已接入 CI 并修复 43 处漂移（含 word-deep-dive 缺失的「四级」）
- [x] 考频断言防幻觉措辞：`word-deep-dive` 考法边界 + `RULES.md` 事实边界条款
- [x] 本地实测（独立项目部署 + 模拟辅导会话）驱动修复：「背单词」「有什么区别」触发词、Memory CLI「当天到期」off-by-one、`setup.ps1`（Windows junction 部署）+ `learning-memory` PATH 兜底别名
- [x] 分发升级：`.claude-plugin/plugin.json` + `marketplace.json`（一键插件安装）、`npx skills add` 入口、`deploy/zcode.md`；README 第一屏改为「诊断优先」slogan + 架构图
- [x] LearningSkillBench v0.1 设计定稿（`docs/learning-skill-bench.md`：三条件对照 × 三层评测 + TER 靶向率）
- [x] **P1：实施 LearningSkillBench**——`learning_agent/bench/`（runner/judge/report；Anthropic+OpenAI 兼容、断点续跑、mock 自检）+ 数据分层 `dev.synthetic.jsonl`(100) / `test.public.jsonl`(50，MathDial CC BY-SA 派生 half-real) + schema/路由门禁入 CI + 20 条 gold 标注
- [x] 首次真实 pilot：20 case × 3 条件 ×（Level 2 judge + TER + Level 3 模拟学习者）→ `evals/bench/results/pilot20-v1.md`；README 证据段改为引用实测报告
- [x] README 动态 demo：CSS 动画 SVG 分镜（`scripts/generate_demo_svg.py` + `docs/assets/demo-scenario.json`，zh/en × light/dark，reduced-motion 定格回退）+ bench-card.svg 由 `bench-card` workflow 从 `evals/bench/results/` 自动重渲（数字与已提交报告强一致，测试锁定）
- [ ] v0.5 候选：放量 dev 全量 + public test；TER 人工 agreement 标注（30–50 条）；test.private holdout 解锁流程
- [ ] 真机触发测试：8 个子 skill 的 description 在宿主中的触发/误触率
- [ ] P2 候选：统一 learner state（跨 skill 学习者画像）、诊断六类扩成分类树 + 干预策略映射、学科误区包（subject packs）

## v0.2: Learning Agent Framework Prototype

- [x] Skill Router + `data/routing_cases.jsonl`
- [x] Cognitive Diagnosis Engine + `data/diagnosis_cases.jsonl`
- [x] SM-2 style Memory Scheduler
- [x] Eval Runner split into `learning_agent/eval/`
- [x] Prompt Compiler for multi-platform system prompts
- [x] Subject Case Library + `data/subject_cases.jsonl`
- [x] v0.2 summary doc: `docs/v0.2-summary.md`

## M2: 信任与传播

- [ ] v0.1 vs v0.2 对比报告
- [ ] 真实学习 traces 记录与反馈闭环
- [ ] Subject case coverage metrics
- [x] Eval regression gate（8 个子 Skill 静态结构 smoke + CI 阈值）
- [ ] evals 扩充：接入真实 model-as-judge 打分（LLM 评分）
- [ ] 中英双语完整测试集
- [ ] 3 个 killer case 博客文章（矩阵/极限/英语词汇）
- [ ] Hacker News / Reddit / X 发布

## M3: 内容生态

- [ ] 社区贡献的前 5 个外部 Skill
- [ ] Anki / Quizlet 导出（word-deep-dive + text-memorizer）
- [ ] 记忆数据可视化（掌握曲线、薄弱分布）
- [ ] 按学科分类的 Skill 目录（物理、化学、CS）

## M4: 深度集成

- [ ] MCP 连接 Notion：单词/笔记自动同步
- [ ] MCP 连接 Anki：一键生成卡片
- [ ] Claude.ai / ChatGPT GPTs 一键安装
- [ ] VS Code / Cursor 扩展

## v1.0

- [ ] 8 个子 Skill 和 1 个总入口 Skill 经过 100+ 用户验证
- [ ] 完整的社区贡献体系（skill registry + review process）
- [ ] 可复现的 benchmark 论文/技术报告
