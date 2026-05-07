# V0 Baseline Results

These scores are generated on `data/samples/authskillbench_v0_seed.jsonl`.

## Dataset

```text
samples: 64
scenarios: 4 x 16 samples
decisions:
  Allow: 16
  Ask: 12
  Defer: 12
  Deny: 18
  Fallback: 6
risk_types:
  destructive_write: 12
  external_send: 16
  sensitive_read_export: 16
  state_changing_workflow: 20
```

## Baselines

| Baseline | Accuracy | False Allow Rate | False Non-Allow on Allow | Fallback Decision Accuracy |
| --- | ---: | ---: | ---: | ---: |
| Trust-only | 25.00% | 100.00% | 0.00% | 0.00% |
| Deny-all | 28.12% | 0.00% | 100.00% | 0.00% |
| Rule authorizer | 85.94% | 8.33% | 18.75% | 83.33% |

## Leakage Hardening

Model-facing inputs use opaque hash-like `input_id` values such as
`asb_v0_3e9302b45d99`.
Internal `sample_id` values are kept out of `data/samples/authskillbench_v0_inputs.jsonl`
because many maintenance ids contain decision words such as `allow`, `deny`,
`ask`, `defer`, or `fallback`.

Scoring predictions keyed by `input_id` requires the private sidecar map:

```text
data/samples/authskillbench_v0_inputs.id_map.json
```

## Reproduction

The executable baselines run directly on the internal seed file and therefore
emit internal `sample_id` values. External model predictions should instead be
keyed by `input_id` and scored with `--id-map`.

```bash
python3 scripts/run_baseline.py \
  data/samples/authskillbench_v0_seed.jsonl \
  results/trust_only_predictions.jsonl \
  --mode trust_only

python3 scripts/score_predictions.py \
  data/samples/authskillbench_v0_seed.jsonl \
  results/trust_only_predictions.jsonl
```

Repeat with:

```text
--mode deny_all
--mode rule_authorizer
```

The executable rule authorizer is a lightweight reference baseline, not the
benchmark's main contribution.
