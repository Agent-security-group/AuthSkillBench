# Coding Scenario — 重构方案

## 当前状态（2026-07-24）

已完成：
- ✅ 数据模型：Repository → Branch → Commit → PR → Issue → Release 的因果链
- ✅ runtime.py：核心 28 个方法（files/branch/commit/pr/ci/issue/release/deps/collaborator）
- ✅ api.py：工具路由器，统一 toolkit（28 个工具）
- ✅ state.json：初始状态
- ✅ 因果链验证：files.write → commit ✅，release.create → HEAD ✅

已验证的因果链：
  files.write → 自动产生 commit
  commit → branch.head 前移
  branch.create → 新分支继承 source 的 HEAD
  release.create → 指向当前 HEAD

未验证的因果链（下一步做）：
  branch.create → pr.create → 真实 diff
  ci.rerun → ci_status 更新
  pr.approve → mergeable 检查
  pr.merge → 约束检查（CI + reviews + CODEOWNERS）

## 数据模型

Repository:
  default_branch, current_branch, branches[], commits{}, pulls{}, issues{}, releases[]
  collaborators[], codeowners[], file_snapshots{}, dependencies[]

Branch:
  name, head → commit_id, protected

Commit:
  id, parent, message, files[FileChange], timestamp

PullRequest:
  id, title, body, author, source_branch, target_branch, state, ci_status
  ci_log, reviews[], diff (由 branch diff 实时计算)

## 6 类 Task

- dev: 修 bug 写功能
- review: 审 PR、approve、merge
- ci: 修复 CI 失败
- deps: 升级依赖
- release: 打 tag 发 release
- repo: 管理 collaborator、branch protection

## 3 类 Threat

- adversarial: 有攻击者
- ambiguous: 边界模糊
- benign: 正常场景

## 下一步

1. 跑通完整 workflow：branch → PR → CI → review → merge → release
2. 补充 tasks/ 下的 JSON 数据文件
3. 补充 threats/ 下的 JSON 数据文件
4. 补充 HTTP server（server.py）
5. 把 data/skills/ 按新分类重写