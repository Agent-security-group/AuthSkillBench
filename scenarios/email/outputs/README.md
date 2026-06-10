# Email Run Outputs

本目录保存已整理的真实 agent/tool-calling 运行记录，按四个顶层目录组织：

```text
outputs/
  benign_control_group/
  unsafe_invocation_runs/
  normal_invocation_runs/
  all_candidate_invocations/
```

- `benign_control_group`: `benign` threat，对照组。
- `unsafe_invocation_runs`: `ambiguous` 和 `adversarial_untrusted` threat 中，agent 提出了不安全调用的运行过程。
- `normal_invocation_runs`: `ambiguous` 和 `adversarial_untrusted` threat 中，agent 未提出不安全高影响候选调用的运行过程。
- `all_candidate_invocations`: 所有已抽取 candidate invocation 的 JSONL 汇总。

真实运行 trajectory 共 21 条：

| 顶层目录 | Trajectory 数 |
| --- | ---: |
| `benign_control_group` | 2 |
| `unsafe_invocation_runs` | 5 |
| `normal_invocation_runs` | 14 |

candidate invocation 共 14 条。
