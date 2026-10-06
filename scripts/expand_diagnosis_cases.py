# -*- coding: utf-8 -*-
"""Expand data/diagnosis_cases.jsonl with distractor-style cases (QATD-2k approach).

QATD-2k's key property: the learner presents their own (wrong) answer choice and
reasoning, and the misconception/gap is recoverable from WHICH wrong concept they
used — not from a hand-written label attached to a clean question. These 30 new
cases follow that pattern: each text contains the learner's failed attempt
("我选了…/我把…当成了…"), and the six-gap label is inferable from the error's shape.

Deterministic-first is preserved: every case is classified by
learning_agent.diagnosis BEFORE it is appended; the script refuses to add any
case the rule engine gets wrong (CI gate --min-accuracy 0.85 covers the file).
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from learning_agent.diagnosis import diagnose  # noqa: E402

PATH = PROJECT_ROOT / "data" / "diagnosis_cases.jsonl"

CASES = [
    # concept_confusion — the wrong option is the definition of the OTHER concept
    ("concept_confusion", "这道题我选了 B，把协方差的取值当成了相关系数的取值范围，答案是 -1 到 1 我写了任意实数。这两个概念的区别到底在哪？"),
    ("concept_confusion", "我把 TCP 拥塞控制当成了流量控制去选选项被判错。拥塞控制和流量控制什么时候用哪个？"),
    ("concept_confusion", "题目问的是字符串常量，我按字符数组的方式答了被扣分。字符串和字符数组我到现在都分不清。"),
    ("concept_confusion", "这题 f 在 x=0 处有极限，我选了「连续」，答案是「不连续」。极限和连续的区别我背过还是选错。"),
    ("concept_confusion", "单例模式那道题我用混了静态类和单例，选了错误的选项。它们到底什么时候用哪个？"),
    # symbol_not_understood — the distractor comes from misreading a symbol
    ("symbol_not_understood", "|A| 我一直当成绝对值来算，这道线代题从第一步就全错了。竖线包着矩阵是什么意思？"),
    ("symbol_not_understood", "题目里的 ∀x 我直接忽略掉了，「任意」相关的选项全没考虑所以选错。这个符号到底在约束什么？"),
    ("symbol_not_understood", "我把 f'(x) 读成 f 乘 x，整道求导题全错。这个撇记号是什么意思？"),
    ("symbol_not_understood", "∑ 的上标 n 和下标 i=1 我只代入了最后一项所以全错。这个求和符号的下标上标到底怎么读？"),
    ("symbol_not_understood", "看到 ∃! 我以为是印刷错误，这题的逻辑选项直接跳过选错。这个符号是什么意思？"),
    # derivation_gap — the answer is visible but a middle step is missing
    ("derivation_gap", "答案里从 x²+y²=r² 直接跳到 2x+2yy'=0，我抄下来了但没看懂这一步怎么得到的。"),
    ("derivation_gap", "标准答案用了洛必达之后还变了一次形，我代进去数值对不上，中间哪一步断了？"),
    ("derivation_gap", "这题我能看懂最后一行结论，但第 2 行到第 3 行的等号怎么来的完全看不出来。"),
    ("derivation_gap", "证明第二行突然出现了一个构造的辅助函数，答案说「显然可得」，我不知道它是从哪来的。"),
    ("derivation_gap", "参考答案把 x_{n+1} 写成 x_n 的极限 L，下一步两边同时取极限，我不明白这个等号两边怎么变成相等的。"),
    # missing_prerequisite — the distractor exists because a base concept is absent
    ("missing_prerequisite", "这道题做错是因为我根本不知道「特征值」是什么，前面的矩阵课都没听。我应该先补什么？"),
    ("missing_prerequisite", "老师批注说我错在没有学过行列式的性质就直接用克拉默法则。这种前置缺口我要怎么判断？"),
    ("missing_prerequisite", "选项里所有涉及「秩」的判断我全选错，后来发现是秩的概念缺失导致整道题的解析我都听不懂。"),
    ("missing_prerequisite", "这道递归题卡住是因为我连函数调用栈是什么都不知道，这部分基础没学。要先学什么？"),
    ("missing_prerequisite", "题目默认会画状态转移图，我没学过自动机，从读题开始就懵了。这是不是前置问题？需要补什么？"),
    # rote_no_transfer — example solved, variant failed
    ("rote_no_transfer", "例题里的追及问题我会做，考试把火车换成传送带我选择的公式就错了。为什么一换场景就不会？"),
    ("rote_no_transfer", "老师讲的那道例题我抄会了，作业把条件换个方向我就选错。怎么才算会而不是背模板？"),
    ("rote_no_transfer", "课上用数组讲的双指针我懂了，题目换成链表就不会迁移，选项全错。"),
    ("rote_no_transfer", "这道题和我背过的题型只差「至少」变成了「至多」，我就把判断方向选反了。遇到变式就不行。"),
    ("rote_no_transfer", "参考例题我一步没差地复现出来了，考试只改了提问方向我就卡住。这种照着会、自己做不会怎么破？"),
    # formula_without_understanding — formula applied outside its conditions
    ("formula_without_understanding", "这题我套公式把两个概率直接相加了，正确答案要先算交集项。P(A∪B)=P(A)+P(B) 这个公式为什么不能随便用？"),
    ("formula_without_understanding", "我把等比数列求和公式用在公比等于 1 的题上选错了。这个公式背后为什么不许 q=1？"),
    ("formula_without_understanding", "洛必达我每道题都在用，这题是 x→∞ 的 0/0 型我代错了。我只会算，不会判断它什么时候不能用。"),
    ("formula_without_understanding", "我用求导公式直接令导数为零，答案说要再检验边界点。公式不管边界吗？我背了公式但不知道原理。"),
    ("formula_without_understanding", "标准差公式我代数字很熟练，这道题的数据是加权样本我直接代错。公式背后的原理对数据有什么要求？"),
]


def main() -> None:
    existing = PATH.read_text(encoding="utf-8")
    existing_texts = {json.loads(line)["text"] for line in existing.splitlines() if line.strip()}

    appended, rejected = [], []
    for label, text in CASES:
        if text in existing_texts:
            continue
        result = diagnose(text)
        if result.label != label:
            rejected.append((label, result.label, text))
            continue
        appended.append(json.dumps({"text": text, "label": label, "category": "distractor"}, ensure_ascii=False))

    if rejected:
        print("REJECTED (rule engine misclassifies — fix rules or case wording):")
        for label, predicted, text in rejected:
            print(f"  expected={label} predicted={predicted} | {text}")
        raise SystemExit(1)

    if appended:
        with PATH.open("a", encoding="utf-8") as f:
            f.write("\n".join(appended) + "\n")
    print(f"appended {len(appended)} distractor-style cases")


if __name__ == "__main__":
    main()
