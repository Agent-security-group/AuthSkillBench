# Generation and Labeling Pipeline

AuthSkillBench v0 uses agent-assisted generation rather than human annotation.
The pipeline should still enforce separation between sample generation,
judgment, and verification.

## Roles

### Generator

Creates candidate samples from a scenario skill set:

- choose a contrast group and candidate skill;
- create task and environment context;
- propose candidate invocation;
- propose expected decision and rationale;
- fill hidden metadata.

### Judge

Receives only the benchmark-facing fields plus the global rubric:

- task;
- environment;
- skill set;
- candidate invocation.

The judge assigns a decision and rationale without seeing the generator's label.

### Verifier

Checks whether the generator label and judge label agree and whether the
rationale follows the global rubric.

The verifier should reject or rewrite samples when:

- the task does not make the authorization boundary clear enough;
- the environment content is implausible;
- the expected decision depends on unstated policy;
- `Ask` and `Defer` are confused;
- `Fallback` has no concrete lower-privilege invocation;
- the candidate skill is not present in the scenario skill set;
- the sample can be solved by static skill risk alone.

## Acceptance Criteria

A sample should be accepted only if:

- the candidate invocation is plausible for an agent to consider;
- the expected decision is grounded in the task and environment;
- the same contrast group contains at least two different labels;
- hidden metadata is complete;
- the fallback invocation, when present, is executable using the same skill set;
- no gold label or metadata is needed to answer the sample.

## Expansion Target

The current seed set has 32 samples. The next target is 64-80 samples:

- keep 4 scenarios;
- add 1-2 contrast groups per scenario;
- increase sensitive read/export coverage;
- preserve enough benign `Allow` samples to measure utility.

