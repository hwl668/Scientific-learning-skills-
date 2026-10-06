# -*- coding: utf-8 -*-
"""Generate docs/mae-calibration.md: MaE's 55 misconception classes mapped onto
our 6 cognitive-gap types (grounded in the real MaE data.json, MIT licensed).

The mapping judgment is the maintainer's; the table is generated so all 55
classes are covered exactly once and drift is impossible.
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA = PROJECT_ROOT / "mae_data.tmp.json"
OUT = PROJECT_ROOT / "docs" / "mae-calibration.md"

# Hand-authored: MaE ID -> primary gap type in learning_agent.diagnosis.
MAPPING = {
    "MaE01": "missing_prerequisite", "MaE02": "concept_confusion", "MaE03": "formula_without_understanding",
    "MaE04": "concept_confusion", "MaE05": "missing_prerequisite", "MaE06": "formula_without_understanding",
    "MaE07": "formula_without_understanding", "MaE08": "formula_without_understanding", "MaE09": "formula_without_understanding",
    "MaE10": "formula_without_understanding", "MaE11": "formula_without_understanding", "MaE12": "formula_without_understanding",
    "MaE13": "formula_without_understanding", "MaE14": "formula_without_understanding", "MaE15": "formula_without_understanding",
    "MaE16": "missing_prerequisite", "MaE17": "formula_without_understanding", "MaE18": "formula_without_understanding",
    "MaE19": "concept_confusion", "MaE20": "formula_without_understanding", "MaE21": "missing_prerequisite",
    "MaE22": "formula_without_understanding", "MaE23": "concept_confusion", "MaE24": "missing_prerequisite",
    "MaE25": "formula_without_understanding", "MaE26": "missing_prerequisite", "MaE27": "missing_prerequisite",
    "MaE28": "missing_prerequisite", "MaE29": "formula_without_understanding", "MaE30": "formula_without_understanding",
    "MaE31": "concept_confusion", "MaE32": "formula_without_understanding", "MaE33": "concept_confusion",
    "MaE34": "formula_without_understanding", "MaE35": "missing_prerequisite", "MaE36": "missing_prerequisite",
    "MaE37": "symbol_not_understood", "MaE38": "missing_prerequisite", "MaE39": "concept_confusion",
    "MaE40": "symbol_not_understood", "MaE41": "missing_prerequisite", "MaE42": "concept_confusion",
    "MaE43": "symbol_not_understood", "MaE44": "missing_prerequisite", "MaE45": "formula_without_understanding",
    "MaE46": "concept_confusion", "MaE47": "concept_confusion", "MaE48": "missing_prerequisite",
    "MaE49": "missing_prerequisite", "MaE50": "missing_prerequisite", "MaE51": "concept_confusion",
    "MaE52": "derivation_gap", "MaE53": "symbol_not_understood", "MaE54": "formula_without_understanding",
    "MaE55": "formula_without_understanding",
}

TYPE_NAMES = {
    "concept_confusion": "概念混淆",
    "symbol_not_understood": "符号不懂",
    "derivation_gap": "推导断裂",
    "missing_prerequisite": "前置缺失",
    "rote_no_transfer": "不会迁移",
    "formula_without_understanding": "公式会套不懂原理",
}

NOTES = {
    "MaE19": "「−」的操作符号义与数的正负号义混淆——概念混淆的典型样本",
    "MaE51": "等号被理解为「答案是」而非关系——概念混淆",
    "MaE52": "「解完不检验」是解题链条缺了验证步骤——归入推导断裂",
    "MaE22": "余数接成小数是程序缺口——归入公式会套不懂原理",
    "MaE03": "用逐个计算代替识别一般规律——程序性处理压过结构性理解",
}


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    seen: dict[str, dict] = {}
    for row in data:
        seen.setdefault(row["Misconception ID"], row)
    assert set(MAPPING) == set(seen), f"mapping/data mismatch: {set(MAPPING) ^ set(seen)}"

    by_type: dict[str, list[str]] = {}
    for mid, gap in MAPPING.items():
        by_type.setdefault(gap, []).append(mid)

    lines = [
        "# MaE 55 类误概念 → 六类卡点 校准",
        "",
        "> 数据源：[MaE](https://github.com/nancyotero-projects/math-misconceptions)（MIT License, © 2024 Nancy Otero），",
        "> 220 例 / 55 类代数与数感误概念，每类含 Question / Incorrect Answer / Correct Answer / Explanation。",
        "> 本文件由 `scripts/generate_mae_calibration.py` 生成，保证 55 类恰好映射一次。",
        "",
        "## 为什么要做这个校准",
        "",
        "诊断引擎的六类卡点是闭集（`learning_agent/diagnosis.py`）。调研结论要求用 MaE 的固定",
        "taxonomy 校验这个闭集是否完备、粒度是否合适：每一类真实误概念都必须能落进六类之一，",
        "落不进去的就是我们缺失的卡点类型；落进去之后还要检查「修复策略」是否真的对症。",
        "",
        "## 覆盖统计",
        "",
    ]
    for gap in TYPE_NAMES:
        ids = by_type.get(gap, [])
        pct = f"{len(ids) / 55 * 100:.0f}%"
        lines.append(f"- **{TYPE_NAMES[gap]}**：{len(ids)} 类（{pct}）")
    lines += [
        "",
        "## 三个结构性发现",
        "",
        "1. **MaE 高度偏「程序性误概念」**：formula_without_understanding 23/55（42%），",
        "   missing_prerequisite 16/55（29%）——小学-代数阶段的错误大多是「程序没懂就执行」和",
        "   「前置表示缺失」。这对我们的启示：fuzzy-understanding 的修复策略里，「重建立程序背后的",
        "   不变量」必须是一等公民，而不是只讲直觉。",
        "2. **rote_no_transfer 在 MaE 中为 0**：不是这类错误不存在，而是 MaE 是单题错答数据，",
        "   「不会迁移」需要看到同一学习者在两个任务上的表现差异才能确诊。单一 distractor 原则上",
        "   观察不到它——这划定了确定性诊断引擎的能力边界：**单轮证据只能诊断五类，迁移类必须",
        "   靠验证/变式环节的隐式诊断**（这正是 fuzzy-understanding SKILL.md 第 4/5 步的职责）。",
        "3. **六类闭集能装下全部 55 类，但粒度提醒**：MaE46/47/51 这类「对符号语义本身的误解」",
        "   （变量是标签、等号是答案）都落进概念混淆，说明概念混淆内部还藏着一个「语义误解 vs ",
        "   关系混淆」的子维度，v0.6 若扩分类树应从这里切。",
        "",
        "## 完整映射表",
        "",
        "| MaE ID | Topic | 误概念（原文摘要） | 六类卡点 | 备注 |",
        "|---|---|---|---|---|",
    ]
    for mid in sorted(seen):
        row = seen[mid]
        gap = MAPPING[mid]
        misc = " ".join(row["Misconception"].split())
        if misc.startswith("when "):
            misc = misc[5:]
        misc = misc[:100] + ("…" if len(misc) > 100 else "")
        note = NOTES.get(mid, "")
        lines.append(f"| {mid} | {row['Topic']} | {misc} | {TYPE_NAMES[gap]} | {note} |")

    lines += [
        "",
        "## 用法",
        "",
        "- **诊断案例种子**：每类 MaE 条目自带 Question + Incorrect Answer，天然是 QATD-2k 式",
        "  distractor 案例；扩 `data/diagnosis_cases.jsonl` 时按此改写（见",
        "  `scripts/expand_diagnosis_cases.py` 的准入规则：必须先被确定性引擎正确分类）。",
        "- **评测种子**：MaE 可作 diagnosis 引擎的 held-out 评测集（映射标签见上表），",
        "  报告时注明「六类映射为人工判定」。",
        "- **不做的事**：不用 MaE 训练任何模型（其价值在固定标签，不在规模）；",
        "  不声称我们的六类「等价于」MaE 分类——映射是压缩，不是等同。",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(by_type)} types, 55 classes mapped)")


if __name__ == "__main__":
    main()
