# 部署到 OpenClaw / Open-Interpreter / 类 Claude Code 客户端

## 通用方法

OpenClaw 等客户端支持通过**自定义系统提示（System Prompt）**或**Skills 目录**加载外部指令。本项目的 Skills 本质上是结构化 Markdown 指令集，可以直接注入。

## 方式一：Skills 目录加载

如果客户端支持类似 Claude Code 的 `.skills/` 机制：

```bash
# 将 skills 目录复制或链接到客户端期望的位置
ln -s /path/to/scientific-learning-skills/skills /path/to/client/skills

# 将 RULES.md 作为系统级引导指令加载
cp /path/to/scientific-learning-skills/RULES.md /path/to/client/rules.md
```

## 方式二：系统提示注入

将所有 Skill 和规则拼合成一个完整的系统提示：

```bash
# 生成系统提示文件
cd /path/to/scientific-learning-skills
{
  echo "# 理工科学习智能体规则"
  cat RULES.md
  echo ""
  echo "# 可用 Skills"
  for skill in skills/*/SKILL.md; do
    echo ""
    echo "---"
    cat "$skill"
  done
} > system-prompt.md
```

将 `system-prompt.md` 的内容粘贴到客户端的系统提示设置中。

## 方式三：按需加载

只加载需要的 Skill，而不是全部：

```bash
# 例如只需要英语单词和解题 Skill
cat RULES.md > custom-prompt.md
cat skills/word-deep-dive/SKILL.md >> custom-prompt.md
cat skills/problem-solving/SKILL.md >> custom-prompt.md
```

## Memory 存储

确认 `memory/` 目录在客户端的工作目录下可读写。如果客户端的文件系统受限，修改 RULES.md 中的存储路径为绝对路径。

## 验证

发送测试消息：

```
> 我会算矩阵乘法，但不知道矩阵到底表示什么。
```

应返回包含"诊断""卡点""修复"的结构化回复，而非百科式的矩阵定义。
