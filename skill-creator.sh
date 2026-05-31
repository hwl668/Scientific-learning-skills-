#!/usr/bin/env bash
set -euo pipefail

# Scientific Learning Skills — Skill 脚手架工具
# 交互式创建新 Skill 的骨架文件

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"

echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  Skill 脚手架 — 创建新的学习 Skill${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
echo

# ── 收集信息 ──────────────────────────────────────────────

read -r -p "$(echo -e "${BOLD}Skill 名称${NC} (短横线分隔，如 physics-concept): ")" SKILL_NAME
if [ -z "$SKILL_NAME" ]; then
    echo -e "  ${RED}名称不能为空${NC}"
    exit 1
fi

# 检查是否已存在
SKILL_DIR="$SKILLS_DIR/$SKILL_NAME"
if [ -d "$SKILL_DIR" ]; then
    echo -e "  ${RED}Skills/$SKILL_NAME 已存在${NC}"
    exit 1
fi

read -r -p "$(echo -e "${BOLD}一句话描述${NC} (何时触发): ")" SKILL_DESC
if [ -z "$SKILL_DESC" ]; then
    SKILL_DESC="TODO: 描述触发条件"
fi

echo
echo -e "  ${DIM}可选信息（回车跳过）${NC}"

read -r -p "$(echo -e "${BOLD}适用场景${NC} (逗号分隔): ")" SCENARIOS_INPUT
read -r -p "$(echo -e "${BOLD}输入的示例问题${NC}: ")" EXAMPLE_INPUT

echo

# ── 构建场景列表 ──────────────────────────────────────────
SCENARIOS_MD=""
if [ -n "$SCENARIOS_INPUT" ]; then
    IFS=',' read -ra SCENARIOS <<< "$SCENARIOS_INPUT"
    for s in "${SCENARIOS[@]}"; do
        s_trimmed="$(echo "$s" | xargs)"
        [ -n "$s_trimmed" ] && SCENARIOS_MD+="- $s_trimmed"$'\n'
    done
fi

if [ -z "$SCENARIOS_MD" ]; then
    SCENARIOS_MD="- [待补充]"$'\n'
fi

# ── 生成 SKILL.md ─────────────────────────────────────────

mkdir -p "$SKILL_DIR"

cat > "$SKILL_DIR/SKILL.md" <<SKILLEOF
---
name: ${SKILL_NAME}
description: ${SKILL_DESC}
---

# 目标

[TODO: 这个 Skill 要解决什么问题？一句话。]

# 适用场景

${SCENARIOS_MD}
# 输入判断

[TODO: 打开 Skill 后，先做什么判断？问什么问题？]

请先追问以下问题，判断学习者当前状态：
1. [问题 1]
2. [问题 2]

# 执行流程

\`\`\`
步骤 1 → 步骤 2 → 步骤 3 → 步骤 N
\`\`\`

## 1. 诊断

[判断学习者卡在哪里]

## 2. 直觉解释

[用生活/图像类比建立直觉]

## 3. 正式定义

[精确定义，逐部分解释含义]

## 4. 最小例题

[一个能跑通的最简单例子]

## 5. 变式迁移

[换条件/场景，验证真实理解]

## 6. 常见误区

[TODO: 至少 2 个，见下表]

| 常见错误 | 为什么错 | 正确理解 |
|----------|---------|---------|
| [错误 1] | [原因]  | [正确]  |
| [错误 2] | [原因]  | [正确]  |

## 7. 自测题

[TODO: 1-2 道检测题]

# 输出格式

\`\`\`markdown
## 诊断
[卡点判断]

## 讲解
[直觉 → 定义 → 例题]

## 常见误区
[表格]

## 验证
[变式题/自测题]
\`\`\`

# 反例：什么时候不要这样做

- [不要做 X]
- [不要做 Y]

# Memory 系统

- 类型：分析记忆（不参与间隔复习）
- 存储内容：[存什么洞察]
- 存储位置：\`memory/${SKILL_NAME}/\`

# 测试样例

**输入**：${EXAMPLE_INPUT:-[TODO: 具体用户输入]}

**期望输出方向**：
1. [应包含诊断环节]
2. [应包含直觉解释]
3. [应包含常见误区表格]
4. [应避免百科式堆知识]
SKILLEOF

echo
echo -e "${GREEN}${BOLD}✅ Skill 骨架已生成：${NC}"
echo -e "   skills/${SKILL_NAME}/SKILL.md"
echo

# ── 初始化 Memory 目录 ────────────────────────────────────
MEMORY_DIR="$SCRIPT_DIR/memory/$SKILL_NAME"
mkdir -p "$MEMORY_DIR"
echo -e "   memory/${SKILL_NAME}/"
echo

# ── 结构检查清单 ──────────────────────────────────────────
echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}  结构检查清单${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════${NC}"
echo

CHECKS=(
    "├─ ${CYAN}诊断环节${NC}        → 输入判断 + 执行流程第 1 步"
    "├─ ${CYAN}直觉解释${NC}        → 执行流程第 2 步"
    "├─ ${CYAN}正式定义${NC}        → 执行流程第 3 步"
    "├─ ${CYAN}最小例题${NC}        → 执行流程第 4 步"
    "├─ ${CYAN}变式迁移${NC}        → 执行流程第 5 步"
    "├─ ${CYAN}常见误区${NC}        → 执行流程第 6 步（P0 强制）"
    "├─ ${CYAN}自测题${NC}          → 执行流程第 7 步"
    "├─ ${CYAN}反例约束${NC}        → 反例部分"
    "├─ ${CYAN}Memory 定义${NC}     → Memory 系统部分"
    "├─ ${CYAN}测试样例${NC}        → 测试样例部分"
    "└─ ${YELLOW}TODO 字段${NC}      → 需要手动填写的内容"
)

for check in "${CHECKS[@]}"; do
    echo -e "  $check"
done

echo
echo -e "${BOLD}下一步：${NC}"
echo -e "  1. 编辑 skills/${SKILL_NAME}/SKILL.md，填充所有 ${YELLOW}[TODO]${NC} 项"
echo -e "  2. 在其中测试：claude  后输入测试样例中的问题"
echo -e "  3. 用 evals/scoring_rubric.md 的 10 维度自评打分"
echo -e "  4. 达标后提交 PR！"
echo
