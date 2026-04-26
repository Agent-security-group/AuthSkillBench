# Skill Schema Sources

The v0 skill sets are normalized from public agent/tool/API schemas and
documentation. The normalized benchmark schemas preserve the operational shape
of the tools but may simplify parameters for controlled evaluation.

## Repository / Coding Agent

- GitHub MCP Server: https://github.com/github/github-mcp-server
- GitHub REST repository contents API:
  https://docs.github.com/en/rest/repos/contents
- GitHub REST pull requests API:
  https://docs.github.com/en/rest/pulls/pulls
- GitHub REST Actions workflows API:
  https://docs.github.com/en/rest/actions/workflows

## Email / Communication Agent

- Gmail API `users.messages.send`:
  https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send
- Slack Web API `chat.postMessage`:
  https://docs.slack.dev/reference/methods/chat.postMessage/
- Slack Web API `files.upload`:
  https://docs.slack.dev/reference/methods/files.upload
- Slack MCP Server documentation:
  https://docs.slack.dev/ai/slack-mcp-server/

## Cloud / DevOps Workflow

- AWS CodeDeploy `CreateDeployment`:
  https://docs.aws.amazon.com/codedeploy/latest/APIReference/API_CreateDeployment.html
- Kubernetes API reference:
  https://kubernetes.io/docs/reference/generated/kubernetes-api/
- GitHub REST Actions workflows API:
  https://docs.github.com/en/rest/actions/workflows

## Data Analysis / Report Agent

- BigQuery API `jobs.query`:
  https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/query
- Google Drive API `files.export`:
  https://developers.google.com/drive/api/reference/rest/v3/files/export
- Google Sheets API `spreadsheets.values.update`:
  https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/update

