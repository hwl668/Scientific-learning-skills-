# 测试者指南（Testing Guide）

谢谢你参与测试 Scientific Learning Skills。这是一套「诊断先于讲解」的 AI 学习辅导 Skill：先判断你卡在哪，再决定讲什么。本指南帮你 5 分钟装好、知道测什么、怎么反馈。

---

## 1. 安装（三选一）

### A. ZCode / Claude Code（推荐，最简单）

把本包里的 `skills/` 目录接入宿主的 skill 目录：

**Windows（ZCode）**

```powershell
# 假设本包解压到 D:\sls-test
cmd /c mklink /J "$env:USERPROFILE\.zcode\skills" "D:\sls-test\skills"
```

**Windows（Claude Code）**

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1 -Target D:\sls-test
```

**macOS / Linux**

```bash
ln -s /path/to/extracted/skills ~/.claude/skills   # Claude Code
ln -s /path/to/extracted/skills ~/.zcode/skills    # ZCode
```

然后**新开会话**（skill 在会话启动时加载）。

### B. 插件安装（Claude Code，免解压）

如果你拿到的是 GitHub 仓库而不是文件包：

```text
/plugin marketplace add hwl668/Scientific-learning-skills-
/plugin install scientific-learning-skills@scientific-learning-skills
```

### C. 完整安装（含记忆功能）

记忆复习（单词/背诵的间隔复习）依赖 Python CLI。装好 Python 3.10+ 后在本目录执行：

```bash
python -m pip install -e .
python -m learning_agent.memory.cli status --skill word-deep-dive
```

Windows 上如果 `python` 提示找不到（装完 Python 没重启终端），用 `learning-memory` 命令代替（`setup.ps1` 会自动安装该别名）。

## 2. 冒烟测试清单（12 条提示词，逐条粘贴）

> 更多分类题目（含压力测试和学科事实抽查）见 [`test-questions.md`](./test-questions.md)；完整 100 题机器可读版在 `evals/bench/dev.synthetic.jsonl`。

| # | 提示词 | 应该看到什么 |
|---|--------|-------------|
| 1 | `!complimentary 六级` | 词典卡片 + 已存入记忆；考频写「常考（经验判断）」而非编造数据 |
| 2 | `复习单词` | 抽词出填空题让你回忆，不是直接给释义 |
| 3 | `✅`（复习时自评） | 间隔推进 1天→2天；后台应调用 CLI 而非手写 JSON |
| 4 | `单词记忆状态` | 真实统计（总数/连击/薄弱），来自 memory/ 文件 |
| 5 | `什么是极限？我第一次接触。` | 直觉类比先行，不上来就甩 ε-δ；结尾有自测 + 误区表 |
| 6 | `我会算矩阵乘法，但不知道矩阵到底在算什么。` | **先诊断卡点或追问**，只修卡住的部分，有变式题 |
| 7 | `这题我做错了：ln(x²-1) 的定义域，我写 x>1，标准答案是 x<-1 或 x>1，帮我看看为什么错。` | 重现错误思路 → 归类错因 → 检查清单 → 变式 |
| 8 | `两个月怎么学完线性代数，每天 1.5 小时，目标期末及格。` | 先校准基础再排计划，有检测标准 |
| 9 | `我每天背单词还是忘，怎么办` | 路由到单词记忆（不是给你排学习计划表） |
| 10 | `考研英语和六级英语有什么区别` | 进入概念辨析诊断，不是泛泛对比 |
| 11 | `学习报告` | 跨 skill 汇总：复习状态 + 薄弱点 + 建议（需完整安装 C） |
| 12 | `这题怎么做：求 lim(x→0)(e^x - 1 - x)/x²。` | 分步推演 + 每步说为什么，不直接给答案 |

重点观察三件事：**是否先诊断再讲解**、**误区表是不是真实具体**（不是凑数）、**记忆数据是否真的落在了项目目录的 `memory/` 下**。

## 3. 反馈模板

每条问题反馈请包含：

```text
提示词：#6（矩阵乘法）
宿主/模型：ZCode + GLM（写你实际用的）
期望：先诊断卡点
实际：（贴出关键输出片段，或截图）
问题类型：路由错误 / 诊断不准 / 内容错误 / 误区表凑数 / 其他
严重度：阻断 / 难受 / 小瑕疵
```

## 4. 已知边界（测之前先知道）

- Skill 是 Markdown 指令集，最终行为取决于宿主模型；同样的 Skill 在不同模型上遵循度不同——这正是我们要测的
- 静态评测（eval.py）只检查输出结构，不验证学科事实；发现**知识性错误**请优先反馈
- 记忆数据是本地文件（`memory/` 目录），删除对应目录即清空；不会上传
- 无 Python 的环境会退化为手写 JSON 维护记忆——如遇到格式错误请截图反馈

## 5. 隐私

你的学习记录（查过的词、背过的题）只存在本机 `memory/` 目录，反馈时**不需要**提交该目录；如提交请自行脱敏。
