# 部署到 ZCode

ZCode 原生支持 Claude 格式的 `SKILL.md`，无需 Claude Code 即可使用本项目。

## 用户级安装（所有项目可用）

把仓库的 `skills/` 以 junction 接入 ZCode 用户级 skill 目录（Windows；需要开发者模式的符号链接不必要，junction 免管理员）：

```powershell
cmd /c mklink /J "$env:USERPROFILE\.zcode\skills" "D:\path\to\Scientific-learning-skills\skills"
```

Linux / macOS / WSL Linux 文件系统：

```bash
ln -s /path/to/Scientific-learning-skills/skills ~/.zcode/skills
```

新开会话后在「设置 → Skills」里应能看到 9 个 skill（scientific-learning + 8 个子 skill）。

## 工作区级安装（只在学习项目里生效）

在目标项目里：

```powershell
mkdir .zcode
cmd /c mklink /J .zcode\skills "D:\path\to\Scientific-learning-skills\skills"
copy "D:\path\to\Scientific-learning-skills\RULES.md" AGENTS.md
```

`AGENTS.md`（工作区指令文件）承载 `RULES.md` 的跨 skill 规则：决策树、转交规则、学习报告触发词。只想轻度体验时可以省略——每份 `SKILL.md` 内嵌了自己的核心流程和间隔复习规则。

## Memory 与复习 CLI

内容记忆（单词/背诵）写在当前项目的 `memory/` 下，复习状态用确定性 CLI 读写：

```bash
python -m learning_agent.memory.cli status --skill word-deep-dive
```

需要项目已 `pip install -e` 本仓库（或 `pip install scientific-learning-skills`）。

## 注意

- 用户级安装会让 9 个 skill 在你的**所有**工作区可见。coding 工作里说「卡住了」这类词可能误触发 `problem-solving`；不想要时删除 junction 即可（junction 删除不影响源仓库）：`rmdir "$env:USERPROFILE\.zcode\skills"`。
- 学习类对话请在学习项目目录里开（或接受记忆数据落在当前项目 `memory/`）。
