#!/usr/bin/env python3
"""Scientific Learning Skills — 评测脚本

对 AI 输出做规则检测打分。支持三种 rubric：
  concept  — 概念讲解 Skill（完整 10 维度）
  word     — 单词查询 Skill（跳过诊断/直觉，总分 16）
  baseline — 裸 AI 对照（评分展示，不参与 pass/fail）

用法:
  python eval.py                # 评测所有 demo（baseline 仅展示）
  python eval.py --quick        # 只测核心 skill demo（不含 baseline）
  python eval.py --all          # 含 baseline 在内的完整评测
  python eval.py --skill fuzzy-understanding
  python eval.py --input-file path.md
  python eval.py --input-text "..."
"""

import sys
import re
import json
from pathlib import Path

# ── 终端颜色 ──────────────────────────────────────────────
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"

PROJECT_ROOT = Path(__file__).resolve().parent
DEMO_DIR = PROJECT_ROOT / "demo"

STOP_MARKER = "<!-- eval:stop -->"

# ── 文件级标记 ────────────────────────────────────────────
RUBRIC_MARKER = re.compile(r"<!--\s*rubric:\s*(\w+)\s*-->")
BASELINE_MARKER = "<!-- rubric: baseline -->"


def parse_file_meta(text: str) -> dict:
    """从文件内容提取 rubric 标记"""
    rubric = "concept"
    is_baseline = False
    for line in text.split("\n")[:10]:
        m = RUBRIC_MARKER.search(line)
        if m:
            kind = m.group(1)
            if kind == "baseline":
                is_baseline = True
                rubric = "concept"
            elif kind in ("concept", "word"):
                rubric = kind
    return {"rubric": rubric, "is_baseline": is_baseline}


def extract_scorable(text: str) -> str:
    """截取 stop marker 之前的内容作为评分对象"""
    if STOP_MARKER in text:
        return text.split(STOP_MARKER)[0]
    return text


# ── 违规词 ────────────────────────────────────────────────

FORBIDDEN_PATTERNS = [
    r"加油", r"你能行", r"坚持就是胜利", r"多练练",
    r"你一定可以", r"相信自己", r"不要放弃",
    r"come on", r"you can do it",
]

SKIP_REASONING_PATTERNS = [
    r"显然", r"易知", r"众所周知", r"不难看出",
    r"obviously", r"clearly", r"it is easy to see",
]

# ── 通用评分维度 ──────────────────────────────────────────

def score_diagnosis(text: str) -> tuple[int, str]:
    diagnostic_keywords = ["诊断", "卡点", "先确认", "了解情况", "先判断", "先问", "定位"]
    diagnostic_questions = len(re.findall(r"[？?]", text))
    has_keywords = any(kw in text for kw in diagnostic_keywords)
    has_questions = diagnostic_questions >= 2
    if has_keywords and has_questions:
        return 2, "有诊断关键词 + 追问问题"
    elif has_keywords or has_questions:
        return 1, "有诊断意识但不充分"
    return 0, "无诊断环节"


def score_intuition(text: str) -> tuple[int, str]:
    intuition_patterns = [
        r"类比", r"像", r"想象", r"比如", r"假设你",
        r"直觉", r"画面", r"打个比方", r"生活",
        r"analogy", r"imagine", r"intuition",
    ]
    matches = sum(1 for p in intuition_patterns if re.search(p, text))
    if matches >= 3:  return 2, f"丰富的直觉/类比 ({matches} 处)"
    elif matches >= 1: return 1, f"有直觉元素 ({matches} 处)"
    return 0, "无直觉解释"


def score_formal_definition(text: str) -> tuple[int, str]:
    has_formal = bool(re.search(r"(定义|记作|记为|即|指的是|满足).{0,20}(如果|当|对任意|存在|使得|则)", text))
    has_math = bool(re.search(r"\$.*\$|lim|∑|∫|ε|δ|→|∀|∃", text))
    if has_formal and has_math: return 2, "有正式定义 + 符号解释"
    elif has_formal or has_math: return 1, "有定义但不够完整"
    elif len(text) > 300: return 1, "有解释但无正式定义"
    return 0, "无正式定义"


def score_example(text: str) -> tuple[int, str]:
    has_example = bool(re.search(r"(例如|例题|例[：:]|举个|比如|具体|自测)", text))
    has_step = bool(re.search(r"(步骤|第\d步|首先.*然后|1\..*2\..*3\.)", text))
    has_worked = bool(re.search(r"(解[：:]|答案|因此|所以|A\.|B\.|C\.|D\.).{10,}", text))
    if has_example and (has_step or has_worked): return 2, "有例题 + 步骤讲解"
    elif has_example: return 1, "有例题但不够详细"
    return 0, "无例题"


def score_variation(text: str) -> tuple[int, str]:
    variation_kw = ["变式", "换成", "如果.*会", "改了", "换一个", "另一道", "检验"]
    has_variation = any(re.search(kw, text) for kw in variation_kw)
    has_test = bool(re.search(r"(自测|验证|检测|试试|尝试|选词填空)", text))
    if has_variation and has_test: return 2, "有变式题 + 验证请求"
    elif has_variation or has_test: return 1, "有变式/验证但不够完整"
    return 0, "无变式迁移"


def score_misconception(text: str) -> tuple[int, str]:
    has_header = bool(re.search(r"常见误区|常见错误|易错|误区|典型错误|陷阱", text))
    table_rows = len(re.findall(r"^\|.*\|.*\|", text, re.MULTILINE))
    if has_header and table_rows >= 3: return 2, f"有误区表格 ({table_rows} 行)"
    elif has_header: return 1, "有误区提示但格式不完整"
    return 0, "无常见误区（P0 缺失）"


def score_conciseness(text: str) -> tuple[int, str]:
    lines = text.strip().split("\n")
    lc = len(lines)
    if lc < 5:  return 0, "输出过短"
    if lc > 120: return 1, f"输出偏长 ({lc} 行)"
    paragraphs = [l for l in lines if l.strip() and not l.startswith("#") and not l.startswith("|")]
    if len(paragraphs) < 3: return 1, "内容偏少"
    return 2, f"简洁适中 ({lc} 行)"


def score_audience(text: str) -> tuple[int, str]:
    advanced_terms = [
        "测度论", "泛函分析", "范畴论", "层论", "上同调",
        "紧算子", "索伯列夫空间", "巴拿赫代数",
    ]
    if any(term in text for term in advanced_terms): return 0, "使用过高阶知识"
    if re.search(r"(用.*(解释|理解|说明)).*(实分析|泛函|拓扑|测度)", text): return 0, "用高阶解释基础"
    return 2, "语言层次适当"


def score_method_summary(text: str) -> tuple[int, str]:
    summary_kw = ["总结", "方法", "关键", "核心", "一句话", "本质", "概括"]
    has_summary = any(kw in text for kw in summary_kw)
    last_200 = text.strip()[-200:]
    has_closing = bool(re.search(r"(总结|关键|核心|本质|概括|一句话)", last_200))
    if has_summary and has_closing: return 2, "有方法总结 + 结尾概括"
    elif has_summary: return 1, "有总结但不够突出"
    return 0, "无方法总结"


def score_no_encouragement(text: str) -> tuple[int, str]:
    found = [p for p in FORBIDDEN_PATTERNS if re.search(p, text)]
    skip_found = [p for p in SKIP_REASONING_PATTERNS if re.search(p, text)]
    issues = found + [f"'{s}'跳过推理" for s in skip_found]
    if issues: return 0, f"违规: {', '.join(issues)}"
    return 2, "无空泛鼓励/跳过推理"


# ── 单词专项维度 ──────────────────────────────────────────

def score_exam_relevance(text: str) -> tuple[int, str]:
    """考试针对性（替代诊断维度）"""
    exam_kw = ["六级", "考研", "雅思", "托福", "GRE", "高考", "考试", "真题", "考法", "备考"]
    has_exam_info = any(kw in text for kw in exam_kw)
    has_action = bool(re.search(r"行动|建议|策略|最低要求|高目标", text))
    if has_exam_info and has_action: return 2, "有考试分析 + 行动建议"
    elif has_exam_info: return 1, "有考试信息但缺乏建议"
    return 0, "缺少考试针对性"


def score_etymology(text: str) -> tuple[int, str]:
    """词根词缀分析（替代直觉维度）"""
    has_etym = bool(re.search(r"词根|词缀|构词|前缀|后缀|同根词|义项引申", text))
    has_lookalike = bool(re.search(r"形近词|近义词|反义词|辨析|梯度", text))
    if has_etym and has_lookalike: return 2, "词根分析 + 形近/近义辨析"
    elif has_etym or has_lookalike: return 1, "有词汇深度但不够完整"
    return 0, "缺少词根/辨析"


# ── Rubric 定义 ───────────────────────────────────────────

CONCEPT_SCORERS = [
    ("诊断卡点", score_diagnosis),
    ("直觉解释", score_intuition),
    ("正式定义", score_formal_definition),
    ("例题展示", score_example),
    ("变式迁移", score_variation),
    ("常见误区", score_misconception),
    ("简洁清晰", score_conciseness),
    ("目标受众", score_audience),
    ("方法总结", score_method_summary),
    ("避免空泛", score_no_encouragement),
]
CONCEPT_MAX = 20
CONCEPT_THRESHOLD = 14

WORD_SCORERS = [
    # 前两个换成单词专项
    ("考试针对性", score_exam_relevance),
    ("词根辨析", score_etymology),
    # 后面与 concept 共用
    ("正式定义", score_formal_definition),
    ("例题展示", score_example),
    ("变式迁移", score_variation),
    ("常见误区", score_misconception),
    ("简洁清晰", score_conciseness),
    ("目标受众", score_audience),
    ("方法总结", score_method_summary),
    ("避免空泛", score_no_encouragement),
]
WORD_MAX = 20
WORD_THRESHOLD = 14


def get_rubric(meta: dict) -> tuple[list, int, int]:
    """根据 rubric 类型返回 (scorers, max_score, threshold)"""
    if meta["rubric"] == "word":
        return WORD_SCORERS, WORD_MAX, WORD_THRESHOLD
    return CONCEPT_SCORERS, CONCEPT_MAX, CONCEPT_THRESHOLD


# ── 评测 ──────────────────────────────────────────────────

def evaluate(text: str, label: str = "") -> dict:
    scorable = extract_scorable(text)
    meta = parse_file_meta(text)
    scorers, max_score, threshold = get_rubric(meta)

    scores = {}
    total = 0
    for name, scorer in scorers:
        s, note = scorer(scorable)
        scores[name] = (s, note)
        total += s

    passed = total >= threshold
    return {
        "label": label,
        "scores": scores,
        "total": total,
        "max": max_score,
        "passed": passed,
        "rubric": meta["rubric"],
        "is_baseline": meta["is_baseline"],
    }


def print_result(result: dict, verbose: bool = True):
    label = result["label"]
    total = result["total"]
    passed = result["passed"]

    if result["is_baseline"]:
        status = f"{DIM}BASELINE{NC}"
    elif passed:
        status = f"{GREEN}PASS{NC}"
    else:
        status = f"{RED}FAIL{NC}"

    bar_w = result["max"] // 2
    filled = int(bar_w * total / result["max"]) if result["max"] > 0 else 0
    bar = f"{GREEN}{'█' * filled}{DIM}{'░' * (bar_w - filled)}{NC}"

    rubric_tag = f" {DIM}[{result['rubric']}]{NC}"
    print(f"\n{BOLD}{label}{rubric_tag}{NC}")
    print(f"  {bar} {status}  {total}/{result['max']}")

    if verbose:
        for name, (s, note) in result["scores"].items():
            color = GREEN if s == 2 else YELLOW if s == 1 else RED
            print(f"  {name:8s} {color}{s}/2{NC}  {DIM}{note}{NC}")


def find_demo_files(skill: str = None) -> list[Path]:
    if not DEMO_DIR.exists():
        return []
    files = []
    for f in DEMO_DIR.glob("*.md"):
        if f.name != "README.md":
            files.append(f)
    for f in (DEMO_DIR / "before-after").glob("*.md"):
        if f.name != "README.md":
            files.append(f)
    if skill:
        files = [f for f in files if skill.lower() in f.name.lower()]
    return sorted(files)


def is_baseline_file(path: Path) -> bool:
    try:
        text = path.read_text()
        return BASELINE_MARKER in text.split("\n")[:10]
    except Exception:
        return False


def is_skill_demo(path: Path) -> bool:
    """非 baseline 的 skill demo（适用于 --quick）"""
    return not is_baseline_file(path)


# ── 主入口 ──────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Scientific Learning Skills — eval")
    parser.add_argument("--skill", help="只评测指定 skill 的 demo")
    parser.add_argument("--quick", action="store_true", help="只测核心 skill demo（不含 baseline）")
    parser.add_argument("--all", action="store_true", help="测试所有 demo（含 baseline）")
    parser.add_argument("--input-file", help="评测任意文件")
    parser.add_argument("--input-text", help="评测任意文本")
    parser.add_argument("--quiet", "-q", action="store_true", help="只显示总分")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    results = []

    if args.input_text:
        text = args.input_text
        meta = parse_file_meta(text)
        result = evaluate(text, label="<stdin>")
        results.append(result)

    elif args.input_file:
        path = Path(args.input_file)
        if not path.exists():
            print(f"{RED}文件不存在: {path}{NC}", file=sys.stderr)
            sys.exit(1)
        text = path.read_text()
        result = evaluate(text, label=path.name)
        results.append(result)

    else:
        files = find_demo_files(args.skill)

        if args.quick:
            files = [f for f in files if is_skill_demo(f)]
        elif not args.all:
            # 默认：包含 baseline 但 baseline 不参与 pass/fail 判分
            pass

        if not files:
            print(f"{YELLOW}未找到 demo 文件。使用 --input-file 或 --input-text 评测。{NC}")
            sys.exit(1)

        for f in files:
            text = f.read_text()
            result = evaluate(text, label=f"demo/{f.relative_to(DEMO_DIR)}")
            results.append(result)

    # 输出
    if args.json:
        output = []
        for r in results:
            out = {
                "label": r["label"],
                "total": r["total"],
                "max": r["max"],
                "passed": r["passed"],
                "rubric": r["rubric"],
                "is_baseline": r["is_baseline"],
                "scores": {k: v[0] for k, v in r["scores"].items()},
            }
            output.append(out)
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        for r in results:
            print_result(r, verbose=not args.quiet)

        # 汇总（baseline 不计入 pass/fail）
        judged = [r for r in results if not r["is_baseline"]]
        if judged:
            avg = sum(r["total"] for r in judged) / len(judged)
            passed = sum(1 for r in judged if r["passed"])
            baseline_count = len([r for r in results if r["is_baseline"]])
            extra = f"（{baseline_count} 个 baseline 仅展示）" if baseline_count else ""
            print(f"\n{BOLD}{'='*50}{NC}")
            print(f"{BOLD}汇总: {passed}/{len(judged)} 通过, 平均 {avg:.1f}/{judged[0]['max']}{extra}{NC}")

    # 退出码：只看非 baseline 的结果
    judged = [r for r in results if not r["is_baseline"]]
    if judged:
        all_pass = all(r["passed"] for r in judged)
        sys.exit(0 if all_pass else 1)
    sys.exit(0)


if __name__ == "__main__":
    main()
