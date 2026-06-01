"""Rule-based teaching quality scorers."""

from __future__ import annotations

import re


STOP_MARKER = "<!-- eval:stop -->"
RUBRIC_MARKER = re.compile(r"<!--\s*rubric:\s*(\w+)\s*-->")
BASELINE_MARKER = "<!-- rubric: baseline -->"

FORBIDDEN_PATTERNS = [
    r"加油", r"你能行", r"坚持就是胜利", r"多练练",
    r"你一定可以", r"相信自己", r"不要放弃",
    r"come on", r"you can do it",
]

SKIP_REASONING_PATTERNS = [
    r"显然", r"易知", r"众所周知", r"不难看出",
    r"obviously", r"clearly", r"it is easy to see",
]


def parse_file_meta(text: str) -> dict:
    rubric = "concept"
    is_baseline = False
    for line in text.split("\n")[:10]:
        match = RUBRIC_MARKER.search(line)
        if not match:
            continue
        kind = match.group(1)
        if kind == "baseline":
            is_baseline = True
            rubric = "concept"
        elif kind in ("concept", "word"):
            rubric = kind
    return {"rubric": rubric, "is_baseline": is_baseline}


def extract_scorable(text: str) -> str:
    if STOP_MARKER in text:
        return text.split(STOP_MARKER)[0]
    return text


def score_diagnosis(text: str) -> tuple[int, str]:
    diagnostic_keywords = ["诊断", "卡点", "先确认", "了解情况", "先判断", "先问", "定位"]
    diagnostic_questions = len(re.findall(r"[？?]", text))
    has_keywords = any(kw in text for kw in diagnostic_keywords)
    has_questions = diagnostic_questions >= 2
    if has_keywords and has_questions:
        return 2, "有诊断关键词 + 追问问题"
    if has_keywords or has_questions:
        return 1, "有诊断意识但不充分"
    return 0, "无诊断环节"


def score_intuition(text: str) -> tuple[int, str]:
    intuition_patterns = [
        r"类比", r"像", r"想象", r"比如", r"假设你",
        r"直觉", r"画面", r"打个比方", r"生活",
        r"analogy", r"imagine", r"intuition",
    ]
    matches = sum(1 for pattern in intuition_patterns if re.search(pattern, text))
    if matches >= 3:
        return 2, f"丰富的直觉/类比 ({matches} 处)"
    if matches >= 1:
        return 1, f"有直觉元素 ({matches} 处)"
    return 0, "无直觉解释"


def score_formal_definition(text: str) -> tuple[int, str]:
    has_formal = bool(re.search(r"(定义|记作|记为|即|指的是|满足).{0,20}(如果|当|对任意|存在|使得|则)", text))
    has_math = bool(re.search(r"\$.*\$|lim|∑|∫|ε|δ|→|∀|∃", text))
    if has_formal and has_math:
        return 2, "有正式定义 + 符号解释"
    if has_formal or has_math:
        return 1, "有定义但不够完整"
    if len(text) > 300:
        return 1, "有解释但无正式定义"
    return 0, "无正式定义"


def score_example(text: str) -> tuple[int, str]:
    has_example = bool(re.search(r"(例如|例题|例[：:]|举个|比如|具体|自测)", text))
    has_step = bool(re.search(r"(步骤|第\d步|首先.*然后|1\..*2\..*3\.)", text))
    has_worked = bool(re.search(r"(解[：:]|答案|因此|所以|A\.|B\.|C\.|D\.).{10,}", text))
    if has_example and (has_step or has_worked):
        return 2, "有例题 + 步骤讲解"
    if has_example:
        return 1, "有例题但不够详细"
    return 0, "无例题"


def score_variation(text: str) -> tuple[int, str]:
    variation_kw = ["变式", "换成", "如果.*会", "改了", "换一个", "另一道", "检验"]
    has_variation = any(re.search(kw, text) for kw in variation_kw)
    has_test = bool(re.search(r"(自测|验证|检测|试试|尝试|选词填空)", text))
    if has_variation and has_test:
        return 2, "有变式题 + 验证请求"
    if has_variation or has_test:
        return 1, "有变式/验证但不够完整"
    return 0, "无变式迁移"


def score_misconception(text: str) -> tuple[int, str]:
    has_header = bool(re.search(r"常见误区|常见错误|易错|误区|典型错误|陷阱", text))
    table_rows = len(re.findall(r"^\|.*\|.*\|", text, re.MULTILINE))
    if has_header and table_rows >= 3:
        return 2, f"有误区表格 ({table_rows} 行)"
    if has_header:
        return 1, "有误区提示但格式不完整"
    return 0, "无常见误区（P0 缺失）"


def score_conciseness(text: str) -> tuple[int, str]:
    lines = text.strip().split("\n")
    line_count = len(lines)
    if line_count < 5:
        return 0, "输出过短"
    if line_count > 120:
        return 1, f"输出偏长 ({line_count} 行)"
    paragraphs = [line for line in lines if line.strip() and not line.startswith("#") and not line.startswith("|")]
    if len(paragraphs) < 3:
        return 1, "内容偏少"
    return 2, f"简洁适中 ({line_count} 行)"


def score_audience(text: str) -> tuple[int, str]:
    advanced_terms = [
        "测度论", "泛函分析", "范畴论", "层论", "上同调",
        "紧算子", "索伯列夫空间", "巴拿赫代数",
    ]
    if any(term in text for term in advanced_terms):
        return 0, "使用过高阶知识"
    if re.search(r"(用.*(解释|理解|说明)).*(实分析|泛函|拓扑|测度)", text):
        return 0, "用高阶解释基础"
    return 2, "语言层次适当"


def score_method_summary(text: str) -> tuple[int, str]:
    summary_kw = ["总结", "方法", "关键", "核心", "一句话", "本质", "概括"]
    has_summary = any(kw in text for kw in summary_kw)
    last_200 = text.strip()[-200:]
    has_closing = bool(re.search(r"(总结|关键|核心|本质|概括|一句话)", last_200))
    if has_summary and has_closing:
        return 2, "有方法总结 + 结尾概括"
    if has_summary:
        return 1, "有总结但不够突出"
    return 0, "无方法总结"


def score_no_encouragement(text: str) -> tuple[int, str]:
    found = [pattern for pattern in FORBIDDEN_PATTERNS if re.search(pattern, text)]
    skip_found = [pattern for pattern in SKIP_REASONING_PATTERNS if re.search(pattern, text)]
    issues = found + [f"'{pattern}'跳过推理" for pattern in skip_found]
    if issues:
        return 0, f"违规: {', '.join(issues)}"
    return 2, "无空泛鼓励/跳过推理"


def score_exam_relevance(text: str) -> tuple[int, str]:
    exam_kw = ["六级", "考研", "雅思", "托福", "GRE", "高考", "考试", "真题", "考法", "备考"]
    has_exam_info = any(kw in text for kw in exam_kw)
    has_action = bool(re.search(r"行动|建议|策略|最低要求|高目标", text))
    if has_exam_info and has_action:
        return 2, "有考试分析 + 行动建议"
    if has_exam_info:
        return 1, "有考试信息但缺乏建议"
    return 0, "缺少考试针对性"


def score_etymology(text: str) -> tuple[int, str]:
    has_etym = bool(re.search(r"词根|词缀|构词|前缀|后缀|同根词|义项引申", text))
    has_lookalike = bool(re.search(r"形近词|近义词|反义词|辨析|梯度", text))
    if has_etym and has_lookalike:
        return 2, "词根分析 + 形近/近义辨析"
    if has_etym or has_lookalike:
        return 1, "有词汇深度但不够完整"
    return 0, "缺少词根/辨析"


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
    ("考试针对性", score_exam_relevance),
    ("词根辨析", score_etymology),
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
    if meta["rubric"] == "word":
        return WORD_SCORERS, WORD_MAX, WORD_THRESHOLD
    return CONCEPT_SCORERS, CONCEPT_MAX, CONCEPT_THRESHOLD
