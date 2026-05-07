# Case Files

`data/cases/` is a human-manageable view of the JSONL benchmark samples.

The canonical evaluation files remain:

```text
data/samples/authskillbench_v0_seed.jsonl
data/samples/authskillbench_v0_inputs.jsonl
```

The case files split each sample into separate task, environment, invocation,
authorization, and metadata components.

## Layout

```text
data/cases/
  manifest.json
  tasks/<scenario>/<task_type>/<sample_id>.task.json
  environments/<scenario>/<environment_type>/<sample_id>.environment.json
  candidate_invocations/<scenario>/<contrast_group>/<sample_id>.candidate_invocation.json
  authorizations/<scenario>/<decision>/<sample_id>.authorization.json
  metadata/<scenario>/<sample_id>.metadata.json
  samples/<scenario>/<contrast_group>/<sample_id>.sample.json
```

`samples/.../*.sample.json` is the per-sample index. It ties the component files
back together.

## Regenerate Case Files

```bash
python3 scripts/materialize_case_files.py \
  data/samples/authskillbench_v0_seed.jsonl \
  data/cases
```

## Rebuild JSONL From Case Files

```bash
python3 scripts/build_seed_from_case_files.py \
  data/cases \
  data/samples/authskillbench_v0_seed.jsonl
```

After rebuilding the seed JSONL, regenerate model inputs:

```bash
python3 scripts/build_model_inputs.py \
  data/samples/authskillbench_v0_seed.jsonl \
  data/samples/authskillbench_v0_inputs.jsonl
```

This also writes the private scoring map:

```text
data/samples/authskillbench_v0_inputs.id_map.json
```

Then validate:

```bash
python3 scripts/validate_dataset.py data/samples/authskillbench_v0_seed.jsonl
python3 scripts/check_model_inputs.py data/samples/authskillbench_v0_inputs.jsonl --gold data/samples/authskillbench_v0_seed.jsonl
```
