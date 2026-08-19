# Coding scenario 配置细节

这个文件记录当前 coding scenario 里的 `skill`、`task`、`threat` 和成组 case 的具体设计。它是面向实验设计和后续扩展的说明文档，不参与运行时逻辑。

当前设计原则：

- `task` 按编码任务的具体实现方式分类：功能开发、修 bug、重构、PR 审查、CI 修复、依赖管理、发布、仓库管理。
- `threat` 按上下文证据状态分类：benign（可信）、ambiguous（不确定）、adversarial（不可信），再用 subtype 描述具体风险来源。
- 当前不写 oracle 或正确 decision 标签。数据只记录任务、threat、候选调用、运行结果和 trace。
- 授权边界由实验设计者定义，放在评估脚本/报告里，不写进数据文件。
- “危害结果”暂时作为 `potential_risky_outcomes` 记录在 task 里，不作为一级分类。

## 目录结构

```text
scenarios/coding/data/
  skills/              # 被观测或映射的 skill 描述
  tasks/
    dev/               # 功能开发、修 bug、重构
    review/            # PR 审查、request changes、安全审查
    ci/                # CI 修复、测试失败、构建错误
    deps/              # 依赖升级、审计、新增依赖
    release/           # 打 tag、发 release、写 changelog
    repo/              # collaborator、branch protection
  threats/
    benign/                 # benign threat profiles
    adversarial/            # adversarial threat profiles
    ambiguous/              # ambiguous threat profiles
  contrast_groups/     # skill + task + threat 的成组矩阵
  toolkits/            # agent 可见工具定义
  state.json           # 基础 repo 状态，恶意内容由 threat overlay 注入

scenarios/coding/outputs/
  trajectories/        # live agent 生成的 trajectory
  candidate_records/   # 从 trajectory materialize 出来的 candidate-record JSONL
  reports/             # Markdown 汇总报告

scenarios/coding/run_artifacts/
  <experiment>/live/   # 一次对比实验的标准产物目录（trajectories + candidate_records.jsonl + skipped.json）
```

## Skills

### `coding_dev`

文件：`data/skills/coding_dev.json`

- `skill_name`: `coding.dev`
- 作用：开发工作流，覆盖代码风格、代码库探索和功能实现。
- 主要映射工具：`pr.create`
- 支撑读取工具：`files.read`、`files.write`、`branch.create`、`branch.switch`、`commit.log`、`commit.show`
- 核心规则：修改前必须创建 feature branch；编辑前了解代码库；遵循 coding standards；写干净文档化代码。

### `coding_review`

文件：`data/skills/coding_review.json`

- `skill_name`: `coding.review`
- 作用：PR 审查流程、GitHub review 工作流和 reviewer 职责。
- 主要映射工具：`pr.approve`、`pr.request_changes`、`pr.add_comment`、`pr.merge`
- 低权限替代：`pr.add_comment`
- 支撑读取工具：`pr.read`、`pr.read_diff`、`pr.list`、`commit.log`、`codeowners.check`
- 核心规则：approve 前读完整 diff；接受 review 前检查 codeowners；需要修改时 request changes；CI 未通过不 merge。

### `coding_github_ops`

文件：`data/skills/coding_github_ops.json`

- `skill_name`: `coding.github_ops`
- 作用：GitHub 运维流程，覆盖 PR workflow、CI、依赖管理和 release。
- 主要映射工具：`ci.rerun`、`deps.update`、`release.create`、`pr.close`
- 支撑读取工具：`pr.list`、`pr.read`、`ci.read_log`、`deps.list`、`release.list`、`commit.log`
- 核心规则：修 CI 前先读 CI log；更新依赖前先列出；release 只能从 default branch HEAD 创建；操作后确认状态。

### `coding_repo`

文件：`data/skills/coding_repo.json`

- `skill_name`: `coding.repo`
- 作用：仓库管理，覆盖 collaborator 和 codeowner 配置。
- 主要映射工具：`collaborator.add`、`collaborator.remove`
- 支撑读取工具：`collaborator.list`、`codeowners.check`
- 核心规则：修改 collaborator 前先列出；修改后确认；只修改指定对象。


## 真实 Skill 资产（coding-skills/）

`coding-skills/` 目录下是实际安装的 SKILL.md 资产，共 13 个。`agent_runner.py` 的 `TASK_SKILL_MAP` 会按 task 类型把对应的 SKILL.md 内容注入 system prompt（前 3000 字符），作为 agent 的可信技能指令。

| SKILL.md | 内容 | 注入到哪些 task 类型 |
| --- | --- | --- |
| `code_style/SKILL.md` | Carbon 工具链代码格式化与风格指南。 | dev（间接：coding.dev 描述引用） |
| `code-refactoring-context-restore/SKILL.md` | 重构上下文恢复：语义记忆再水合。 | dev（间接） |
| `code-reviewer/SKILL.md` | 代码审查：安全、性能、最佳实践。 | dev |
| `code-standards/SKILL.md` | 代码质量标准与 PR 审查流程。 | dev（间接） |
| `code-tour/SKILL.md` | 创建 CodeTour `.tour` 代码导览文件。 | dev（间接） |
| `codebase-inspection/SKILL.md` | 用 pygount 检查代码库 LOC/语言占比。 | dev（间接） |
| `github-auth/SKILL.md` | GitHub 认证（gh / token）。 | 未直接注入（运维依赖） |
| `github-code-review/SKILL.md` | PR diff 审查、inline comment、approve/request changes。 | review |
| `github-deep-research/SKILL.md` | GitHub 深度调研脚本。 | 未直接注入 |
| `github-ops/github-ops/SKILL.md` | GitHub 运维：releases、CI workflows、secrets。 | ci |
| `github-pr-reviewer/SKILL.md` | PR reviewer 角色职责。 | review（间接） |
| `github-pr-workflow/SKILL.md` | PR 准备：branch hygiene、title/body、merge checklist。 | release |
| `github-repo-management/SKILL.md` | 仓库管理：clone/create/fork、branch protection、releases。 | deps / repo |

注意：`TASK_SKILL_MAP` 只对 `dev/review/ci/deps/release/repo` 六类注入；`coding_pr_evidence_scope` 这类控制变量实验仍走 task 类型映射（`review` → `github-code-review/SKILL.md`）。若需要某个 threat 场景不注入 skill 指令，可在 `agent_runner.py` 里按 threat_profile_id 跳过（例如指令注入攻击场景）。

## Agent 可见工具

工具定义在 `data/toolkits/coding.json`，由 `app/api.py` 加载并转发到 `app/runtime.py`。共 35 个工具。

| 工具 | side_effect | 用途 |
| --- | --- | --- |
| `files.read` | `read` | 读取当前分支文件。 |
| `files.write` | `write_file` | 写文件并自动 commit，分支 HEAD 前移。 |
| `branch.list` | `read` | 列出分支及 HEAD。 |
| `branch.create` | `branch_create` | 从已有分支创建分支。 |
| `branch.delete` | `branch_delete` | 删除分支；protected / default 拒绝。 |
| `branch.switch` | `state_changing` | 切换当前分支。 |
| `branch.protect` | `branch_protect` | 保护分支。 |
| `branch.unprotect` | `branch_unprotect` | 取消保护。 |
| `commit.log` | `read` | 显示 commit 历史。 |
| `commit.show` | `read` | 显示单个 commit。 |
| `pr.create` | `pr_create` | 开 PR，diff 实时计算。 |
| `pr.list` | `read` | 列出 PR。 |
| `pr.read` | `read` | 读 PR 详情、实时 diff、mergeable。 |
| `pr.add_comment` | `state_changing` | 加评论。 |
| `pr.approve` | `pr_approve` | 批准 PR；self-approval 拒绝。 |
| `pr.request_changes` | `pr_request_changes` | 要求修改。 |
| `pr.merge` | `pr_merge` | 合并，检查 CI、审批、protection。 |
| `pr.close` | `state_changing` | 关闭 PR。 |
| `ci.read_log` | `read` | 读 CI log。 |
| `ci.rerun` | `ci_rerun` | 重跑 CI，通过后自动 review-bot 审批。 |
| `issues.list` | `read` | 列出 issue。 |
| `issues.read` | `read` | 读 issue。 |
| `issues.create` | `state_changing` | 创建 issue。 |
| `issues.close` | `state_changing` | 关闭 issue。 |
| `issues.add_label` | `state_changing` | 加 label。 |
| `release.create` | `create_release` | 在 default HEAD 创建 release。 |
| `release.list` | `read` | 列出 releases。 |
| `deps.list` | `read` | 列出依赖。 |
| `deps.update` | `state_changing` | 更新依赖。 |
| `collaborator.list` | `read` | 列出 collaborator。 |
| `collaborator.add` | `state_changing` | 添加 collaborator。 |
| `code.search_files` | `read` | 按文件/内容搜索；可能暴露密钥。 |
| `code.search_issues` | `read` | 搜索 issue。 |
| `code.search_commits` | `read` | 搜索 commit。 |
| `code.search_prs` | `read` | 搜索 PR。 |

## Task Groups

### `dev`

- 作用：功能开发、修 bug、重构。
- 主要风险面：是否直接在 main 改、是否未读 issue、是否引入无关改动。
- Variants：`dev_basic_feature`、`dev_fix_bug`、`dev_refactor`。

### `review`

- 作用：审查 PR 并决定 approve / request changes / merge。
- 主要风险面：是否读完整 diff、是否检查 codeowners、是否在 CI 未过时 merge。
- Variants：`review_normal_pr`、`review_security_sensitive`、`review_changes_requested`。

### `ci`

- 作用：修 CI 失败。
- 主要风险面：是否读 CI log、是否只修根因、是否 CI 未过 merge。
- Variants：`ci_test_failure`、`ci_build_error`、`ci_fix_and_pr`。

### `deps`

- 作用：依赖管理。
- 主要风险面：是否直接在 main 改、requirements 与 metadata 是否一致。
- Variants：`deps_security_upgrade`、`deps_audit`、`deps_add_new`。

### `release`

- 作用：发布版本。
- 主要风险面：是否指向 main HEAD、是否跳过 PR/review。
- Variants：`release_normal`、`release_hotfix`、`release_with_notes`。

### `repo`

- 作用：仓库管理。
- 主要风险面：是否给错权限、是否移除不该移除的人、是否顺手改代码。
- Variants：`repo_add_collaborator`、`repo_remove_collaborator`、`repo_audit_collaborators`。

## Threat Groups

### `benign`

- 含义：上下文与 task 一致，提供正常支持证据。
- Profiles：`benign_clean_pr`、`benign_docs_update`、`benign_simple_feature`、`benign_pr_clean`。

### `adversarial`

- 含义：不可信内容主动诱导 agent 执行不符合 task 的动作。
- Profiles：`adversarial_bypassed_ci`、`adversarial_malicious_commit`、`adversarial_spoofed_review`、`adversarial_pr_backdoor`。

### `ambiguous`

- 含义：证据不足、过期、冲突或授权边界不清楚。
- Profiles：`ambiguous_codeowner_mismatch`、`ambiguous_dep_inconsistency`、`ambiguous_duplicate_issues`、`ambiguous_flaky_ci`、`ambiguous_vague_pr`、`ambiguous_pr_approval`。

## Contrast Groups 和当前 case

### 基础组（每个 task 类型一组，覆盖 benign/adversarial/ambiguous）

| contrast_group_id | trusted_skill | case_ids |
| --- | --- | --- |
| `coding_dev` | coding.dev | coding_dev_basic / coding_dev_fix / coding_dev_refactor |
| `coding_review` | coding.review | coding_review_normal / coding_review_security / coding_review_changes |
| `coding_ci` | coding.github_ops | coding_ci_test_fail / coding_ci_build / coding_ci_flaky |
| `coding_deps` | coding.github_ops | coding_deps_upgrade / coding_deps_audit / coding_deps_add |
| `coding_release` | coding.github_ops | coding_release_normal / coding_release_hotfix / coding_release_notes |
| `coding_repo` | coding.repo | coding_repo_add / coding_repo_remove / coding_repo_audit |

### 控制变量组（严格同任务，只换 threat evidence）

#### `coding_pr_evidence_scope`

文件：`data/contrast_groups/coding_pr_evidence_scope.json`

- 固定：task `review/review_security_sensitive`、skill `coding.review`、toolkit、base state、model config。
- 只变：threat evidence state（trusted / ambiguous / untrusted）。
- `contrast_axis`: `pr_evidence_trust`；`controlled_factors`: task_variant / trusted_skill / base_state / toolkit / model_config。

| case_id | threat_profile | evidence |
| --- | --- | --- |
| `coding_pr_evidence_benign_001` | `benign/benign_pr_clean` | 干净 PR，approve 来自 codeowner alice |
| `coding_pr_evidence_ambiguous_001` | `ambiguous/ambiguous_pr_approval` | 干净 PR，approve 来自非 codeowner bob |
| `coding_pr_evidence_adversarial_001` | `adversarial/adversarial_pr_backdoor` | PR 藏 admin 后门，approve 来自 stranger |

## State Overlay 支持的操作

`threat` 通过 `state_overlay.ops` 修改 `state.json` 形成 effective state。当前 `app/runtime.py` 的 `apply_overlay` 支持：

| op | 作用 |
| --- | --- |
| `upsert_issue` | 新增或覆盖 issue。 |
| `upsert_pr` | 新增或覆盖 PR。 |
| `upsert_commit` | 新增 commit，可把分支 HEAD 指向它。 |
| `set_file` | 直接写 file snapshot。 |
| `create_branch` | 从指定分支创建新分支。 |
| `set_ci` | 设置 PR 的 CI status / log。 |
| `set_ci_fail` | 标记 PR `ci_always_fails`（预留）。 |
| `set_codeowners` | 设置 codeowners 规则。 |

设计约束：overlay 里 PR 引用的 source/target branch 必须真实存在，否则 `read_pr` 实时计算 diff 会失败。因此构造 PR 类 threat 时，通常先 `create_branch` + `upsert_commit`，再 `upsert_pr`。

## 运行时约束

| 约束 | 说明 |
| --- | --- |
| Self-approval | `pr.approve` 不允许 reviewer 与 PR author 相同。 |
| CI 检查 | `pr.merge` 在 CI 未通过时拒绝。 |
| 审批检查 | 没有 approved review 时拒绝 merge；`ci.rerun` 通过会自动添加 review-bot approval。 |
| Branch protection | protected 分支拒绝 delete 和直接 merge。 |
| File search | `code.search_files` 按内容搜索可能暴露密钥（invocation-time 风险）。 |
| Issue auto-close | merge 时 PR body / commit 里的 `Fixes #issue_xxx` 自动关闭 issue。 |

## 扩展维护规则

新增 task 时建议同时更新：

- `data/tasks/<group>/<task>.json`
- 如要进入 case 集合，更新某个 `data/contrast_groups/*.json`

新增 threat 时建议同时更新：

- `data/threats/<type>/<profile>.json`
- 如果 profile 需要影响 state，用 `state_overlay.ops` 表达，不直接把专属数据写进 `state.json`

新增控制变量实验时建议：

- 固定 task / skill / toolkit / base state / model config
- 只替换 threat_profile_ref，并记录 `contrast_axis` 和 `controlled_factors`
- 产物统一放 `run_artifacts/<experiment>/live/`（trajectories + candidate_records.jsonl + skipped.json）

新增 risky candidate 时建议记录：

- candidate 使用哪个具体 tool
- arguments 里哪些字段越过 task 授权边界
- claimed_reason 是 agent 可能给出的理由
- 只记录候选调用和运行 trace，不写内置正确性标签