# Contributing

欢迎贡献新的 Skill、改进现有 Skill、或提交学科案例。

## 最容易贡献的 5 件事（5 分钟起）

| 任务 | 说明 | 耗时 |
|------|------|------|
| 添加常见误区 | 在任意 SKILL.md 的常见误区表中加一行你踩过的坑 | 2 分钟 |
| 补充测试用例 | 在 `evals/test_cases.md` 中添加你遇到的真实问题 | 3 分钟 |
| 报告 bad case | 提 Issue：给出 AI 回复未遵循规范的例子 | 5 分钟 |
| 提交变式题 | 给任意 Skill 的测试样例增加一个变式题 | 5 分钟 |
| 翻译 | 将 README 或任意 SKILL.md 中的部分内容译为英文 | 10 分钟 |

## 贡献方式

1. **新增 Skill**：运行 `bash skill-creator.sh` 生成骨架，在 `skills/` 下填充 `SKILL.md`。
2. **改进 Skill**：直接修改对应 `SKILL.md`，确保符合 `evals/scoring_rubric.md` 的标准。
3. **新增学科案例**：在 `examples/` 下新建文件。
4. **新增测试用例**：在 `evals/test_cases.md` 中添加测试问题。

## 什么是一个好 Skill

参考 `templates/skill-template.md` 的完整结构。以下是最低要求和加分项：

### 最低要求

- [ ] YAML frontmatter（name, description）
- [ ] 诊断/输入判断环节
- [ ] 直觉解释（先于正式定义）
- [ ] 常见误区表格（至少 2 条，P0 强制）
- [ ] 1-2 道验证题/变式题
- [ ] 反例约束（"什么时候不要这样做"）

### 加分项

- [ ] 最小例题（数字干净、只涉及当前概念）
- [ ] 多视角解释（同一个概念从不同角度讲）
- [ ] 跨知识联系（"这个和你知道的 X 有什么关系"）
- [ ] Memory 系统定义（存什么、何时读写）

### 判断标准

用 `eval.py` 自测：`python eval.py --input-file skills/<your-skill>/SKILL.md`

合格线：≥ 14 分。

## Skill 设计原则

- 一个 Skill 只解决一类问题，不要混。
- 必须有诊断步骤，不能假设已知学习者状态。
- 面向高中到本科低年级学生，不过度复杂。
- 没有空泛鼓励语（"加油""坚持就是胜利"等）。
- 没有长篇百科式堆砌。

## 提交前检查

```bash
# 1. 验证 frontmatter 和结构
python eval.py --input-file skills/<name>/SKILL.md

# 2. 在 Claude Code 中实际测试
#    输入测试样例中的问题，确认输出符合预期
```

## 目录约定

```
skills/<skill-name>/SKILL.md    # Skill 定义（规范源）
memory/<skill-name>/            # 用户学习数据（.gitignore 忽略 JSON）
demo/                           # 演示 transcript
evals/                          # 测试集 + 评分标准
deploy/                         # 各平台部署指南
```
