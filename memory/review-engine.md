---
name: review-engine
description: 所有内容记忆型 Skill 共享的间隔复习引擎规则。
---

# 共享复习引擎

所有内容记忆型 Skill（`word-deep-dive`、`text-memorizer`）使用此引擎管理间隔复习。

## 确定性 CLI（推荐路径）

本引擎的间隔规则、复习抽取和状态更新已经有确定性实现。**宿主环境有 Python 时，一律通过 CLI 读写记忆，不要手写 JSON**——手写容易造成字段漂移、日期格式错误和覆盖丢数据；手写 JSON 仅作为无 Python 平台（如纯网页对话）的回退方案，文件格式两者完全一致。

```bash
# 存入（幂等：重复 add 只刷新内容字段，保留复习状态）
python -m learning_agent.memory.cli add --skill word-deep-dive --id complimentary --word complimentary --exam 六级 --note "免费的；赞美的"
python -m learning_agent.memory.cli add --skill text-memorizer --id kp-1 --content "实践是检验真理的唯一标准" --module 真理观

# 抽取到期项（按遗忘风险 + 薄弱优先排序；--weak-only 只取薄弱项；--all 忽略间隔）
python -m learning_agent.memory.cli due --skill word-deep-dive --limit 6

# 记录自评结果（--correct 等价 quality=5；--wrong 等价 quality=1，重置间隔）
python -m learning_agent.memory.cli grade --skill word-deep-dive --id complimentary --correct

# 状态摘要 / 删除（--json 可获得机器可读输出）
python -m learning_agent.memory.cli status --skill word-deep-dive
python -m learning_agent.memory.cli remove --skill word-deep-dive --id complimentary
```

CLI 的存储位置与下文一致（`memory/{skill-name}/`），默认相对当前目录，可用 `--memory-root` 指定。写入是原子操作并自动保留 `.bak` 备份；遇到损坏的记忆文件会报错退出而不是当成空库覆盖。

## 存储格式

各 Skill 在自己的 `memory/{skill-name}/` 下存储数据。每条记忆记录必须包含以下字段：

```json
{
  "id": "唯一标识符",
  "content": "原始内容摘要",
  "created_at": "2026-05-31",
  "review_count": 0,
  "correct_streak": 0,
  "last_reviewed": null,
  "next_review": null,
  "interval_days": 1
}
```

## 间隔规则

```
初始间隔：1 天
正确：interval_days × 2  （1→2→4→8→16→32→64）
错误：interval_days = 1   （重置）
```

| 连续正确次数 | 间隔天数 | 状态 |
|------------|---------|------|
| 0 | 1 | 新学 |
| 1 | 2 | 复习中 |
| 2 | 4 | 复习中 |
| 3 | 8 | 复习中 |
| 4 | 16 | 复习中 |
| 5 | 32 | 已掌握（停推） |

## 复习抽取算法

当用户请求复习时：

1. 筛选 `next_review <= 今天` 的记录
2. 按优先级排序：
   - 优先级 1：`correct_streak = 0` 的记录（刚重置的，最需要巩固）
   - 优先级 2：`next_review` 最早的记录
3. 每次抽取 5-8 条（可配置）
4. 对每条记录执行检测 → 用户自评 → 更新

## 自评机制

复习时，先展示最小提示（如单词的中文释义、知识点的关键词），用户尝试回忆完整内容后自评：

- **正确**：`correct_streak += 1`，`interval_days *= 2`，`next_review = 今天 + interval_days`
- **错误**：`correct_streak = 0`，`interval_days = 1`，`next_review = 明天`

## 掌握标准

连续正确 5 次（`correct_streak >= 5`）→ 标记为 `mastered: true`，不再主动推送复习。但保留在数据中，用户可以请求"复习全部"时包含。

## SM-2 风格调度升级

Learning Agent Framework 提供 `learning_agent.memory.scheduler` 作为新的调度 baseline。它兼容现有字段，同时增加：

- `ease_factor`：题目的难度因子，答得越稳增长越快，答错会下降。
- `mastery_probability`：当前掌握概率估计。
- `forgetting_risk`：当前遗忘风险估计。
- `review_priority`：复习优先级，用于排序到期和薄弱项目。

复习质量使用 SM-2 语义：

| quality | 含义 |
|---------|------|
| 0-2 | 回忆失败，重置间隔 |
| 3-5 | 回忆成功，按质量调整间隔和 ease factor |

命令行示例：

```bash
python -m learning_agent.memory.scheduler '{"id":"limit","correct_streak":2,"interval_days":6}' --quality 5 --json
```

## 复习报告

每次复习结束后展示：

```
本轮复习：共 X 条
✅ 正确：Y 条（间隔延长）
❌ 错误：Z 条（间隔重置为 1 天）
📈 已掌握：累计 M 条
📅 下次复习：N 条在 X 天后
```
