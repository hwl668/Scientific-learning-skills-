# Scientific Learning Skills

> Turns AI from answer machine into diagnostic tutor. Student-facing Agent Skills — diagnosis before explanation.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Platforms](https://img.shields.io/badge/Platform-Claude%20Code%20|%20Codex%20|%20OpenClaw%20|%20GPTs%20|%20Generic-lightgrey)]()

[中文版](./README.md)

---

## What It Does

**Look up a word — get more than a translation:**

```
> !undermine CET-6

📌 Saved to memory (new word, review tomorrow)

Meaning: 1. gradually weaken (high frequency) 2. erode foundations
Etymology: under + mine → dig beneath → weaken the foundation
Lookalikes: undermine vs undergo vs undertake vs underline
Exam focus: classic gap-fill discriminator, reading synonym (= weaken)
Common mistake: confusing with underestimate — former is "destroy", latter is "underrate"
```

**"I can calculate but don't get it" — diagnosis before lecture:**

```
> I can multiply matrices but don't understand what matrices represent.

Diagnosis: your sticking point is missing intuition for "linear transformation".
You're not bad at calculation — you're treating matrices as static tables, not actions.

Fix: each column = where a basis vector lands after transformation.
[2 0; 0 3] → stretches x by 2, y by 3.
[0 -1; 1 0] → rotates the plane 90°.

Verify: what does [0,-1; 1,0] do to a square?
Variation: swap to [1,1; 0,1], predict the effect.
```

**9 Skills covering the full learning loop:**

| You're thinking | Auto-triggers |
|----------------|---------------|
| "I want one big learning entry" | `scientific-learning` — routes first, then applies the right mode |
| "Never learned this" | `zero-base-learning` — intuition first |
| "Learned but foggy" | `fuzzy-understanding` — diagnose & fix |
| "Want deeper insight" | `deepening-learning` — multiple perspectives |
| "Can't solve this" | `problem-solving` — step-by-step, no spoilers |
| "Got this wrong" | `mistake-review` — error type + checklist |
| An English word | `word-deep-dive` — full dictionary + spaced review |
| "Help me memorize" | `text-memorizer` — mind map + quiz + weak-spot tracking |
| "Study plan for..." | `study-plan-builder` — phases + tasks + checkpoints |

---

## With vs Without

Same question, different responses:

**User**: I can multiply matrices but don't understand what they represent.

<table>
<tr><th>Bare AI</th><th>With Skills</th></tr>
<tr><td>

> Matrices have three interpretations:
> 1. Linear transformations on space
> 2. Coefficients of linear equations
> 3. Columns = where basis vectors land
>
> In short: a matrix is an action on space.

</td><td>

> Diagnosis: let me ask first —
> 1. Did you learn matrices via equation solving or geometry?
> 2. When you compute, do you have a mental picture?
>
> (waits for answer, then provides targeted fix)

</td></tr>
</table>

**Core difference**: bare AI assumes you need everything — and gives you 80% you don't need. Skills diagnose first, then deliver only what you're missing.

---

## Quick Start

```bash
git clone https://github.com/hwl668/Scientific-learning-skills-.git
cd scientific-learning-skills
./setup.sh    # auto-detect AI tools + symlinks + init memory
claude        # start Claude Code; Skills auto-load
```

Then ask naturally:

```text
> What is a limit? First time learning.
> I can multiply matrices but don't understand what they represent.
> !undermine CET-6
```

Want to inspect the behavior first? Browse [`demo/`](./demo/) for complete transcripts.

Want a local smoke check? Run:

```bash
python eval.py --quick
```

Expected core results:

```text
fuzzy-understanding-matrix  17/20 PASS
zero-base-learning-limit    18/20 PASS
word-deep-dive-undermine    17/20 PASS  [word rubric]
```

## v0.2 / v0.3: Learning Agent Framework

v0.2 upgrades the project from a Skill Pack into a runnable Learning Agent Framework. Skills still define tutoring behavior; framework modules handle routing, cognitive diagnosis, memory scheduling, evaluation, prompt compilation, and subject cases.

v0.3 adds a learned router baseline trained on synthetic routing data with hard negatives and a `non-learning` class, so platform questions like "what model are you?" or "why did image upload fail?" do not get forced into learning skills.

| Module | Purpose | Command |
|--------|---------|---------|
| Skill Router | Rule-based routing to the right skill | `python -m learning_agent.router "I can multiply matrices but do not know what they mean"` |
| Cognitive Diagnosis | Detects 6 learning bottleneck types | `python -m learning_agent.diagnosis "I can calculate matrix multiplication but do not know why row times column"` |
| Eval Runner | Runs demo or JSONL suites with text/JSON/Markdown reports | `python -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report markdown` |
| Prompt Compiler | Builds platform-specific prompts from selected skills and token budgets | `python -m learning_agent.compile --target codex --skills fuzzy,problem,word --output prompt.md --metadata` |
| Learned Router | TF-IDF char n-gram + Logistic Regression baseline with top-k and fallback | `python -m learning_agent.ml_router predict "I can multiply matrices but do not know what they mean"` |

Key datasets:

| Dataset | Purpose |
|---------|---------|
| `data/routing_cases.jsonl` | Router eval cases |
| `data/diagnosis_cases.jsonl` | Cognitive diagnosis eval cases |
| `data/subject_cases.jsonl` | Subject/scenario coverage |
| `data/training/router_training_v0.3.jsonl` | Learned router training data |
| `evals/cases/smoke.jsonl` | Eval Runner smoke suite |

Regression checks:

```bash
python -B -m unittest discover -s tests
python -B -m learning_agent.router --eval
python -B -m learning_agent.diagnosis --eval
python -B -m learning_agent.ml_router evaluate
python -B eval.py --quick
```

## Install On Other Platforms

Skills are platform-agnostic Markdown instruction sets. Combine `RULES.md` + `skills/` into a system prompt, or see [deploy/](./deploy/) for platform-specific notes.

| Platform | Loading method | Notes |
|----------|----------------|-------|
| Claude Code | `.claude/skills/` auto-load | [Guide](./deploy/claude-code.md) |
| OpenAI Codex / GPTs | merged system instructions | [Guide](./deploy/codex.md) |
| OpenClaw / OI | Skills directory or system prompt | [Guide](./deploy/openclaw.md) |
| Cursor / Cline / Copilot | rules file or custom instructions | [Guide](./deploy/generic.md) |
| Any agent | system prompt injection | [Guide](./deploy/generic.md) |

Token budget: all 9 Skills are about 20K-30K tokens. Load only the router or 2-3 focused Skills when context is tight.

### Memory Support

Memory powers spaced review and weak-spot tracking. Support depends on whether the agent can read/write local files:

| Platform | Memory support | Notes |
|----------|----------------|-------|
| Claude Code | Full | Native filesystem access |
| Cursor / Cline | Limited | Usually project-directory writes only |
| OpenClaw | Runtime-dependent | Check filesystem permissions |
| ChatGPT / GPTs | None | Needs external storage via function calling |
| Codex / API | None | Needs external storage API |

Platforms without Memory still support diagnosis, explanations, problem solving, and mistake review.

---

## Usage

No need to select skills manually — describe your problem naturally:

```text
> What's a derivative? First time learning.
> I can compute limits but ε-N makes no sense.
> lim(x→0) (e^x - 1 - x) / x² — stuck, need approach.
> f(x)=ln(x²-1), I got x>1 but answer is x<-1 or x>1.
> !complimentary CET-6
> Help me memorize: Practice is the sole criterion of truth...
> Two months to self-study linear algebra, 1.5 hrs/day.
```

**Memory & tools:**

```text
> review words        # spaced repetition review
> quiz me             # text-memorizer weak-spot quiz
> learning report     # cross-skill summary + weak points
```

```bash
python review.py          # terminal dashboard: due reviews, mastery rate, top weak items
bash skill-creator.sh     # interactive new skill scaffold
```

---

## Learn More

- Design philosophy, cognitive science basis, architecture → [DESIGN.md](./DESIGN.md)
- Contribute → [CONTRIBUTING.md](./CONTRIBUTING.md)
- Roadmap → [docs/roadmap.md](./docs/roadmap.md)

## License

MIT
