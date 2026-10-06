# MaE 55 类误概念 → 六类卡点 校准

> 数据源：[MaE](https://github.com/nancyotero-projects/math-misconceptions)（MIT License, © 2024 Nancy Otero），
> 220 例 / 55 类代数与数感误概念，每类含 Question / Incorrect Answer / Correct Answer / Explanation。
> 本文件由 `scripts/generate_mae_calibration.py` 生成，保证 55 类恰好映射一次。

## 为什么要做这个校准

诊断引擎的六类卡点是闭集（`learning_agent/diagnosis.py`）。调研结论要求用 MaE 的固定
taxonomy 校验这个闭集是否完备、粒度是否合适：每一类真实误概念都必须能落进六类之一，
落不进去的就是我们缺失的卡点类型；落进去之后还要检查「修复策略」是否真的对症。

## 覆盖统计

- **概念混淆**：11 类（20%）
- **符号不懂**：4 类（7%）
- **推导断裂**：1 类（2%）
- **前置缺失**：16 类（29%）
- **不会迁移**：0 类（0%）
- **公式会套不懂原理**：23 类（42%）

## 三个结构性发现

1. **MaE 高度偏「程序性误概念」**：formula_without_understanding 23/55（42%），
   missing_prerequisite 16/55（29%）——小学-代数阶段的错误大多是「程序没懂就执行」和
   「前置表示缺失」。这对我们的启示：fuzzy-understanding 的修复策略里，「重建立程序背后的
   不变量」必须是一等公民，而不是只讲直觉。
2. **rote_no_transfer 在 MaE 中为 0**：不是这类错误不存在，而是 MaE 是单题错答数据，
   「不会迁移」需要看到同一学习者在两个任务上的表现差异才能确诊。单一 distractor 原则上
   观察不到它——这划定了确定性诊断引擎的能力边界：**单轮证据只能诊断五类，迁移类必须
   靠验证/变式环节的隐式诊断**（这正是 fuzzy-understanding SKILL.md 第 4/5 步的职责）。
3. **六类闭集能装下全部 55 类，但粒度提醒**：MaE46/47/51 这类「对符号语义本身的误解」
   （变量是标签、等号是答案）都落进概念混淆，说明概念混淆内部还藏着一个「语义误解 vs 
   关系混淆」的子维度，v0.6 若扩分类树应从这里切。

## 完整映射表

| MaE ID | Topic | 误概念（原文摘要） | 六类卡点 | 备注 |
|---|---|---|---|---|
| MaE01 | Number sense | students don't understand how to represent proportional relationships. | 前置缺失 |  |
| MaE02 | Number sense | Students misunderstand proportional relationships, not realizing parts must be equal in size. | 概念混淆 |  |
| MaE03 | Number sense | students misunderstand numerical exponent patterns, resorting to computation instead of recognizing … | 公式会套不懂原理 | 用逐个计算代替识别一般规律——程序性处理压过结构性理解 |
| MaE04 | Number sense | students misunderstand algebraic terms and equations involving exponents, such as numerical bases ra… | 概念混淆 |  |
| MaE05 | Number sense | Students think longer numerals mean larger numbers, misunderstanding place value | 前置缺失 |  |
| MaE06 | Number Operations | students inaccurately simplify fractions by guessing instead of dividing | 公式会套不懂原理 |  |
| MaE07 | Number Operations | students simplify just one of the terms in a fraction, either the numerator or the denominator | 公式会套不懂原理 |  |
| MaE08 | Number Operations | students incorrectly add or subtract fractions by summing both numerators and denominators separatel… | 公式会套不懂原理 |  |
| MaE09 | Number Operations | students find common denominators but wrongly keep the original numerators unchanged | 公式会套不懂原理 |  |
| MaE10 | Number Operations | students subtract mixed numbers incorrectly, avoiding regrouping and just subtracting the smaller fr… | 公式会套不懂原理 |  |
| MaE11 | Number Operations | students wrongly subtract mixed numbers by separately subtracting wholes, numerators, and denominato… | 公式会套不懂原理 |  |
| MaE12 | Number Operations | When students multiply the numerator of the first fraction by the denominator of the second fraction… | 公式会套不懂原理 |  |
| MaE13 | Number Operations | students incorrectly scale both numerator and denominator by the same whole number, effectively mult… | 公式会套不懂原理 |  |
| MaE14 | Number Operations | students wrongly divide fractions by splitting numerators and denominators into separate divisions, … | 公式会套不懂原理 |  |
| MaE15 | Number Operations | students incorrectly invert the dividend instead of the divisor when dividing fractions, misundersta… | 公式会套不懂原理 |  |
| MaE16 | Number Operations | students mistakenly position the decimal point left of the sum, assuming units and tenths combine se… | 前置缺失 |  |
| MaE17 | Number Operations | students incorrectly drop extra decimal digits directly into their answer when subtracting uneven de… | 公式会套不懂原理 |  |
| MaE18 | Number Operations | students are unsure of the correct sign when adding positive and negative numbers | 公式会套不懂原理 |  |
| MaE19 | Number Operations | students confuse signs of operations and signs of numbers, inappropriately applying the rule "two ne… | 概念混淆 | 「−」的操作符号义与数的正负号义混淆——概念混淆的典型样本 |
| MaE20 | Number Operations | students wrongly position the decimal in multiplication by counting from the left, not the right | 公式会套不懂原理 |  |
| MaE21 | Number Operations | students fail to regroup in subtraction, mistakenly subtracting the larger number from the smaller | 前置缺失 |  |
| MaE22 | Number Operations | students extend quotients with remainders as decimals, if division isn't exact within the dividend's… | 公式会套不懂原理 | 余数接成小数是程序缺口——归入公式会套不懂原理 |
| MaE23 | Ratios and proportional reasoning | students confuse fixed scaling (absolute) with ratio comparisons (relative) in proportional relation… | 概念混淆 |  |
| MaE24 | Ratios and proportional reasoning | students struggle to understand that ratios can compare same or different units | 前置缺失 |  |
| MaE25 | Ratios and proportional reasoning | students struggle to apply correct operations on ratios expressed as fractions | 公式会套不懂原理 |  |
| MaE26 | Ratios and proportional reasoning | students misunderstand how to identify and use equivalent forms of ratios, including fractions and d… | 前置缺失 |  |
| MaE27 | Ratios and proportional reasoning | students lack unitization skills, unable to treat ratios as composite units to solve problems system… | 前置缺失 |  |
| MaE28 | Ratios and proportional reasoning | students fail to see ratios as relationships between two quantities | 前置缺失 |  |
| MaE29 | Ratios and proportional reasoning | students incorrectly apply a single proportion formula to all percentage problems: (smaller value)/(… | 公式会套不懂原理 |  |
| MaE30 | Ratios and proportional reasoning | students struggle to discern the three types of percent problems, relying solely on "percent times a… | 公式会套不懂原理 |  |
| MaE31 | Properties of number and operations | students incorrectly assume the commutative and associative properties apply to subtraction and divi… | 概念混淆 |  |
| MaE32 | Properties of number and operations | students mistakenly add two negative numbers, yielding a positive sum, particularly in equations wit… | 公式会套不懂原理 |  |
| MaE33 | Properties of number and operations | students interchange minuend and subtrahend, reversing subtraction order, causing calculation errors… | 概念混淆 |  |
| MaE34 | Properties of number and operations | students incorrectly perform operations from left to right, neglecting the proper order of operation… | 公式会套不懂原理 |  |
| MaE35 | Patterns, relationships, and functions | students struggle to represent key aspects and relationships in patterns, as seen in attempts like g… | 前置缺失 |  |
| MaE36 | Patterns, relationships, and functions | students struggle to accurately represent problems using graphical notation, misunderstanding the pu… | 前置缺失 |  |
| MaE37 | Patterns, relationships, and functions | students struggle to interpret graph scales accurately | 符号不懂 |  |
| MaE38 | Patterns, relationships, and functions | students struggle to grasp the concept that a linear function represents a consistent rate of change | 前置缺失 |  |
| MaE39 | Patterns, relationships, and functions | students confuse linear and exponential functions' properties and representations. | 概念混淆 |  |
| MaE40 | Patterns, relationships, and functions | students misinterpret slope signs in equations versus their upward or downward trends in graphs. | 符号不懂 |  |
| MaE41 | Patterns, relationships, and functions | students struggle to connect different representations of the same function (graph, equation, table)… | 前置缺失 |  |
| MaE42 | Patterns, relationships, and functions | students confuse linear relationships with direct proportions, believing that because a linear funct… | 概念混淆 |  |
| MaE43 | Algebraic representations | students struggle with plotting points, reversing the x- and y-coordinates | 符号不懂 |  |
| MaE44 | Algebraic representations | students struggle to grasp the concept of independent and dependent variables | 前置缺失 |  |
| MaE45 | Variables, expressions, and operations | students mistakenly switch variables when transposing expressions involving subtraction | 公式会套不懂原理 |  |
| MaE46 | Variables, expressions, and operations | students mistakenly perceive variables as labels or units, or associate their value with their alpha… | 概念混淆 |  |
| MaE47 | Variables, expressions, and operations | students incorrectly assume two variables in an equation must represent distinct numerical values, r… | 概念混淆 |  |
| MaE48 | Variables, expressions, and operations | students struggle to grasp that variables can represent changing or varying quantities | 前置缺失 |  |
| MaE49 | Equations and inequalities | students find it challenging to comprehend the various meanings and applications of variables | 前置缺失 |  |
| MaE50 | Equations and inequalities | students struggle with forming and understanding algebraic expressions and equations. | 前置缺失 |  |
| MaE51 | Equations and inequalities | students misunderstand the equal sign as indicating "the answer is" rather than representing a relat… | 概念混淆 | 等号被理解为「答案是」而非关系——概念混淆 |
| MaE52 | Equations and inequalities | students neglect to check their solutions or make errors during the checking process | 推导断裂 | 「解完不检验」是解题链条缺了验证步骤——归入推导断裂 |
| MaE53 | Equations and inequalities | students get confusion over operation symbols and their meanings in algebra | 符号不懂 |  |
| MaE54 | Equations and inequalities | students make reversal order errors, swapping variables in equations, such as writing 2X=Y instead o… | 公式会套不懂原理 |  |
| MaE55 | Equations and inequalities | students struggle to recognize when to combine like terms, failing to add or subtract terms with the… | 公式会套不懂原理 |  |

## 用法

- **诊断案例种子**：每类 MaE 条目自带 Question + Incorrect Answer，天然是 QATD-2k 式
  distractor 案例；扩 `data/diagnosis_cases.jsonl` 时按此改写（见
  `scripts/expand_diagnosis_cases.py` 的准入规则：必须先被确定性引擎正确分类）。
- **评测种子**：MaE 可作 diagnosis 引擎的 held-out 评测集（映射标签见上表），
  报告时注明「六类映射为人工判定」。
- **不做的事**：不用 MaE 训练任何模型（其价值在固定标签，不在规模）；
  不声称我们的六类「等价于」MaE 分类——映射是压缩，不是等同。
