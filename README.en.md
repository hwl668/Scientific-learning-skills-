# Scientific Learning Skills

> A student-facing Agent Skills prototype for diagnosis-before-explanation tutoring.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
![Platforms](https://img.shields.io/badge/Platform-Claude%20Code%20|%20Codex%20|%20OpenClaw%20|%20GPTs%20|%20Generic-lightgrey)

[中文版](./README.md)

---

## What It Does

> The outputs below are repository-authored behavior examples. They illustrate the intended interaction pattern; they are not controlled comparisons, live model transcripts, or evidence from real learners.

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

**9 Skills covering nine common learning workflows:**

| You're thinking | Typical match |
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

## Design Comparison Example

The table compares two repository-authored examples to show the design intent behind "diagnose before explaining." It is not an on-the-fly A/B test using the same model and settings.

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

**Design goal**: identify the learner's specific bottleneck before explaining, then reduce information unrelated to that bottleneck.

The checked-in baseline and Skill examples can be scored with `python -B eval.py --all`. This is a heuristic structural check for observable elements such as diagnostic questions, variations, and misconception tables. It does not generate a fresh model response or measure learning outcomes.

---

## Quick Start

```bash
git clone https://github.com/hwl668/Scientific-learning-skills-.git scientific-learning-skills
cd scientific-learning-skills
bash setup.sh # auto-detect AI tools + symlinks + init memory
claude        # start Claude Code; Skills auto-load
```

`setup.sh` supports Linux, macOS, and WSL when the repository is cloned inside the WSL Linux filesystem. Git for Windows may materialize repository symlinks as ordinary files when `core.symlinks=false`, so the Git Bash installation path is not currently supported. The script creates `.claude/skills/` links for a detected Claude Code installation and initializes local `memory/` directories. It only detects the Codex CLI; it does not install these Skills into Codex. See [`deploy/codex.md`](./deploy/codex.md).

Then ask naturally:

```text
> What is a limit? First time learning.
> I can multiply matrices but don't understand what they represent.
> !undermine CET-6
```

Want to inspect the intended behavior first? Browse [`demo/`](./demo/) for repository-authored static examples.

Want a local smoke check? Run:

```bash
python eval.py --quick
```

This checks checked-in text with heuristic rules; it does not call a model or generate new answers. The JSONL structural smoke suite is available separately:

```bash
python -B -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report markdown
```

## v0.2 / v0.3: Experimental Learning Agent Modules

The project currently combines a **Skill Pack with independently runnable experimental CLI modules**. Skills define tutoring behavior; routing, cognitive diagnosis, memory scheduling, evaluation, prompt compilation, and case inspection run as separate components. They are not yet wired into a persistent end-to-end tutoring application.

v0.3 also includes a learned-router baseline trained on synthetic routing data, with hard negatives, a `non-learning` class, and low-confidence fallback.

| Module | Purpose | Command |
|--------|---------|---------|
| Skill Router | Rule-based routing to the right skill | `python -m learning_agent.router "I can multiply matrices but do not know what they mean"` |
| Cognitive Diagnosis | Detects 6 learning bottleneck types | `python -m learning_agent.diagnosis "I can calculate matrix multiplication but do not know why row times column"` |
| Eval Runner | Runs demo or JSONL suites with text/JSON/Markdown reports | `python -m learning_agent.eval.runner --suite evals/cases/smoke.jsonl --report markdown` |
| Prompt Compiler | Builds platform-specific prompts from selected skills and token budgets | `python -m learning_agent.compile --target codex --skills fuzzy,problem,word --output prompt.md --metadata` |
| Learned Router | TF-IDF char n-gram + Logistic Regression baseline with top-k and fallback | `python -m learning_agent.ml_router predict "I can multiply matrices but do not know what they mean"` |

Key datasets:

| File | Provenance and purpose |
|------|------------------------|
| `data/routing_cases.jsonl` | Repository-authored labeled regression cases for the rule router; not a sample of real users or an external holdout |
| `data/diagnosis_cases.jsonl` | Repository-authored labeled diagnosis regression cases; not a sample of real users or an external holdout |
| `data/subject_cases.jsonl` | A catalog for subject/scenario coverage, not learning-outcome data |
| `learning_agent/resources/data/training/router_training_v0.3.jsonl` | Programmatically generated synthetic/silver router training data with hard negatives and `non-learning`; not independent test evidence |
| `evals/cases/smoke.jsonl` | Eight hand-authored child-Skill static-output structural smoke cases; no model is called, and routing accuracy or subject correctness is not tested |

## Evidence Boundaries and Local Verification

| Validation layer | What it supports | What it does not support |
|------------------|------------------|--------------------------|
| `demo/` + `eval.py` | Whether checked-in examples contain selected tutoring structures | Reliable Skill following on unseen prompts |
| Router/diagnosis regression cases | Whether current rules regress on in-repo labeled cases | Generalization to new users, phrasing, or subjects |
| Learned-router grouped-where-possible synthetic holdout (with disclosed fallback) | A synthetic-data baseline and pipeline health check | Accuracy on real traffic or tutoring effectiveness |
| Real-user study | **Not provided yet** | Learning gains, transfer, or long-term retention |

Read learned-router metrics together with the dataset fingerprint and split strategy. A high synthetic-holdout score must not be described as "100% real-world accuracy" or evidence of improved learning outcomes.

See [`artifacts/README.md`](./artifacts/README.md) for the safe format, hashes, split limitations, and intended-use boundary.

Regression checks:

```bash
# Full regression checks need the optional ML and Skill-validation dependencies.
python -m pip install -e ".[ml,validation]"

python -B -m unittest discover -s tests
python -B -m learning_agent.router --eval
python -B -m learning_agent.diagnosis --eval
python -B -m learning_agent.ml_router evaluate
python -B eval.py --quick
```

## Install On Other Platforms

Skills are structured Markdown instruction sets. A host with Agent Skills support can load Skill directories; other platforms can use the Prompt Compiler. Actual adherence depends on the host, model, and tool permissions.

| Platform | Loading method | Notes |
|----------|----------------|-------|
| Claude Code | `.claude/skills/` auto-load | [Guide](./deploy/claude-code.md) |
| OpenAI Codex / API / GPTs | native Skills where supported, or compiled instructions | [Guide](./deploy/codex.md) |
| OpenClaw / OI | Skills directory or system prompt | [Guide](./deploy/openclaw.md) |
| Cursor / Cline / Copilot | rules file or custom instructions | [Guide](./deploy/generic.md) |
| Any agent | system prompt injection | [Guide](./deploy/generic.md) |

Token use depends on the selected Skills. Run `python -B -m learning_agent.compile --target generic --skills all --metadata` for this revision's heuristic estimate; the target model's tokenizer is authoritative.

### Memory Support

Memory powers spaced review and weak-spot tracking. Support depends on whether the agent can read/write local files:

| Platform | Memory support | Notes |
|----------|----------------|-------|
| Claude Code | Permission-dependent | File memory works when the workspace is writable |
| Cursor / Cline | Limited | Usually project-directory writes only |
| OpenClaw | Runtime-dependent | Check filesystem permissions |
| Codex (local workspace) | Sandbox-dependent | `memory/` must be inside a writable root |
| ChatGPT / GPTs | External storage required | Connect persistence through a tool or API |
| OpenAI API | External storage required | The caller owns session state and persistence |

This repository does not provide a hosted user-memory service. Without writable storage, single-turn tutoring instructions can still be loaded, but review state will not persist across sessions.

---

## Usage

When child Skills are loaded and the host supports Skill discovery/matching, describe the problem naturally. The host implementation still determines the final match:

```text
> What's a derivative? First time learning.
> I can compute limits but ε-N makes no sense.
> lim(x→0) (e^x - 1 - x) / x² — stuck, need approach.
> f(x)=ln(x²-1), I got x>1 but answer is x<-1 or x>1.
> !complimentary CET-6
> Help me memorize: Practice is the sole criterion of truth...
> Two months to self-study linear algebra, 1.5 hrs/day.
```

**Memory & tools (when the relevant content-memory Skill is loaded and `memory/` is writable):**

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
- Router model card and safe-artifact notes → [artifacts/README.md](./artifacts/README.md)
- Private vulnerability reporting and data boundaries → [SECURITY.md](./SECURITY.md)
- Contribute → [CONTRIBUTING.md](./CONTRIBUTING.md)
- Roadmap → [docs/roadmap.md](./docs/roadmap.md)

## License

MIT
