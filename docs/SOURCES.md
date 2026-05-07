# Skill Schema Sources

The v0 skill sets now include source-derived `real_tool_schema` objects and
benchmark-facing projections.

The extracted artifacts live in:

```text
data/skills/source_artifacts/
```

The projections preserve the authorization-relevant operational shape while
keeping examples readable. See `docs/SKILL_COLLECTION.md` for the distinction
between raw source schema and benchmark projection.

## Repository / Coding Agent

- GitHub MCP Server: https://github.com/github/github-mcp-server
- GitHub REST OpenAPI description:
  https://github.com/github/rest-api-description
- GitHub REST repository contents API:
  https://docs.github.com/en/rest/repos/contents
- GitHub REST pull requests API:
  https://docs.github.com/en/rest/pulls/pulls
- GitHub REST Actions workflows API:
  https://docs.github.com/en/rest/actions/workflows

## Email / Communication Agent

- Google Discovery API:
  https://developers.google.com/discovery/v1/using
- Gmail API `users.messages.send`:
  https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send
- Slack Web API OpenAPI specs:
  https://github.com/slackapi/slack-api-specs
- Slack Web API `chat.postMessage`:
  https://docs.slack.dev/reference/methods/chat.postMessage/
- Slack Web API `files.upload`:
  https://docs.slack.dev/reference/methods/files.upload
- Slack MCP Server documentation:
  https://docs.slack.dev/ai/slack-mcp-server/

## Cloud / DevOps Workflow

- Botocore CodeDeploy service model:
  https://github.com/boto/botocore/tree/develop/botocore/data/codedeploy/2014-10-06
- AWS CodeDeploy `CreateDeployment`:
  https://docs.aws.amazon.com/codedeploy/latest/APIReference/API_CreateDeployment.html
- Kubernetes API reference:
  https://kubernetes.io/docs/reference/generated/kubernetes-api/
- Kubernetes OpenAPI specs:
  https://github.com/kubernetes/kubernetes/tree/master/api/openapi-spec
- GitHub REST Actions workflows API:
  https://docs.github.com/en/rest/actions/workflows

## Data Analysis / Report Agent

- Google Discovery API:
  https://developers.google.com/discovery/v1/using
- BigQuery API `jobs.query`:
  https://cloud.google.com/bigquery/docs/reference/rest/v2/jobs/query
- Google Drive API `files.export`:
  https://developers.google.com/drive/api/reference/rest/v3/files/export
- Google Sheets API `spreadsheets.values.update`:
  https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/update
