# Adversarial Untrusted

不可信外部内容试图诱导越权调用。

| 子类 | Trajectory 数 | 说明 |
| --- | ---: | --- |
| `content_injection` | 1 | 不可信上下文被写入发送内容。 |
| `export_scope_expansion` | 1 | 有限导出被扩大成外部或包含附件的导出。 |
| `marketing_consent_boundary` | 1 | 营销同意边界被绕过或洗白后触发 campaign send。 |
| `recipient_scope_expansion` | 2 | 收件人范围被扩大，例如隐藏 BCC。 |
