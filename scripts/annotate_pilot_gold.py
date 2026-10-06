# -*- coding: utf-8 -*-
"""Annotate the 20-case pilot subset of dev.synthetic.jsonl (v2: harder post-tests + levels).

v2 changes (driven by pilot20-v1's Level-3 ceiling — all three conditions scored
100% on post-tests too easy for a strong simulated learner):
- post_test items are now multi-step application/prediction tasks (compute,
  predict, prove monotonicity) instead of "explain the idea" prompts;
- every pilot case carries student_level (low/mid/high) so reports can stratify
  and beginner-harm stays visible (McMiner: same prompt +15.9pp advanced,
  −12.2pp beginners).

Gold annotations (diagnosis / must_address / must_not_do) are hand-authored by
the maintainer following docs/learning-skill-bench.md. wd/tm/sp carry gold only.
"""

import json
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "evals" / "bench" / "dev.synthetic.jsonl"

GOLD = {
    "zb-001": {
        "student_level": "low",
        "gold": {
            "skill": "zero-base-learning",
            "learner_state": "prior_missing",
            "diagnosis": "第一次接触极限，只有高中函数背景；需要先用具体例子建立「无限逼近」的直觉，再给出直观定义，不能直接上形式化语言。",
            "must_address": [
                "用具体例子（如 1/n 越来越接近 0）建立「无限逼近」直觉",
                "直观定义：极限描述的是变化趋势，不要求某一点真的到达该值",
                "点出「趋近但不一定相等」这个最容易卡住的地方",
            ],
            "must_not_do": [
                "直接抛出 ε-δ 定义而不做任何直觉铺垫",
                "假设学习者已掌握数列收敛等前置概念",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "数列 aₙ = n/(n+1)：算出 a₁、a₂、a₁₀、a₁₀₀ 的数值；它趋近于哪个数？a₁₀₀ 与极限值相差多少？由此说明「极限值不必等于任何一项」。",
                "reference_answer": "a₁=1/2, a₂=2/3, a₁₀≈0.909, a₁₀₀≈0.990；极限是 1；差约 0.01；每一项都严格小于 1 且不等于 1，但无限逼近——极限值不要求被某一项取到。",
            },
            "near_transfer": {
                "question": "f(x)=x² 在 x→2 时极限是 4。若改成分段函数：x<2 时 f(x)=x²，但定义 f(2)=100。x→2 的极限还是 4 吗？为什么 f(2) 的取值不影响极限？",
                "reference_answer": "仍是 4。极限只关心 x 趋近 2 时（x≠2）函数值的趋势，与该点本身的定义无关——所以 f(2)=100 不影响极限存在且为 4。",
            },
            "far_transfer": {
                "question": "有人说：「油量表读数越来越接近 0，所以油量的极限是 0，发动机此刻一定没油了。」指出这句话混淆了极限语言的哪两个概念。",
                "reference_answer": "混淆了「趋近的极限值」与「某时刻的实际取值」。极限描述变化趋势，不保证在某一时刻真正达到该值——读数趋于 0 不等于此刻油量为 0。",
            },
        },
    },
    "zb-008": {
        "student_level": "low",
        "gold": {
            "skill": "zero-base-learning",
            "learner_state": "prior_missing",
            "diagnosis": "刚开始学编程，完全没接触过递归；需要用最小的可运行例子说明「函数调用自己」+ 终止条件 + 返回值如何逐层回传。",
            "must_address": [
                "用一个最小例子（如阶乘或倒计时）说明函数调用自己是什么样子",
                "强调基线条件（终止条件）为什么必须有，否则无限调用",
                "说明每层调用结束后返回值如何逐层「回来」合并",
            ],
            "must_not_do": [
                "用汉诺塔、八皇后等复杂问题作为入门例子",
                "只展示递归代码而不解释调用栈的展开与回传",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "给出 2ⁿ 的递归定义（基线条件 + 递归步骤），并写出 f(4) 展开经历的每一层调用与最终返回值。",
                "reference_answer": "基线 f(0)=1（或 f(1)=2）；递归 f(n)=2·f(n-1)。f(4)=2·f(3)→2·(2·f(2))→2·(2·(2·f(1)))→2·(2·(2·2))，逐层返回得 16，共 5 层调用。",
            },
            "near_transfer": {
                "question": "写一个统计文件夹内所有文件数的伪代码 countFiles(folder)（文件夹可嵌套）：基线是什么？递归步骤是什么？如果忘了基线会发生什么？",
                "reference_answer": "基线：folder 无子文件夹时返回其中文件数；递归：对本文件夹每个子文件夹调用 countFiles 并求和。没有基线 → 递归不终止，调用栈无限增长直至栈溢出。",
            },
            "far_transfer": {
                "question": "「先有鸡还是先有蛋」也是一种自我引用。递归为什么不是这种死循环？两者最关键的差异是什么（用「基线/规模」的语言）？",
                "reference_answer": "递归每层把问题规模缩小（n→n-1），且存在一定能到达的基线出口；鸡生蛋问题没有缩小规模的机制、没有基线，自我引用不终止。",
            },
        },
    },
    "zb-014": {
        "student_level": "low",
        "gold": {
            "skill": "zero-base-learning",
            "learner_state": "prior_missing",
            "diagnosis": "第一次接触机器学习，没有优化/函数极值的背景；应先用「下山找最低点」的直觉建立梯度下降的图景，再落到「沿负梯度方向小步更新」。",
            "must_address": [
                "用下山/蒙眼下坡类比建立「一步步往低处走」的直觉",
                "说明「梯度指向上坡最陡方向」因此要沿负梯度更新",
                "点出学习率的作用：步子太大来回震荡，太小走太慢",
            ],
            "must_not_do": [
                "上来就写 ∂L/∂w 的链式法则推导",
                "假设学习者知道损失函数、凸优化等术语而不解释",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "在 f(w)=(w-3)² 上从 w=0 出发，学习率 η=0.2。算出前两步更新后的 w 值（写出每步的导数值），并说出最终收敛到哪里。",
                "reference_answer": "f'(w)=2(w-3)。第一步：w₁=0−0.2×(−6)=1.2；第二步：w₂=1.2−0.2×2×(1.2−3)=1.2+0.72=1.92；继续迭代收敛到最低点 w=3。",
            },
            "near_transfer": {
                "question": "同样的函数改用 η=2.5 会发生什么？用「步长 vs 曲线坡度」解释，并给出一个判断学习率过大的实用信号。",
                "reference_answer": "步子太大反复越过最低点，w 在 3 两侧来回震荡甚至发散（例如 w₂=1.2−2.5×2×(1.2−3)=10.2，直接跳到另一侧更远处）。信号：loss 不降反升或剧烈震荡。",
            },
            "far_transfer": {
                "question": "为什么不干脆把学习率设得极小（如 1e-9）来保证绝不震荡？这会付出什么代价？实际系统怎么折中？",
                "reference_answer": "极小步长下每步几乎不动，收敛需要的更新次数爆炸（可能永不完成）；实际用学习率调度/自适应步长（先大后小），在稳定性和速度间折中。",
            },
        },
    },
    "fz-001": {
        "student_level": "mid",
        "gold": {
            "skill": "fuzzy-understanding",
            "learner_state": "representation_gap",
            "diagnosis": "会按规则算矩阵乘法（程序性知识在），缺的是「矩阵=线性变换、乘法=变换的复合」这层语义；卡点是表征缺失，不是计算。",
            "must_address": [
                "把一个 2×2 矩阵解释为「对平面向量做的变换」（旋转/拉伸/剪切）",
                "说明 AB 的含义：先做 B 的变换再做 A 的变换，所以乘法规则是为「复合」服务的",
                "用「对基向量做了什么」来重新解读乘法的每一列",
            ],
            "must_not_do": [
                "再教一遍行乘列的计算程序",
                "泛泛说「线性代数很重要」而不落到本例",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "A=[[0,-1],[1,0]]（逆时针转 90°）。用「A 对基向量做了什么」解释 A 的两列各是什么，并用基向量合成算出 A·(2,1)。",
                "reference_answer": "A·(1,0)=(0,1)（第一列），A·(0,1)=(-1,0)（第二列）；A·(2,1)=2·A·(1,0)+1·A·(0,1)=2(0,1)+(-1,0)=(-1,2)。列 = 基向量的像，任意向量 = 列的线性组合。",
            },
            "near_transfer": {
                "question": "B=[[2,0],[0,3]]。分别计算 B·A·(1,1) 和 A·B·(1,1)，说明每步几何动作，并解释为什么结果不同。",
                "reference_answer": "BA(1,1)：先拉伸 (1,1)→(2,3)，再旋转→(-3,2)。AB(1,1)：先旋转 (1,1)→(-1,1)，再拉伸→(-2,3)。先旋转会改变拉伸轴的方向，两种顺序复合结果不同，故 BA≠AB。",
            },
            "far_transfer": {
                "question": "把「矩阵乘法=变换复合」迁移到一元函数：f(x)=x², g(x)=x+3。算 f(g(1)) 和 g(f(1))，并说明这对应矩阵乘法的哪个一般性质。",
                "reference_answer": "f(g(1))=f(4)=16；g(f(1))=g(1)=4。函数复合有顺序且一般不可交换——与矩阵乘法同构（AB 是先 B 后 A 的复合），故一般 AB≠BA。",
            },
        },
    },
    "fz-006": {
        "student_level": "mid",
        "gold": {
            "skill": "fuzzy-understanding",
            "learner_state": "concept_confusion",
            "diagnosis": "把「概率密度函数 PDF」和「累积分布函数 CDF」混为一谈；关键区分是：PDF 本身不是概率，其下方面积才是概率。",
            "must_address": [
                "明确区分：CDF F(x)=P(X≤x) 是累积的概率；PDF f(x) 是 CDF 的导数/变化率",
                "强调 f(x) 的值可以大于 1，单点的 f(x) 不是概率",
                "用均匀分布或正态分布的具体图形指出「面积 vs 高度」",
            ],
            "must_not_do": [
                "只复述两个定义而不指出混淆的根源",
                "用测度论语言讲解",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "X 服从参数 1 的指数分布：f(x)=e^{-x}（x≥0）。验证 f 归一化，写出 F(x)，并解释为什么 f(2)≈0.135 不是「X=2 的概率」。",
                "reference_answer": "∫₀^∞ e^{-x}dx=1（归一成立）；F(x)=1-e^{-x}。f(2) 是密度（每单位长度的密集程度），概率=密度对区间积分；单点区间宽度为 0，P(X=2)=0。",
            },
            "near_transfer": {
                "question": "人群身高密度在 170cm 处高于 150cm。为什么「随机抽一人身高恰好 170.000…cm」的概率是 0，而「169.5~170.5cm」的概率是正的？用「宽度×高度」说明。",
                "reference_answer": "单点区间宽度为 0，面积（概率）=密度×宽度=0；169.5~170.5 宽 1cm，面积≈密度×1>0。密度不是概率，积分后的面积才是。",
            },
            "far_transfer": {
                "question": "泊松分布（单位时间内事件数）也有一条钟形曲线。要算「下一秒恰好来 2 个事件」的概率，能用概率密度吗？写出正确的计算式结构。",
                "reference_answer": "不能。泊松是离散分布，没有 PDF；应使用概率质量函数 P(N=2)=e^{-λ}λ²/2!（λ 为单位时间均值）。「曲线」要区分 PMF（离散、可直接读概率）与 PDF（连续、需积分）。",
            },
        },
    },
    "fz-012": {
        "student_level": "low",
        "gold": {
            "skill": "fuzzy-understanding",
            "learner_state": "symbol_gap",
            "diagnosis": "不认识偏导数符号 ∂，且不清楚它与普通微分 d 的区别；卡点是符号语义：∂ 表示「固定其他变量、只对一个变量求变化率」。",
            "must_address": [
                "解释 ∂ 的读法与含义：多元函数中对其中一个变量求导、其余视为常数",
                "用一个二元函数的具体例子演示 ∂f/∂x 的计算过程",
                "指出 d 与 ∂ 的使用场景差异（一元 vs 多元）",
            ],
            "must_not_do": [
                "只说「∂ 就是 d」而不解释多元语境",
                "展开讲全微分/微分形式的严格定义",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "f(x,y)=x²y+sin(y)。求 ∂f/∂x 和 ∂f/∂y，每一步说明把哪个变量当成了常数。",
                "reference_answer": "∂f/∂x=2xy（把 y 当常数，sin(y) 对 x 求导为 0）；∂f/∂y=x²+cos(y)（把 x 当常数，x² 对 y 求导为 0）。",
            },
            "near_transfer": {
                "question": "理想气体 V(T,P)=nRT/P。说出 ∂V/∂T 和 ∂V/∂P 各自「固定了什么」，并算出两个表达式。",
                "reference_answer": "∂V/∂T=nR/P（固定 P）：定压下每升 1 度体积增加 nR/P；∂V/∂P=−nRT/P²（固定 T）：定温下加压体积按 P² 反比缩小。",
            },
            "far_transfer": {
                "question": "一元函数 y=f(x) 的导数也是随 x 变化的。既然如此，∂f/∂x「是一个数还是一条函数」？∂ 和 d 的区别到底在哪一层？",
                "reference_answer": "∂f/∂x 一般仍是 (x,y) 的函数——每个点有自己的偏导数。d 与 ∂ 的区别不在「数还是函数」，而在多元时必须声明「对哪个变量、其余固定」；一元只有一个变量，无需区分。",
            },
        },
    },
    "fz-019": {
        "student_level": "mid",
        "gold": {
            "skill": "fuzzy-understanding",
            "learner_state": "representation_gap",
            "diagnosis": "会套贝叶斯公式但缺少对先验/后验的语义理解；卡点是「证据如何把信念从先验更新为后验」这层表征没有建立。",
            "must_address": [
                "用一句话说清：先验=看到证据前的信念，后验=看到证据后更新的信念",
                "用医疗检测或垃圾邮件的具体数字走一遍更新过程",
                "指出公式每一项在「信念更新」故事中的角色（P(B|A) 是证据的可靠性）",
            ],
            "must_not_do": [
                "把重点放在公式变形技巧上",
                "只给形式化推导不讲更新语义",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "工厂次品率 1%。检测器对次品 95% 报阳、对正品 10% 误报。某人报阳，用贝叶斯算他真是次品的概率，并指出分子、分母各代表什么。",
                "reference_answer": "0.95×0.01/(0.95×0.01+0.10×0.99)=0.0095/0.1085≈8.8%。分子=「是次品且报阳」的概率；分母=「报阳」的全部路径（次品报阳+正品误报）。先验 1% 被证据更新到约 8.8%。",
            },
            "near_transfer": {
                "question": "他又独立做了第二次检测，仍然报阳。用「上一次的后验=这一次的先验」算新的后验，并说明证据是如何迭代更新信念的。",
                "reference_answer": "以 0.088 为新先验：0.95×0.088/(0.95×0.088+0.10×0.912)≈0.0836/0.1748≈47.8%。贝叶斯更新是链式的：每次证据把上一次后验当新先验，两次报阳把 1% 推到约 48%。",
            },
            "far_transfer": {
                "question": "「头奖有人中过，所以买彩票中头奖没那么离谱」——用先验/似然/基数的语言解释这句话错在哪。",
                "reference_answer": "错误在忽略基数与条件化：「有人中奖」是亿万人各买一注下的必然结果（对整体而言概率≈1），但对单个具体的人，先验极小、在「买了票」条件下后验仍然极小；把总体必然性误当个体概率。",
            },
        },
    },
    "ps-001": {
        "student_level": "mid",
        "gold": {
            "skill": "problem-solving",
            "learner_state": "strategy_missing",
            "diagnosis": "对 0/0 型极限没有启动「泰勒展开或洛必达+等价替换」的策略；需要的是题型识别→方法选择→分步执行，而不是直接抄答案。",
            "must_address": [
                "先识别类型：x→0 时分子 eˣ-1-x 与分母 x² 同时趋近 0（0/0 型）",
                "给出方法选择：泰勒展开 eˣ=1+x+x²/2+o(x²) 最能看出主项",
                "分步执行并解释每步依据，最后指出极限为 1/2",
            ],
            "must_not_do": [
                "只写答案不给方法选择依据",
                "顺便展开讲一整章泰勒理论",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "求 lim(x→0) (cos x − 1 + x²/2)/x⁴。写明你选的方法和理由，分步执行到最终值。",
                "reference_answer": "0/0 型且差式含高阶小量，选泰勒：cos x = 1 − x²/2 + x⁴/24 + o(x⁴)，分子 = x⁴/24 + o(x⁴)，除以 x⁴ 得极限 1/24。洛必达要连做四次，泰勒一次看清。",
            },
            "near_transfer": {
                "question": "求 lim(x→0) (tan x − x)/x³，并说明为什么这里洛必达一次后反而更复杂、泰勒更直接。",
                "reference_answer": "tan x = x + x³/3 + o(x³)，分子 = x³/3 + o(x³)，极限 = 1/3。若用洛必达：(sec²x−1)/3x² 仍需再处理 sec²−1=tan²x，绕路；泰勒直接暴露 x³ 主项。",
            },
            "far_transfer": {
                "question": "单摆小角度近似 sin θ ≈ θ 用到了泰勒。说明误差是几阶的，并估计 θ=0.5rad 时近似带来的相对误差量级。",
                "reference_answer": "sin θ = θ − θ³/6 + o(θ⁵)，误差主项 θ³/6，相对误差约 θ²/6。θ=0.5 时 ≈0.042，约 4%——小角度下可忽略，角度大时必须用完整 sin。",
            },
        },
    },
    "ps-006": {
        "student_level": "mid",
        "gold": {
            "skill": "problem-solving",
            "learner_state": "strategy_missing",
            "diagnosis": "推不出最长上升子序列（LIS）的状态转移方程；卡点在「状态定义」这一步没建立：dp[i] 应定义为「以 i 结尾的 LIS 长度」。",
            "must_address": [
                "先引导定义状态：dp[i] = 以第 i 个元素结尾的最长上升子序列长度",
                "引导转移：dp[i] = max(dp[j]+1)（j<i 且 a[j]<a[i]），解释为什么必须「以 i 结尾」",
                "指出边界 dp[i]≥1 与答案取 max，而不是 dp[n-1]",
            ],
            "must_not_do": [
                "直接甩出 O(n log n) 的贪心+二分做法",
                "代替学习者完成全部推理",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "序列 [2, 5, 3, 4, 8, 7]：写出每个位置的 dp 值（以 i 结尾的 LIS 长度），指出 dp[4]（元素 8）的转移来源，并给出 LIS 长度。",
                "reference_answer": "dp = [1, 2, 2, 3, 4, 4]。dp[4]（8）= dp[3]（4）+1 = 4，来源 2<4<8 链。LIS 长度 = max dp = 4（如 2,3,4,8）。注意最后一个 7 的 dp 也是 4（7<8 不能接在 8 后）。",
            },
            "near_transfer": {
                "question": "换成「最长公共子序列 LCS(a,b)」：状态应该定义成什么（含两个下标）？写出 a[i]==b[j] 与不等时的两个转移。",
                "reference_answer": "dp[i][j] = a 前 i 个与 b 前 j 个的 LCS 长度。a[i]==b[j]：dp[i][j]=dp[i-1][j-1]+1；否则 dp[i][j]=max(dp[i-1][j], dp[i][j-1])。同样是「固定结尾」消除后效性。",
            },
            "far_transfer": {
                "question": "有同学把状态定义为「前 i 个数里选出的 LIS 长度」而推不出转移。用「转移时缺了什么信息」解释这个状态为什么失败，「以 i 结尾」补上了什么。",
                "reference_answer": "「前 i 个随便选」没有记录选中的最后一个元素，转移时无法判断新元素能否接上去（比较对象未知）——信息不足导致后效。「以 i 结尾」固定了最后一块信息，使每个子问题自洽可转移。",
            },
        },
    },
    "ps-011": {
        "student_level": "mid",
        "gold": {
            "skill": "problem-solving",
            "learner_state": "strategy_missing",
            "diagnosis": "二分查找边界（找第一个等于 target 的位置）反复写错；卡点是没有统一的区间不变量（左闭右闭 or 左闭右开）约定，导致 left/right/mid 调整规则混乱。",
            "must_address": [
                "引导先声明区间约定（如左闭右闭 [l,r]），说明循环条件与更新规则必须和约定一致",
                "按约定推一遍找「第一个 2」：a[mid]≥target 时 r=mid-1 否则 l=mid+1，记录答案",
                "用数组 [1,2,2,2,3] 实际走一遍边界验证",
            ],
            "must_not_do": [
                "罗列三种边界写法却不解释不变量",
                "直接给代码不解释为什么不会死循环/漏解",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "数组 [1,2,2,2,3]：按左闭右闭约定分别写出「找第一个 2」和「找最后一个 2」中 a[mid]==2 时的更新方向（一个 l=mid+1，一个 r=mid-1，谁是谁？）与最终返回下标。",
                "reference_answer": "找第一个 2：命中后继续向左收缩，r=mid−1 并记录 ans=mid，最终下标 1；找最后一个 2：命中后继续向右，l=mid+1 记录 ans，最终下标 3。方向由「要第一个还是最后一个」决定。",
            },
            "near_transfer": {
                "question": "有序数组 [1,3,5,7] 中找「第一个 ≥6 的位置」（数组里没有 6）。用同一套不变量写过程，返回什么？这对应 C++ 的哪个标准函数？",
                "reference_answer": "条件泛化为 a[mid]≥6 即收缩右半并记录：最终返回下标 3（元素 7），即 6 应插入的位置。这正是 lower_bound 语义——「找第一个 2」是它取 target=2 的特例。",
            },
            "far_transfer": {
                "question": "「把长度 L 的木头切成段、要求段数 ≥ k」——证明 L 的可行性关于 L 单调，因此可以对 L 二分；再把目标改成「段数恰好等于 k」，说明单调性为什么失效。",
                "reference_answer": "L 越大每段越长、段数越少：若 L 可行（段数≥k）则更小的 L 也可行，可行集是前缀 → 单调，可二分最大可行 L。「恰好 =k」时可行集两侧都不可行、不是前缀/后缀，二分前提被破坏。",
            },
        },
    },
    "ps-020": {
        "student_level": "mid",
        "gold": {
            "skill": "problem-solving",
            "learner_state": "strategy_missing",
            "diagnosis": "「三人轮流投篮先中者胜」类几何分布/无穷级数题没有建模思路；卡点是不会用「第一轮胜/没胜进入循环」的递归分解（或无穷等比级数求和）。",
            "must_address": [
                "设每人单次命中率为 p1,p2,p3，先写出第一轮某人胜的概率（如 p1）",
                "引导递归/循环视角：一轮无人命中则局面回到起点、胜率整体乘以 (1-p1)(1-p2)(1-p3)",
                "用无穷等比级数求和得到第一人胜率 p1 / (1-(1-p1)(1-p2)(1-p3))",
            ],
            "must_not_do": [
                "跳过建模直接给最终公式",
                "引入马尔可夫链等更重的方法而不给最小路径",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "甲乙轮流投篮，甲命中率 1/2、乙 1/3，甲先投。列出甲获胜概率的方程（或级数）并解出具体值。",
                "reference_answer": "P = 1/2（甲首轮中）+ (1/2)(2/3)·P（双双未中后局面重现）⇒ P(1−1/3)=1/2 ⇒ P=3/4。或级数 Σ (1/3)^k·(1/2)。",
            },
            "near_transfer": {
                "question": "若甲先投但命中率只有 1/4、乙 1/2，谁占优？算出两人的获胜概率。",
                "reference_answer": "P甲 = (1/4)/(1−(3/4)(1/2)) = (1/4)/(5/8) = 2/5；P乙 = 3/5。先手优势被低命中率抵消，乙反而占优——占优与否由「首轮成功率/全失败率」之比决定。",
            },
            "far_transfer": {
                "question": "把规则改成「每人最多投 3 轮，总分高者胜」。为什么无穷级数方法在这里失效？应该换成什么建模工具？",
                "reference_answer": "有限轮没有「全失败后局面等比重现」的无穷结构，级数的公比结构消失；应改为按轮次的有限状态递推/枚举（DP 或决策树），逐轮累加得分分布。",
            },
        },
    },
    "mr-001": {
        "student_level": "low",
        "gold": {
            "skill": "mistake-review",
            "learner_state": "concept_error",
            "diagnosis": "把 x² > 4 当成 x² = 4 开方处理，丢掉「负根」分支：本质是对「不等式两边开方要分类讨论」这一规则未掌握，属于概念错误而非粗心。",
            "must_address": [
                "先重现错误：从 x²>4 直接写 x>2，指出丢掉了 x<-2 的分支",
                "归类错因：对 |x|>2 ⇔ x<-2 或 x>2（或图像法）的规则性误解",
                "给出正确思路并用图像/数轴验证，附同类陷阱（如 x²<4 的解是 -2<x<2）",
            ],
            "must_not_do": [
                "归因为「粗心」而不指出规则性漏洞",
                "只给正确答案不复盘错误发生的位置",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "解 x² ≥ 9，写出完整解集，并演示一个自检动作证明你没有再丢分支。",
                "reference_answer": "x≤−3 或 x≥3。自检：等价于 |x|≥3；或代 x=−4（满足）进原式检验 16≥9 ✓——负支必须保留。",
            },
            "near_transfer": {
                "question": "解 (x−1)² < 4。这次解是双分支还是区间？为什么与上一题结构相反？",
                "reference_answer": "|x−1|<2 ⇒ −1<x<3，是区间。平方项小于正数意味着点落在两根「之间」（图像在 y=4 下方），大于号才产生两侧分支。",
            },
            "far_transfer": {
                "question": "求 √(2x−1) + √(3−x) 有意义的 x 范围，指出每个约束各自贡献了区间的哪一端。",
                "reference_answer": "需 2x−1≥0 且 3−x≥0 ⇒ x≥1/2 且 x≤3，即 [1/2, 3]。左端点来自第一个根号，右端点来自第二个根号——丢掉任何一侧约束都会截错区间。",
            },
        },
    },
    "mr-003": {
        "student_level": "mid",
        "gold": {
            "skill": "mistake-review",
            "learner_state": "concept_error",
            "diagnosis": "对瑕积分 ∫₋₁¹ 1/x² dx 直接用牛顿-莱布尼茨得 -2，忽略了 x=0 处被积函数无界、积分应按瑕积分定义判断敛散；错因是「原函数存在且可代入」的误用，不是计算错误。",
            "must_address": [
                "重现错误：指出 F(x)=-1/x 在 x=0 无定义，不能直接两端代入相减",
                "归类错因：瑕积分必须拆成 [−1,0) 和 (0,1] 取极限，且每侧发散则整体发散",
                "给出正确流程并给同类陷阱清单（如 1/x 在 [−1,1]、ln x 在 0 处）",
            ],
            "must_not_do": [
                "只说「答案是发散」不解释原代法错在哪一步",
                "把错因归为粗心",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "判断 ∫₁^∞ 1/x^p dx 对哪些 p 收敛，写出极限过程的关键表达式。",
                "reference_answer": "p≠1 时 ∫₁^t x^{−p}dx = (t^{1−p}−1)/(1−p)；t→∞ 时仅当 1−p<0（p>1）收敛，值为 1/(p−1)；p=1 时 ln t→∞ 发散。结论：p>1 收敛，p≤1 发散。",
            },
            "near_transfer": {
                "question": "同样的幂换成区间 (0,1] 上的 ∫₀¹ 1/x^p dx：敛散条件如何反转？指出这次的问题点在哪个端点。",
                "reference_answer": "问题点在瑕点 x=0：∫_ε¹ x^{−p}dx 在 ε→0⁺ 时仅当 1−p>0（p<1）有有限极限。结论反转：p<1 收敛，p≥1 发散——与无穷端恰好互补。",
            },
            "far_transfer": {
                "question": "p-级数 Σ 1/n^p 的敛散性与 ∫₁^∞ 1/x^p 完全一致。积分判别法依赖被积函数的哪三个性质？为什么能「以积判级」？",
                "reference_answer": "要求 f 在 [1,∞) 正、连续、单调递减。此时部分和 Σ₂ⁿ f(k) 被夹在 ∫₁ⁿ f 与 ∫₂^{n+1} f 之间，级数与积分同敛散——p-级数结论直接继承。",
            },
        },
    },
    "mr-008": {
        "student_level": "low",
        "gold": {
            "skill": "mistake-review",
            "learner_state": "concept_error",
            "diagnosis": "认为「大小为 10 的数组下标可以从 1 到 10」，混淆了「元素个数」与「最大下标」；C 中下标从 0 开始，合法范围 0..9，越界写 a[10] 是未定义行为，不是「必然报错」。",
            "must_address": [
                "重现错误心智模型：10 个元素 ≠ 下标到 10，0-based 下标范围 0..9",
                "归类错因：对 0-based 索引的规则性误解（非粗心）",
                "说明越界是未定义行为（可能静默破坏内存），并给防越界检查习惯",
            ],
            "must_not_do": [
                "只说「你越界了」而不纠正心智模型",
                "展开讲整个内存布局/段页机制",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "char buf[8] 要装字符串 \"abcdefg\"（7 个字母）。写出合法下标范围，'\\0' 存在下标几？此时 buf[7] 还能再写吗？",
                "reference_answer": "合法下标 0..7 共 8 字节；7 个字母占 0..6，'\\0' 在下标 7。buf[7] 作为「下标位置」在数组内（不是越界），但它已经是 '\\0'——再写入会覆盖终止符导致字符串无界，写 buf[8] 才是真越界。",
            },
            "near_transfer": {
                "question": "for (int i = 0; i <= strlen(s); i++) s[i] = toupper(s[i])：哪些 i 是安全读？哪个 i 的写入会破坏字符串但不是越界？为什么编译器不报错？",
                "reference_answer": "读 0..strlen(s) 都安全（s[len] 是 '\\0'）；写 s[len] 覆盖 '\\0' 破坏终止符（之后 strlen 会失控），但仍不是越界访问。编译器只查类型不查运行时边界，所以不报错。",
            },
            "far_transfer": {
                "question": "同样的越界写 C 里常「看起来能跑」，Python 的 lst[10] 立即抛 IndexError。两种语言行为差异的根源是什么？对定位 C 的这类 bug 意味着什么？",
                "reference_answer": "C 为性能不做运行时边界检查，越界是未定义行为，后果取决于内存布局（可能静默破坏其他变量）；Python 运行时检查并立即抛错。所以 C 的越界 bug 常常延迟爆发、位置漂移，需要 ASan/Valgrind 这类工具或防御性自查。",
            },
        },
    },
    "mr-015": {
        "student_level": "low",
        "gold": {
            "skill": "mistake-review",
            "learner_state": "concept_error",
            "diagnosis": "把矩阵乘法当可交换（BA 与 AB 混用）；根源是「乘法=数乘推广」的直觉迁移错误，未建立「矩阵乘法=变换复合、顺序不可换」的语义。",
            "must_address": [
                "重现错误：指出题目中用了 BA 而条件要求 AB（或反之）",
                "归类错因：默认交换律成立的规则性误解",
                "给出正确思路并用一个具体 2×2 反例说明 AB≠BA，附检查习惯（每步写明作用顺序）",
            ],
            "must_not_do": [
                "只说「矩阵乘法不满足交换律」这一句结论",
                "归因为粗心",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "A=[[1,1],[0,1]]（剪切），B=[[2,0],[0,1]]（横向拉伸 2 倍）。算出 AB 与 BA，并用「先做什么变换、再做什么」解释两者为什么不同。",
                "reference_answer": "AB=[[2,1],[0,1]]：先 B 后 A——先拉伸再剪切；BA=[[2,2],[0,1]]：先剪切再拉伸。剪切会复制 x 坐标进 y，两个顺序作用在不同坐标上，结果不同。",
            },
            "near_transfer": {
                "question": "D=diag(2,3) 与旋转 45° 的 R：DR 与 RD 是否相等？用「缩放的轴」和「旋转的轴」一句话解释。",
                "reference_answer": "不相等。D 沿固定的坐标轴缩放；R 先把物体的轴转走，DR 是「转完再按原坐标轴拉伸」，RD 是「先拉伸再转」——缩放作用的轴不同，效果不同。",
            },
            "far_transfer": {
                "question": "举一个 A、B 都不是单位阵、也不是彼此幂，但 AB=BA 的例子，并用计算验证。它们可交换的几何原因是什么？",
                "reference_answer": "取同为对角阵：A=diag(2,3), B=diag(5,7)，AB=BA=diag(10,21)。几何上都是沿同一组坐标轴的缩放，先后顺序不影响结果——共享「特征方向」的变换可交换。",
            },
        },
    },
    "dp-001": {
        "student_level": "high",
        "gold": {
            "skill": "deepening-learning",
            "learner_state": "representation_gap",
            "diagnosis": "想要傅里叶变换的本质理解：为什么任何信号能拆成正弦波；应从「正弦基=线性空间的基底、变换=换坐标系」多层展开，而不是重复公式。",
            "must_address": [
                "核心类比：傅里叶变换=把信号投影到正弦波这组「基」上求坐标",
                "解释正弦基为什么特殊：频率成分物理意义清晰（如音高）、微分运算变乘法",
                "指出边界/条件（如可积性）与「不是所有信号都能完美展开」的诚实说明",
            ],
            "must_not_do": [
                "只推导变换公式而不解释「为什么是正弦」",
                "把讲解膨胀成整本信号与系统教程",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "对称方波（±1 交替）的傅里叶级数只含奇次谐波、系数 ∝1/n。用「奇函数在正弦/余弦基下的坐标」解释为什么余弦项全部消失，并说出吉布斯过冲出现在哪里。",
                "reference_answer": "方波关于原点奇对称：偶函数（余弦）与它内积为零 → 余弦系数全 0，只留奇次正弦项。吉布斯过冲出现在每个跳变点两侧，约 9% 的固定过冲，随谐波数增加宽度变窄但不消失。",
            },
            "near_transfer": {
                "question": "「时域卷积 = 频域相乘」——用「复指数是 LTI 系统的特征函数」解释这句话为什么成立，并据此说明低通滤波在频域该做什么操作。",
                "reference_answer": "e^{iωt} 过 LTI 系统输出 H(ω)e^{iωt}（特征函数，特征值 H(ω)）。任意输入按频率展开后每条成分独立缩放，故时域卷积对应频域逐点乘 H(ω)；低通滤波 = 乘以低频段 1、高频段 0 的窗。",
            },
            "far_transfer": {
                "question": "压缩感知用远低于 Nyquist 的采样数重建信号。用「信号在某个基下稀疏」解释这为什么可能，傅里叶基在这个故事里承担什么角色？",
                "reference_answer": "若信号在某个变换基（常见即频域）只有 k 个大系数（稀疏），远少于 Nyquist 的随机线性测量仍携带全部信息，可用 L1 最小化找回稀疏解。傅里叶基提供与测量基不相干、能量集中的表示空间。",
            },
        },
    },
    "dp-005": {
        "student_level": "high",
        "gold": {
            "skill": "deepening-learning",
            "learner_state": "representation_gap",
            "diagnosis": "期望与均值的直觉经常混用且不知何时失效；应讲清「均值=对已有样本的描述统计，期望=对随机变量分布的加权平均（理论值）」以及平均直觉失效的场景（重尾/偏态）。",
            "must_address": [
                "区分：均值描述一组已发生的数；期望是随机变量按概率加权的「长期平均」",
                "大数定律把两者连起来：样本均值随样本量增大趋向期望",
                "给出平均直觉失效的例子（如收入分布重尾：平均工资被少数人拉高）",
            ],
            "must_not_do": [
                "只给 E(X)=Σx·p 的公式",
                "声称「期望就是均值」",
            ],
        },
        "post_test": {
            "isomorphic": {
                "question": "X 服从参数 λ=2 的指数分布。算出 E[X] 与中位数，说明哪个更「典型」以及为什么两者差距这么大。",
                "reference_answer": "E[X]=1/λ=0.5；中位数 m 满足 1−e^{−2m}=0.5 ⇒ m=ln2/2≈0.347。分布右偏（长尾在右侧）把均值拉离典型值，中位数更抗尾部影响，此时中位数更能代表「典型等待时间」。",
            },
            "near_transfer": {
                "question": "方案 A：50% 概率得 100 元、50% 得 0；方案 B：100% 得 45 元。A 的期望更高，但多数人选 B。用期望、方差、效用函数三个概念解释这个选择，并指出期望最大化在什么前提下才正确。",
                "reference_answer": "E[A]=50>45，但 Var[A] 大；风险厌恶者的效用函数是凹的，E[U(A)]<U(E[A])，故选确定的小额。期望最大化仅在「风险中性」或「可大量独立重复（大数定律摊平方差）」时才是最优准则。",
            },
            "far_transfer": {
                "question": "保险公司卖出期望赔付 90 元的保单收 100 元保费：公司为什么敢卖、个人为什么愿意买？「90 元」这个期望对双方的意义有什么本质不同？",
                "reference_answer": "公司承保海量独立保单，大数定律使总赔付收敛到期望，90→100 的差是稳定利润（聚合视角，期望是可实现的长期均值）；个人只买一次，买的是风险转移——用确定的小损失替换灾难性大损失（个体视角，期望不描述他的单次体验）。",
            },
        },
    },
    "wd-001": {
        "student_level": "mid",
        "gold": {
            "skill": "word-deep-dive",
            "learner_state": "word_depth_missing",
            "diagnosis": "对 resilient 只有词典级认知，缺词根拆解（re+sili 回弹）、形近/近义辨析（resistant/tough/flexible）与雅思场景用法。",
            "must_address": [
                "词根词缀：re-（回）+ sili（跳/弹，同 salute/silo 系）→ 弹回 → 韧性强、恢复快",
                "核心义项与例句：材料物理韧性 & 人的心理韧性 & 系统抗冲击（resilient economy）",
                "辨析 resilient vs resistant（弹回来 vs 挡住不进）与雅思场景（环境、心理类话题）",
            ],
            "must_not_do": [
                "只给中文释义「有韧性的」",
                "编造不存在的词源故事",
            ],
        },
    },
    "tm-001": {
        "student_level": "low",
        "gold": {
            "skill": "text-memorizer",
            "learner_state": "memorization_missing",
            "diagnosis": "需要背一段政治原理文字；应先做内容结构分类（因果/论证型），再拆块、压缩关键词、生成主动提取题，而不是让用户重复抄写。",
            "must_address": [
                "结构化拆分：按「论点—理由 1（真理本性）—理由 2（实践特点）」分块",
                "关键词压缩成记忆链并可触发抽背",
                "给出主动提取题（填空/问答）用于自测",
            ],
            "must_not_do": [
                "只重复原文让用户硬背",
                "改变原文字句导致表述失真",
            ],
        },
    },
    "sp-001": {
        "student_level": "low",
        "gold": {
            "skill": "study-plan-builder",
            "learner_state": "constraint_unmapped",
            "diagnosis": "两个月、每天 1.5 小时、目标期末及格的线代计划；应先校准约束（可用总时长 ≈90 小时）与及格所需覆盖面，再拆阶段和每日任务，而不是给理想化排期。",
            "must_address": [
                "约束校准：明确总预算 ~90h 与「及格」对应的掌握范围（以历年卷/考纲为准）",
                "阶段划分与每阶段可交付（如第 1-3 周行列式+矩阵、第 4-6 周方程组+向量组…）",
                "每日任务带时长、含自测与每周复盘调整机制",
            ],
            "must_not_do": [
                "不问约束直接给每天学什么的固定表",
                "覆盖全部线代内容而不区分及格优先级",
            ],
        },
    },
}


def main() -> None:
    cases = [json.loads(line) for line in PATH.open(encoding="utf-8") if line.strip()]
    annotated = 0
    for case in cases:
        annotation = GOLD.get(case["id"])
        if not annotation:
            continue
        case["student_level"] = annotation["student_level"]
        case["gap_type"] = annotation["gold"]["learner_state"]
        case["gold"] = annotation["gold"]
        if "post_test" in annotation:
            case["post_test"] = annotation["post_test"]
        annotated += 1
    if annotated != len(GOLD):
        raise SystemExit(f"expected to annotate {len(GOLD)} cases, matched {annotated}")
    with PATH.open("w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(c, ensure_ascii=False) for c in cases) + "\n")
    from collections import Counter

    levels = Counter(c["student_level"] for c in cases if c["id"] in GOLD)
    print(f"annotated {annotated} cases (v2: harder post-tests + student_level); levels={dict(levels)}")


if __name__ == "__main__":
    main()
