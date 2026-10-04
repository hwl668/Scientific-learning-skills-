"""LearningSkillBench: three-condition tutoring benchmark infrastructure.

Modules:
    cases          — schema + loading for bench JSONL files
    validate_cases — CI gate: schema validation + router agreement
    runner         — three-condition response generation (base / generic-tutor / skills)
    judge          — LLM-as-judge scoring (Level 2), TER units, Level-3 grading
    report         — aggregation into report.md / report.json

Status: v0.1 implementation of docs/learning-skill-bench.md. Simulated-learner
results are NOT evidence of real learning outcomes; mock runs are not evidence
of anything except that the pipeline runs.
"""

from learning_agent.bench.cases import BENCH_SOURCES, SUB_SKILLS, load_cases

__all__ = ["BENCH_SOURCES", "SUB_SKILLS", "load_cases"]
