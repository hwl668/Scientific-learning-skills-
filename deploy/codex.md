# 部署到 OpenAI Codex、API 或 ChatGPT

## 选择加载方式

- 当前宿主支持 Agent Skills 发现时，优先按宿主文档加载 `skills/<name>/` 目录。
- 当前宿主不支持 Skill 目录，或需要调用 OpenAI API/自定义 GPT 时，使用仓库自带的 Prompt Compiler 生成单一指令文件。

Skill 是行为指令，不是独立应用。实际遵循效果、文件访问和持久化能力取决于宿主、模型与沙箱权限。

## 方式一：生成合并指令

在仓库根目录运行：

```bash
# 加载全部 9 个 Skill
python -B -m learning_agent.compile --target codex --skills all --output codex-system-message.md --metadata
```

`codex-system-message.md` 会包含 `RULES.md`、选中的 `SKILL.md` 和记忆策略说明。`--metadata` 输出选中 Skill 和启发式 token 估算；实际 token 数以目标模型 tokenizer 为准。

上下文受限时，只编译需要的子 Skill：

```bash
python -B -m learning_agent.compile --target codex --skills fuzzy,problem,mistake --output codex-system-message.md --no-memory --metadata
```

`scientific-learning` 是兜底路由入口，只适合用户显式调用统一入口或意图真正模糊的场景。已能明确匹配的请求应直接加载/使用对应子 Skill。

## 方式二：在 OpenAI API 中使用

先安装 OpenAI Python SDK，并在环境变量中配置 `OPENAI_API_KEY` 和项目有权限使用的 `OPENAI_MODEL`。不要将 API key 写入仓库。

```python
import os
from pathlib import Path

from openai import OpenAI

instructions = Path("codex-system-message.md").read_text(encoding="utf-8")

client = OpenAI()
response = client.responses.create(
    model=os.environ["OPENAI_MODEL"],
    instructions=instructions,
    input="什么是极限？我第一次接触。",
)
print(response.output_text)
```

API 调用方负责保存会话状态、学习记录和复习日期；只把 Skill 编译进 `instructions` 不会自动提供持久化。

## 方式三：自定义 GPT

1. 用 `--target chatgpt` 和实际需要的 `--skills` 生成指令。
2. 将生成文件中的指令粘贴到自定义 GPT 的 Instructions，并确认没有超出当前产品限制。
3. 如果需要跨会话记忆，通过可用的工具/API 连接外部存储。

不要假设把 `SKILL.md` 仅作为知识库附件上传就等同于加载了行为指令。

## 验证边界

可用下列请求做手工 smoke check：

```text
我会算极限，但不理解 ε-N 定义到底在干什么。
```

预期回复先校准具体卡点，而不是只重复定义。这个手工检查只能验证单次行为，不能证明对新请求的稳定遵循率或真实学习效果。
