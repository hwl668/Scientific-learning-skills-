"""Rule-based teaching quality scorers."""

from __future__ import annotations

import re


STOP_MARKER = "<!-- eval:stop -->"
RUBRIC_MARKER = re.compile(r"<!--\s*rubric:\s*([a-z][a-z0-9_-]*)\s*-->", re.IGNORECASE)
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
        kind = match.group(1).lower()
        if kind == "baseline":
            is_baseline = True
            rubric = "concept"
        else:
            rubric = canonicalize_rubric(kind)
    return {"rubric": rubric, "is_baseline": is_baseline}


def extract_scorable(text: str, *, allow_stop_marker: bool = False) -> str:
    if allow_stop_marker and STOP_MARKER in text:
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
    data_rows = _count_misconception_data_rows(text)
    if has_header and data_rows >= 2:
        return 2, f"有误区表格 ({data_rows} 条真实误区)"
    if has_header:
        if data_rows == 1:
            return 1, "误区表只有 1 条真实误区，至少需要 2 条"
        return 1, "有误区提示但缺少规范表格或真实数据行"
    return 0, "无常见误区（P0 缺失）"


def _markdown_cells(line: str) -> list[str] | None:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    return [cell.strip() for cell in stripped[1:-1].split("|")]


def _is_markdown_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _is_misconception_header(cells: list[str]) -> bool:
    if len(cells) < 3:
        return False
    patterns = (
        r"(?:常见)?(?:错误|误区)|典型错误|易错点|common\s+(?:error|mistake)|misconception",
        r"为什么错|错误原因|原因|why\s+(?:it\s+is\s+)?wrong",
        r"正确理解|正确做法|纠正|correct\s+understanding|correction",
    )
    return all(
        re.fullmatch(pattern, cell.strip(), re.IGNORECASE)
        for pattern, cell in zip(patterns, cells[:3])
    )


def _is_substantive_misconception_row(cells: list[str]) -> bool:
    if len(cells) < 3 or not all(cell.strip() for cell in cells[:3]):
        return False
    placeholder = re.compile(
        r"(?:\.{2,}|…+|[-—]+|todo|tbd|n/?a|待补充|"
        r"\[[^\]]*\]|<[^>]*>|错误(?:示例)?\s*[一二三四五六七八九十\d]+|"
        r"原因\s*[一二三四五六七八九十\d]*|正解|正确理解\s*[一二三四五六七八九十\d]+)",
        re.IGNORECASE,
    )
    return all(not placeholder.fullmatch(cell.strip()) for cell in cells[:3])


def _count_misconception_data_rows(text: str) -> int:
    """Count real rows in a standard misconception table.

    A header and Markdown separator are structural rows, not misconceptions.  The
    table must advertise an error column and contain at least three populated
    columns so unrelated tables elsewhere in the response cannot earn this score.
    """

    lines = text.splitlines()
    best = 0
    index = 0
    while index < len(lines):
        first = _markdown_cells(lines[index])
        if first is None:
            index += 1
            continue

        table: list[list[str]] = []
        while index < len(lines):
            cells = _markdown_cells(lines[index])
            if cells is None:
                break
            table.append(cells)
            index += 1

        if not table:
            continue
        header = table[0]
        if not _is_misconception_header(header):
            continue
        unique_rows = {
            tuple(re.sub(r"\s+", " ", cell.strip()).casefold() for cell in cells[:3])
            for cells in table[1:]
            if not _is_markdown_separator(cells)
            and _is_substantive_misconception_row(cells)
        }
        best = max(best, len(unique_rows))
    return best


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


def _score_signals(
    text: str,
    dimension: str,
    patterns: tuple[str, ...],
    *,
    full_at: int = 2,
) -> tuple[int, str]:
    """Score the presence of independent structural signals for one dimension."""

    matches = sum(bool(re.search(pattern, text, re.IGNORECASE | re.MULTILINE)) for pattern in patterns)
    if matches >= full_at:
        return 2, f"{dimension}结构完整 ({matches}/{len(patterns)} 个信号)"
    if matches:
        return 1, f"有{dimension}，但结构不完整 ({matches}/{len(patterns)} 个信号)"
    return 0, f"缺少{dimension}"


def score_problem_purpose(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "问题背景",
        (r"要解决什么问题|问题背景", r"为什么(?:需要|要学)|作用", r"应用场景|现实场景|用途"),
    )


def score_cardpoint(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "卡点结论",
        (r"诊断结果|卡点(?:类型|位置)", r"卡在|主因是|属于(?:前置|概念|符号|迁移)", r"不是.+而是"),
    )


def score_targeted_repair(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "针对性修复",
        (r"针对性修复|##\s*修复", r"针对(?:这个|上述|你的).{0,20}(卡点|问题)", r"对比|拆开|只修"),
    )


def score_verification(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "理解验证",
        (r"##\s*验证|验证理解", r"用自己的话|判断下列|回答(?:这个|以下)", r"[？?]"),
    )


def score_foundation_confirmation(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "基础确认",
        (r"基础确认|先确认", r"已经(?:理解|掌握)|能否解释|会不会", r"若.*(?:不清楚|答不出).*(?:先补|转回)"),
    )


def score_multi_perspective(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "多视角解释",
        (r"多视角|另一个视角", r"几何视角|图像视角", r"代数视角|符号视角", r"计算视角|物理视角"),
    )


def score_cross_link(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "跨知识联系",
        (r"跨知识联系|和.+的联系", r"对应|统一", r"前置知识|后续知识"),
    )


def score_derivation(text: str) -> tuple[int, str]:
    return _score_signals(text, "推导/证明", (r"推导|证明", r"因为|由此", r"所以|因此|得到"))


def score_counterexample(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "反例辨析",
        (r"反例", r"不满足|失效|不成立", r"边界|条件不可省"),
    )


def score_application(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "实际应用",
        (r"实际应用|现实应用", r"用于|可用来", r"工程|物理|计算机|数据|经济"),
    )


def score_problem_type(text: str) -> tuple[int, str]:
    return _score_signals(text, "题型识别", (r"题型识别|这是一道", r"属于.+题", r"识别信号|看到.+想到"))


def score_key_conditions(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "关键条件",
        (r"关键条件", r"题目(?:给出|中的)", r"条件意味着|隐含条件", r"目标是|所求"),
    )


def score_model_building(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "解题模型",
        (r"解题模型|建立模型", r"设\s*[^，。\n]+(?:为|=)", r"转化为|等价于", r"方程|函数|不等式|向量"),
    )


def score_stepwise_solution(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "分步求解",
        (r"分步求解|步骤", r"第\s*1\s*步|1[\.、]", r"第\s*2\s*步|2[\.、]", r"因此|所以"),
        full_at=3,
    )


def score_reasoning_explanation(text: str) -> tuple[int, str]:
    return _score_signals(text, "步骤依据", (r"为什么", r"因为|依据", r"所以|因此", r"这一步"))


def score_error_reproduction(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "错误重现",
        (r"重现错误|你的(?:原|错误)解", r"你(?:写成|认为|做到)", r"错误发生在|从.+跳到"),
    )


def score_error_classification(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "错因归类",
        (r"错因类型|主要错因", r"次要错因", r"概念错误|条件漏看|推理跳步|计算错误|策略错误|表达错误"),
    )


def score_correct_reasoning(text: str) -> tuple[int, str]:
    return _score_signals(text, "正确思路", (r"正确思路", r"应当|应该", r"因为|依据", r"步骤|先.+再"), full_at=3)


def score_trap_identification(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "同类陷阱识别",
        (r"同类陷阱|识别同类", r"识别信号|看到.+(?:先|要)", r"容易漏|警惕"),
    )


def score_checklist(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "检查清单",
        (r"检查清单", r"\[[ xX]\]", r"逐项检查|检查(?:定义域|条件|符号|单位|边界)"),
    )


def score_plan_constraints(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "约束校准",
        (r"目标", r"时间|截止", r"基础|当前水平", r"每天|每周.*(?:小时|分钟)"),
        full_at=3,
    )


def score_goal_decomposition(text: str) -> tuple[int, str]:
    return _score_signals(text, "目标拆解", (r"目标拆解|里程碑", r"总目标", r"阶段目标|可交付|完成标准"))


def score_phase_plan(text: str) -> tuple[int, str]:
    return _score_signals(text, "阶段划分", (r"阶段划分", r"阶段\s*1|第一阶段", r"阶段\s*2|第二阶段", r"第\s*\d+\s*周"), full_at=3)


def score_daily_tasks(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "每日任务",
        (r"每日任务|每天", r"\d+\s*(?:分钟|小时)", r"练习|阅读|复习", r"自测|检测|真题"),
        full_at=3,
    )


def score_resource_match(text: str) -> tuple[int, str]:
    return _score_signals(text, "资源匹配", (r"资源匹配|学习资源", r"教材|课程|题库|真题", r"使用方式|用于"))


def score_success_criteria(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "检测标准",
        (r"检测标准|完成标准", r"正确率|得分|限时|能独立", r"达到|不少于|至少"),
    )


def score_review_mechanism(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "复盘调整",
        (r"复盘机制|每周复盘", r"完成率|偏差", r"调整|下周计划", r"缓冲|弹性"),
        full_at=3,
    )


def score_word_meanings(text: str) -> tuple[int, str]:
    return _score_signals(text, "核心义项", (r"含义|义项", r"1[\.、].+2[\.、]", r">\s*\*?.+\*?", r"例句"))


def score_collocations(text: str) -> tuple[int, str]:
    return _score_signals(text, "用法搭配", (r"用法搭配|常用搭配", r"搭配", r"语境|例句"))


def score_word_formation(text: str) -> tuple[int, str]:
    return _score_signals(
        text,
        "词根词缀",
        (r"词根|词缀|构词|前缀|后缀", r"词族|同根词|派生词", r"义项引申|原义|词源"),
    )


def score_confusables(text: str) -> tuple[int, str]:
    return _score_signals(text, "易混词辨析", (r"形近词|易混词", r"区分要点|辨析", r"陷阱"))


def score_synonym_gradient(text: str) -> tuple[int, str]:
    return _score_signals(text, "近义词梯度", (r"近义词梯度|近义词", r"→|强度|正式度|语气", r"区别|辨析"))


def score_memory_anchor(text: str) -> tuple[int, str]:
    return _score_signals(text, "记忆锚点", (r"记忆锚点|记忆口诀", r"联想|故事", r"自测|回忆"))


def score_content_classification(text: str) -> tuple[int, str]:
    return _score_signals(text, "内容分类", (r"内容分类", r"并列型|过程型|因果型|对比型|论证型", r"判断依据|结构"))


def score_structured_breakdown(text: str) -> tuple[int, str]:
    return _score_signals(text, "结构化拆分", (r"结构化拆分", r"模块\s*1|模块一", r"模块\s*2|模块二", r"主题标签|核心句"), full_at=3)


def score_mind_map(text: str) -> tuple[int, str]:
    return _score_signals(text, "思维导图", (r"思维导图", r"├|└|→", r"层级|主干|分支"))


def score_keyword_compression(text: str) -> tuple[int, str]:
    return _score_signals(text, "关键词压缩", (r"关键词压缩|关键词", r"触发词|记忆链", r"→|口诀"))


def score_recall_questions(text: str) -> tuple[int, str]:
    return _score_signals(text, "主动提取题", (r"检测题|题库|抽背", r"填空", r"问答", r"[？?]"), full_at=3)


def score_question_variety(text: str) -> tuple[int, str]:
    return _score_signals(text, "检测题型覆盖", (r"填空检测|填空题", r"问答检测|简答题", r"关键词触发|线索", r"随机抽背"), full_at=2)


def score_review_tracking(text: str) -> tuple[int, str]:
    return _score_signals(text, "复习追踪", (r"复习|抽背", r"薄弱点|掌握", r"下次|间隔", r"正确|错误.*记录"), full_at=3)


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
    ("核心义项", score_word_meanings),
    ("用法搭配", score_collocations),
    ("词根词缀", score_word_formation),
    ("易混词辨析", score_confusables),
    ("近义词梯度", score_synonym_gradient),
    ("考试针对性", score_exam_relevance),
    ("常见误区", score_misconception),
    ("记忆锚点", score_memory_anchor),
    ("简洁清晰", score_conciseness),
    ("避免空泛", score_no_encouragement),
]
WORD_MAX = 20
WORD_THRESHOLD = 14


ZERO_BASE_SCORERS = [
    ("输入诊断", score_diagnosis),
    ("问题背景", score_problem_purpose),
    ("直觉解释", score_intuition),
    ("正式定义", score_formal_definition),
    ("最小例题", score_example),
    ("自测迁移", score_variation),
    ("常见误区", score_misconception),
    ("简洁清晰", score_conciseness),
    ("目标受众", score_audience),
    ("避免空泛", score_no_encouragement),
]

FUZZY_SCORERS = [
    ("快速诊断", score_diagnosis),
    ("卡点结论", score_cardpoint),
    ("针对性修复", score_targeted_repair),
    ("理解验证", score_verification),
    ("变式测试", score_variation),
    ("常见误区", score_misconception),
    ("简洁清晰", score_conciseness),
    ("目标受众", score_audience),
    ("方法总结", score_method_summary),
    ("避免空泛", score_no_encouragement),
]

DEEPENING_SCORERS = [
    ("基础确认", score_foundation_confirmation),
    ("多视角解释", score_multi_perspective),
    ("跨知识联系", score_cross_link),
    ("推导证明", score_derivation),
    ("反例辨析", score_counterexample),
    ("实际应用", score_application),
    ("变式迁移", score_variation),
    ("常见误区", score_misconception),
    ("简洁清晰", score_conciseness),
    ("避免空泛", score_no_encouragement),
]

PROBLEM_SCORERS = [
    ("题型识别", score_problem_type),
    ("关键条件", score_key_conditions),
    ("解题模型", score_model_building),
    ("分步求解", score_stepwise_solution),
    ("步骤依据", score_reasoning_explanation),
    ("方法总结", score_method_summary),
    ("变式训练", score_variation),
    ("常见误区", score_misconception),
    ("简洁清晰", score_conciseness),
    ("避免空泛", score_no_encouragement),
]

MISTAKE_SCORERS = [
    ("错误重现", score_error_reproduction),
    ("错因归类", score_error_classification),
    ("关键误区", score_misconception),
    ("正确思路", score_correct_reasoning),
    ("同类陷阱", score_trap_identification),
    ("检查清单", score_checklist),
    ("变式训练", score_variation),
    ("简洁清晰", score_conciseness),
    ("目标受众", score_audience),
    ("避免空泛", score_no_encouragement),
]

PLAN_SCORERS = [
    ("约束校准", score_plan_constraints),
    ("目标拆解", score_goal_decomposition),
    ("阶段划分", score_phase_plan),
    ("每日任务", score_daily_tasks),
    ("资源匹配", score_resource_match),
    ("检测标准", score_success_criteria),
    ("复盘调整", score_review_mechanism),
    ("常见误区", score_misconception),
    ("简洁清晰", score_conciseness),
    ("避免空泛", score_no_encouragement),
]

TEXT_MEMORIZER_SCORERS = [
    ("内容分类", score_content_classification),
    ("结构化拆分", score_structured_breakdown),
    ("思维导图", score_mind_map),
    ("关键词压缩", score_keyword_compression),
    ("主动提取题", score_recall_questions),
    ("检测题型", score_question_variety),
    ("复习追踪", score_review_tracking),
    ("常见误区", score_misconception),
    ("简洁清晰", score_conciseness),
    ("避免空泛", score_no_encouragement),
]


RUBRIC_SCORERS = {
    "concept": CONCEPT_SCORERS,
    "zero-base-learning": ZERO_BASE_SCORERS,
    "fuzzy-understanding": FUZZY_SCORERS,
    "deepening-learning": DEEPENING_SCORERS,
    "problem-solving": PROBLEM_SCORERS,
    "mistake-review": MISTAKE_SCORERS,
    "study-plan-builder": PLAN_SCORERS,
    "word": WORD_SCORERS,
    "text-memorizer": TEXT_MEMORIZER_SCORERS,
}

RUBRIC_ALIASES = {
    "zero-base": "zero-base-learning",
    "fuzzy": "fuzzy-understanding",
    "deepening": "deepening-learning",
    "problem": "problem-solving",
    "mistake": "mistake-review",
    "plan": "study-plan-builder",
    "word-deep-dive": "word",
    "memorization": "text-memorizer",
}


def canonicalize_rubric(rubric: str) -> str:
    if not isinstance(rubric, str) or not rubric.strip():
        raise ValueError("rubric must be a non-empty string")
    normalized = rubric.strip().lower().replace("_", "-")
    normalized = RUBRIC_ALIASES.get(normalized, normalized)
    if normalized not in RUBRIC_SCORERS:
        allowed = ", ".join(sorted(RUBRIC_SCORERS))
        raise ValueError(f"unknown rubric {rubric!r}; expected one of: {allowed}")
    return normalized


def get_rubric(meta: dict) -> tuple[list, int, int]:
    rubric = canonicalize_rubric(meta.get("rubric", "concept"))
    scorers = RUBRIC_SCORERS[rubric]
    return scorers, len(scorers) * 2, 14
