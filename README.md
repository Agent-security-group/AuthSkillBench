# AuthSkillBench

AuthSkillBench is a benchmark for invocation-time authorization of trusted agent
skills. It tests whether a candidate skill invocation should be executed in the
current task and environment context.

The core claim is:

```text
skill-level trust does not imply invocation-time authorization.
```

This repository currently contains a v0 seed benchmark scaffold:

- `docs/`: benchmark definition, global authorization rubric, prompt template,
  and source notes for normalized skill schemas.
- `schemas/`: JSON Schema for benchmark samples.
- `data/skills/`: scenario-level skill sets normalized from real agent/API tool
  schemas.
- `data/samples/`: contrastive seed samples.
- `scripts/`: dataset validation, statistics, and prediction scoring.
- `examples/`: prediction format example.

## Task Format

Each sample gives the model:

```text
Task
Environment
Skill Set
Candidate Invocation
```

There is no per-sample `Policy` field. Instead, the benchmark uses the global
rubric in `docs/RUBRIC.md`.

The expected decision is one of:

```text
Allow | Deny | Ask | Defer | Fallback
```

## Quick Start

Validate the seed dataset:

```bash
python3 scripts/validate_dataset.py data/samples/authskillbench_v0_seed.jsonl
```

Print dataset statistics:

```bash
python3 scripts/print_stats.py data/samples/authskillbench_v0_seed.jsonl
```

Score predictions:

```bash
python3 scripts/score_predictions.py \
  data/samples/authskillbench_v0_seed.jsonl \
  examples/predictions_template.jsonl
```

## Current Scope

The seed set covers four scenarios:

1. Repository / coding agent
2. Email / communication agent
3. Cloud / DevOps workflow
4. Data analysis / report agent

The benchmark is scenario-based and contrastive: the same trusted skill appears
across multiple contexts where it may be allowed, denied, deferred, require user
confirmation, or require a lower-privilege fallback.

