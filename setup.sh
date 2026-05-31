#!/usr/bin/env bash
set -euo pipefail

# Scientific Learning Skills — 一键安装脚本
# 自动检测 AI 工具，创建所需符号链接和目录结构

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "${BOLD}${CYAN}========================================${NC}"
    echo -e "${BOLD}${CYAN}  Scientific Learning Skills — 安装${NC}"
    echo -e "${BOLD}${CYAN}========================================${NC}"
    echo
}

print_ok()   { echo -e "  ${GREEN}[OK]${NC} $1"; }
print_warn(){ echo -e "  ${YELLOW}[WARN]${NC} $1"; }
print_err() { echo -e "  ${RED}[ERR]${NC} $1"; }

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_SRC="$SCRIPT_DIR/skills"
RULES_SRC="$SCRIPT_DIR/RULES.md"
MEMORY_SRC="$SCRIPT_DIR/memory"

# 需要初始化的 memory 子目录（分析记忆 + 内容记忆）
MEMORY_DIRS=(
    zero-base-learning
    scientific-learning
    fuzzy-understanding
    deepening-learning
    problem-solving
    mistake-review
    study-plan-builder
    word-deep-dive
    text-memorizer
)

DETECTED_TOOLS=0

# ── 检测 AI 工具 ──────────────────────────────────────────
detect_tools() {
    echo -e "${BOLD}检测 AI 工具...${NC}"
    echo

    # Claude Code
    if command -v claude &>/dev/null; then
        print_ok "Claude Code 已安装"
        DETECTED_TOOLS=$((DETECTED_TOOLS + 1))

        # 确保 .claude 目录存在
        mkdir -p "$SCRIPT_DIR/.claude/skills"

        # 创建 skills 符号链接
        for skill_dir in "$SKILLS_SRC"/*/; do
            local name=$(basename "$skill_dir")
            local link="$SCRIPT_DIR/.claude/skills/$name"
            if [ -L "$link" ]; then
                print_warn "skill 链接已存在: $name → 跳过"
            elif [ -d "$link" ]; then
                print_warn "skill 目录已存在(非链接): $name → 跳过"
            else
                ln -s "$skill_dir" "$link" 2>/dev/null || {
                    # macOS 不支持 ln -r，用绝对路径
                    local abs_skill_dir="$SKILLS_SRC/$name"
                    ln -s "$abs_skill_dir" "$link" 2>/dev/null || print_err "创建链接失败: $name"
                    continue
                }
                print_ok "skill 链接: $name → .claude/skills/$name"
            fi
        done

        # 创建 CLAUDE.md 链接
        local claude_md="$SCRIPT_DIR/.claude/CLAUDE.md"
        if [ -L "$claude_md" ] || [ -f "$claude_md" ]; then
            print_warn ".claude/CLAUDE.md 已存在 → 跳过"
        else
            ln -s "$RULES_SRC" "$claude_md" 2>/dev/null || {
                ln -s "$(readlink -f "$RULES_SRC" 2>/dev/null || echo "$SCRIPT_DIR/RULES.md")" "$claude_md" 2>/dev/null || print_err "创建 CLAUDE.md 链接失败"
                return 0
            }
            print_ok "CLAUDE.md 链接: RULES.md → .claude/CLAUDE.md"
        fi
        echo
    else
        print_warn "未检测到 Claude Code (claude 命令)"
        echo "  安装: npm install -g @anthropic-ai/claude-code"
        echo
    fi

    # OpenAI Codex CLI
    if command -v codex &>/dev/null; then
        print_ok "OpenAI Codex CLI 已安装"
        DETECTED_TOOLS=$((DETECTED_TOOLS + 1))
        echo
    fi

    # 通用提示
    if [ $DETECTED_TOOLS -eq 0 ]; then
        print_warn "未检测到支持的 AI 工具"
        echo "  你仍可以通过系统提示注入使用（见 deploy/ 目录）"
        echo
    fi
}

# ── 初始化 Memory 目录 ──────────────────────────────────────
init_memory() {
    echo -e "${BOLD}初始化 Memory 目录...${NC}"
    echo

    mkdir -p "$SCRIPT_DIR/memory"

    for dir in "${MEMORY_DIRS[@]}"; do
        local target="$SCRIPT_DIR/memory/$dir"
        if [ -d "$target" ]; then
            print_warn "memory/$dir 已存在 → 跳过"
        else
            mkdir -p "$target"
            print_ok "创建 memory/$dir/"
        fi
    done
    echo
}

# ── 生成 .gitignore 补充 ────────────────────────────────────
ensure_gitignore() {
    if ! grep -q "^# Claude$" "$SCRIPT_DIR/.gitignore" 2>/dev/null; then
        cat >> "$SCRIPT_DIR/.gitignore" <<'GITIGNORE'

# Claude
.claude/cache/
.claude/sessions/
GITIGNORE
        print_ok ".gitignore 已更新"
    fi
}

# ── 安装摘要 ────────────────────────────────────────────────
print_summary() {
    echo -e "${BOLD}${CYAN}========================================${NC}"
    echo -e "${BOLD}${CYAN}  安装完成${NC}"
    echo -e "${BOLD}${CYAN}========================================${NC}"
    echo
    echo -e "  项目路径:   ${GREEN}$SCRIPT_DIR${NC}"
    echo -e "  检测到工具: ${GREEN}$DETECTED_TOOLS${NC} 个"
    echo -e "  Skills:     ${GREEN}$(ls -1 "$SKILLS_SRC" | wc -l)${NC} 个"
    echo
    echo -e "${BOLD}快速开始:${NC}"
    echo "  cd $SCRIPT_DIR"
    echo
    if command -v claude &>/dev/null; then
        echo "  claude    # 启动 Claude Code，Skills 自动加载"
        echo
    fi
    echo -e "${BOLD}Memory 管理:${NC}"
    echo "  python review.py              # 查看复习状态面板"
    echo "  bash skill-creator.sh         # 创建自定义 Skill"
    echo
    echo -e "${BOLD}部署到其他平台:${NC}"
    echo "  cat deploy/generic.md         # 通用部署指南"
    echo
}

# ── 主流程 ──────────────────────────────────────────────────
main() {
    print_header
    detect_tools
    init_memory
    ensure_gitignore
    print_summary
}

main
