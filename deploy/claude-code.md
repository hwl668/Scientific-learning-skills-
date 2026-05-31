# 部署到 Claude Code

## 自动加载（推荐）

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

## Memory 存储

Memory 数据默认写入项目根目录的 `memory/` 下。如需自定义路径，在 RULES.md 中搜索 `memory/` 并替换为目标路径。

## 验证

```bash
claude
# 在对话中输入：什么是极限？我第一次接触。
# 如果输出从直觉出发而非堆公式，说明 Skill 已加载。
```
