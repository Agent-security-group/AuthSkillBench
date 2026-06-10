# Unsafe Invocation Runs

本目录保存非 benign threat 中 agent 提出不安全调用的真实运行。先按 threat type 分，再按风险类型分。

| Threat type | Trajectory 数 | 说明 |
| --- | ---: | --- |
| `ambiguous` | 0 | 上下文不完整、过期或身份/范围不明确；本批运行未产生 unsafe 样本。 |
| `adversarial_untrusted` | 5 | 不可信外部内容诱导了越权候选调用。 |
