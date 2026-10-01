# 部署到 Claude Code

## 插件安装（推荐，免克隆）

仓库提供 `.claude-plugin/` 清单，可直接作为 Claude Code 插件安装：

```text
/plugin marketplace add hwl668/Scientific-learning-skills-
/plugin install scientific-learning-skills@scientific-learning-skills
```

注意：插件方式只安装 Skills 本身；Memory 数据和 `python -m learning_agent.memory.cli` 工具仍建议按下面的克隆方式使用。

## 自动加载（克隆方式）

Claude Code 自动读取 `.claude/skills/` 下的 Skill 文件和 `.claude/CLAUDE.md` 规则文件。本项目已预置符号链接：

```bash
# 克隆后无需额外配置，直接使用
cd scientific-learning-skills
claude
```

## 手动安装到已有项目

```bash
# 方式一：符号链接（推荐，保持同步更新）
ln -s /path/to/scientific-learning-skills/skills .claude/skills
ln -s /path/to/scientific-learning-skills/RULES.md .claude/CLAUDE.md

# 方式二：复制
cp -r /path/to/scientific-learning-skills/skills .claude/skills
cp /path/to/scientific-learning-skills/RULES.md .claude/CLAUDE.md
```

## Windows

Windows 上不要用 WSL 的 `ln -s` 写到 NTFS 盘（`/mnt/...`）——那样创建的符号链接对 Windows 原生程序不可读（WinError 1920），Claude Code 读不到 Skills。用 `setup.ps1`（junction 方案，目录链接不需要管理员权限）：

```powershell
# 部署本仓库自身
powershell -ExecutionPolicy Bypass -File setup.ps1

# 或部署到另一个项目（junction 指回本仓库，repo 更新自动生效）
powershell -ExecutionPolicy Bypass -File setup.ps1 -Target D:\path\to\your-project
```

注意：Windows 检出仓库时，git 会把 `.claude/skills` 符号链接落成普通文本文件；`setup.ps1` 会自动替换成 junction。`CLAUDE.md` 是复制而非链接，`RULES.md` 更新后需要重新复制。

## Memory 存储

Memory 数据默认写入项目根目录的 `memory/` 下。如需自定义路径，在 RULES.md 中搜索 `memory/` 并替换为目标路径。

## 验证

```bash
claude
# 在对话中输入：什么是极限？我第一次接触。
# 如果输出从直觉出发而非堆公式，说明 Skill 已加载。
```
