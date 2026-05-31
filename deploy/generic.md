# 部署到任意智能体（通用方法）

## 核心思路

本项目的 Skills 本质上就是**结构化的 Markdown 指令集**。任何支持系统提示的 AI 智能体都可以使用。

## 最小部署步骤

### 1. 合成系统提示

```bash
cd scientific-learning-skills

# 生成完整系统提示
cat RULES.md > agent-system-prompt.md
for skill in skills/*/SKILL.md; do
  echo "" >> agent-system-prompt.md
  cat "$skill" >> agent-system-prompt.md
done
```

### 2. 注入智能体

将 `agent-system-prompt.md` 的内容作为智能体的系统提示注入：

- **Web UI 类工具**（ChatGPT、Claude.ai、Poe、Gemini 等）：粘贴到自定义指令/系统提示设置框
- **API 类工具**：作为 `system` 消息传入
- **IDE 插件**（Cursor、Copilot、Cline 等）：放入项目根目录的规则文件中
- **本地客户端**（Ollama + Open WebUI、LM Studio 等）：在模型设置中加载

### 3. Token 优化

全部 9 个 Skill（1 个总入口 + 8 个子 skill）约 20K-30K tokens。如需精简：

```bash
# 只保留总入口，让它做路由和简版兜底
cat RULES.md > router-prompt.md
cat skills/scientific-learning/SKILL.md >> router-prompt.md

# 只保留最常用的 3-4 个 Skill
cat RULES.md > minimal-prompt.md
cat skills/scientific-learning/SKILL.md >> minimal-prompt.md
cat skills/fuzzy-understanding/SKILL.md >> minimal-prompt.md
cat skills/problem-solving/SKILL.md >> minimal-prompt.md
cat skills/mistake-review/SKILL.md >> minimal-prompt.md
cat skills/word-deep-dive/SKILL.md >> minimal-prompt.md
```

### 4. Memory 处理

本项目的 Memory 系统（间隔复习、薄弱点追踪）依赖本地文件系统。对于无文件系统访问的智能体：

- **推荐**：禁用 Memory 功能，只使用 Skill 的诊断/讲解/解题能力
- **备选**：将 Memory 逻辑改为通过 Function Calling 访问外部数据库（需自行开发适配层）

---

## 各平台速查

| 平台 | 加载方式 | Memory 支持 |
|------|---------|------------|
| **Claude Code** | `.claude/skills/` 目录 | 原生文件系统 |
| **OpenClaw** | 系统提示注入或 Skills 目录 | 取决于运行时环境 |
| **ChatGPT** | 自定义 GPT Instructions | 无（需 Function Calling） |
| **Codex / API** | system message | 无（需外部存储 API） |
| **Cursor** | `.cursorrules` 或 Rules for AI | 有限（项目目录可写） |
| **Cline / Roo Code** | `.clinerules` 或自定义指令 | 取决于 VS Code 环境 |
| **Ollama + WebUI** | 模型系统提示 | 取决于部署环境 |
| **Gemini** | 系统指令 | 无（需 Google Cloud 存储） |

---

## 验证

无论哪个平台，用同一句话测试：

```
> 我会算矩阵乘法，但不知道矩阵到底在表示什么。
```

期望行为：
1. 不直接堆定义
2. 先追问理解状态
3. 输出包含"诊断""卡点""修复"结构
4. 有验证题和变式题

如果没有出现诊断结构，说明系统提示未正确加载或模型未遵循指令。检查：是否完整粘贴了 RULES.md 的内容？Skill 的 SKILL.md 是否也被加载？
