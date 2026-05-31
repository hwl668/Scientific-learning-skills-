# 部署到 OpenAI Codex / GPT / o1 系列

## 概述

Codex 和 GPT 系列模型不直接支持 Skill 目录机制，但可以通过**系统消息（System Message）**或**自定义 GPTs** 加载指令集。

## 方式一：合成为单一 System Message

将本项目合成为一个完整的系统消息：

```bash
cd /path/to/scientific-learning-skills
python3 -c "
import glob, os

parts = []
# 加载总规则
parts.append(open('RULES.md').read())

# 加载所有 Skill
for f in sorted(glob.glob('skills/*/SKILL.md')):
    parts.append(open(f).read())

print('\n\n'.join(parts))
" > codex-system-message.txt
```

在 API 调用中：

```python
from openai import OpenAI

with open("codex-system-message.txt") as f:
    system_message = f.read()

client = OpenAI()
response = client.responses.create(
    model="gpt-5",
    instructions=system_message,
    input="什么是极限？我第一次接触。"
)
```

## 方式二：自定义 GPT

1. 打开 ChatGPT → 探索 GPTs → 创建
2. 在"Instructions"中粘贴 `RULES.md` 的内容
3. 上传 `skills/` 下的 SKILL.md 文件作为知识库附件
4. 或者在 Instructions 中追加所有 Skill 内容

## 方式三：只加载需要的 Skill

对于 token 敏感的场景，按需加载：

```bash
# 只加载 fuzzy-understanding 和 problem-solving
cat RULES.md > custom-system.txt
cat skills/fuzzy-understanding/SKILL.md >> custom-system.txt
cat skills/problem-solving/SKILL.md >> custom-system.txt
```

## 注意事项

- **Token 预算**：全部 8 个 Skill 合成后约 20K-30K tokens。如果模型上下文窗口较小，建议按需加载 2-3 个 Skill。
- **o1/o3 系列**：这些模型的系统消息会被转为用户消息。确认规则内容以用户消息形式传入也能被遵循。
- **Memory**：GPT 模型无原生文件系统。Memory 功能（间隔复习、薄弱点追踪）需要外部存储支持（如通过 Function Calling 访问数据库或文件 API）。

## 验证

使用 API 或 ChatGPT 界面发送：

```
> 我会算极限，但不理解 ε-N 定义到底在干什么。
```

应返回诊断型回复（明确指出卡点类型），而非单纯重复 ε-N 定义。
