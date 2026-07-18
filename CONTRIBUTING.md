# Contributing

欢迎贡献新的 Skill、改进现有 Skill，或提交学科案例与失败用例。请区分两类检查：仓库校验器检查 Skill 定义本身；输出评分器检查由 Skill 生成的教学回答。后者不能证明真实学习效果。

## 最容易贡献的 5 件事（2 分钟起）

| 任务 | 说明 | 参考耗时 |
|------|------|----------|
| 添加常见误区 | 为某个 Skill 补充真实、具体、可纠正的误区 | 2 分钟 |
| 补充路由或诊断样例 | 在 `data/` 的 JSONL 测试集中添加边界用例 | 3 分钟 |
| 报告 bad case | 提交可复现的输入、实际输出、期望行为与环境 | 5 分钟 |
| 提交静态教学样例 | 在 `evals/cases/smoke.jsonl` 中补充人工审阅过的输出 | 10 分钟 |
| 改进文档或翻译 | 修正不准确的能力声明、命令或中英文内容 | 10 分钟 |

## 贡献方式

1. **新增 Skill**：运行 `bash skill-creator.sh` 生成骨架，在 `skills/<name>/SKILL.md` 中完成定义。
2. **改进 Skill**：修改对应 `SKILL.md`，并遵守 `RULES.md` 与 `evals/scoring_rubric.md`。
3. **新增学科案例**：在 `examples/` 下添加文件，并标明它是说明性案例还是实际测试记录。
4. **新增评测样例**：静态输出放入 `evals/cases/`；路由、诊断样例放入 `data/` 对应 JSONL 文件。

## 什么是一个好 Skill

参考 `templates/skill-template.md`。最低要求包括：

- [ ] 合法且无重复键的 YAML frontmatter，`name` 与目录名一致
- [ ] 先判断学习者状态，再选择解释深度
- [ ] 直觉解释先于正式定义
- [ ] 实质性教学输出包含至少 2 行真实数据的“常见误区”表格
- [ ] 提供 1–2 道自测题或变式题
- [ ] 给出反例或适用边界

可选增强项：最小例题、多视角解释、跨知识联系，以及明确的数据保存与清除规则。

## 两类验收，不要混用

### 1. Skill 定义校验

这一步检查 frontmatter、目录名、字段类型和 P0 结构约束：

```bash
python -B -m learning_agent.validate_skills
```

### 2. 教学输出评分

`eval.py` 的输入应当是某次生成的教学回答，不是 `SKILL.md` 提示词文件：

```bash
python eval.py --input-file path/to/generated-answer.md --skill fuzzy-understanding
```

当前门禁要求总分至少 14/20，且“常见误区/关键误区”和“避免空泛”都必须满 2 分。它只表示静态结构规则基本达标，不代表学生真正学会，也不代表线上 A/B 测试结果。需要报告教学有效性时，请提供真实用户、任务、基线、样本量与结果指标。

## Skill 设计原则

- 一个 Skill 聚焦一类学习问题；路由层负责分流。
- 不假设学习者已经掌握前置知识。
- 面向高中到本科低年级理工科学生，避免循环依赖高阶概念。
- 不使用空泛鼓励语，也不堆砌百科式内容。
- 示例、合成数据、静态评分和真实用户证据必须分别标注。

## 提交前检查

```bash
# 严格校验所有 Skill
python -B -m learning_agent.validate_skills

# 完整回归测试
python -B -m unittest discover -s tests -v

# 路由、诊断与静态教学输出评测
python -B -m learning_agent.router --eval
python -B -m learning_agent.diagnosis --eval
python -B -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report json
```

提交前还应人工检查新增样例是否泄露个人信息、是否夸大证据，以及失败路径是否给出可行动的错误提示。

## 目录约定

```text
skills/<skill-name>/SKILL.md       # Skill 定义（规范源）
memory/<skill-name>/               # 本地学习数据；默认不提交
demo/                              # 人工编写的静态行为示例，不是在线 transcript
evals/                             # 静态测试集与评分规则
learning_agent/resources/          # 随安装包发布的数据与安全模型 artifact
deploy/                            # 各平台部署指南
```
