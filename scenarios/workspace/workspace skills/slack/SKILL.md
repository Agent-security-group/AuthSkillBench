---
name: slack
description: |
  Slack API integration with managed OAuth. Access conversations, messages, files, and workspace administration for team communication and collaboration. Use this skill when users want to send messages, upload files, manage channels, or search Slack conversations. For other third party apps, use the api-gateway skill (https://clawhub.ai/byungkyu/api-gateway).
compatibility: Requires network access and valid Maton API key
metadata:
  author: maton
  version: "1.0"
  clawdbot:
    emoji: 🧠
    requires:
      env:
        - MATON_API_KEY
---

# Slack

Access the Slack API with managed OAuth authentication. Send messages, upload and manage files, list conversations, and interact with Slack workspaces through the Maton gateway.

## Quick Start

```bash
# List conversations
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/slack/api/conversations.list?types=public_channel&limit=10')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/slack/{native-api-path}
```

Replace `{native-api-path}` with the actual Slack Web API method (e.g., `api/chat.postMessage`, `api/files.upload`). The gateway proxies requests to Slack and automatically injects your OAuth token.

## Authentication

All requests require the Maton API key in the Authorization header:

```
Authorization: Bearer $MATON_API_KEY
```

**Environment Variable:** Set your API key as `MATON_API_KEY`:

```bash
export MATON_API_KEY="YOUR_API_KEY"
```

### Getting Your API Key

1. Sign in or create an account at [maton.ai](https://maton.ai)
2. Go to [maton.ai/settings](https://maton.ai/settings)
3. Copy your API key

## Connection Management

Manage your Slack OAuth connections at `https://ctrl.maton.ai`.

### List Connections

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=slack&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Create Connection

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({'app': 'slack'}).encode()
req = urllib.request.Request('https://ctrl.maton.ai/connections', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

Open the returned `url` in a browser to complete OAuth authorization.

### Specifying Connection

If you have multiple Slack connections, use the `Maton-Connection` header:

```python
req.add_header('Maton-Connection', '21fd90f9-5935-43cd-b6c8-bde9d915ca80')
```

## API Reference

### Conversations (Channels)

#### List Conversations

```bash
GET /slack/api/conversations.list?types=public_channel,private_channel&limit=100
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/slack/api/conversations.list?types=public_channel&limit=20')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "ok": true,
  "channels": [
    {
      "id": "C0123456789",
      "name": "team-general",
      "is_channel": true,
      "is_archived": false,
      "topic": {"value": "General team discussion"},
      "purpose": {"value": "For team-wide announcements"},
      "num_members": 15
    }
  ]
}
```

#### Get Conversation Info

```bash
GET /slack/api/conversations.info?channel=C0123456789
```

#### Create Conversation

```bash
POST /slack/api/conversations.create
Content-Type: application/json

{
  "name": "project-q3",
  "is_private": false
}
```

#### Archive Conversation

```bash
POST /slack/api/conversations.archive
Content-Type: application/json

{
  "channel": "C0123456789"
}
```

### Messages

#### Post a Message

```bash
POST /slack/api/chat.postMessage
Content-Type: application/json

{
  "channel": "C0123456789",
  "text": "Hello from the automation team!",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "Hello from the automation team!"
      }
    }
  ]
}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({
    'channel': 'C0123456789',
    'text': 'Q3 proposal has been updated. Please review.',
    'blocks': [
        {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': '*Q3 Proposal Updated*\nThe budget section has been revised. See the attached file for details.'
            }
        }
    ]
}).encode()
req = urllib.request.Request('https://gateway.maton.ai/slack/api/chat.postMessage', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "ok": true,
  "channel": "C0123456789",
  "ts": "1717152000.000001",
  "message": {
    "text": "Q3 proposal has been updated. Please review.",
    "type": "message"
  }
}
```

#### Post Message in Thread

```bash
POST /slack/api/chat.postMessage
Content-Type: application/json

{
  "channel": "C0123456789",
  "thread_ts": "1717152000.000001",
  "text": "This is a reply in the thread."
}
```

#### Update a Message

```bash
POST /slack/api/chat.update
Content-Type: application/json

{
  "channel": "C0123456789",
  "ts": "1717152000.000001",
  "text": "Updated message text"
}
```

#### Delete a Message

```bash
POST /slack/api/chat.delete
Content-Type: application/json

{
  "channel": "C0123456789",
  "ts": "1717152000.000001"
}
```

### Files

#### Upload File

```bash
POST /slack/api/files.upload
Content-Type: multipart/form-data

file: @/path/to/document.md
channels: C0123456789
filename: Q3_Proposal.md
title: Q3 Proposal Document
initial_comment: Here is the updated Q3 proposal for review.
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
import http.client

boundary = '----boundary123'
data = b''
data += f'--{boundary}\r\n'.encode()
data += 'Content-Disposition: form-data; name="channels"\r\n\r\n'.encode()
data += b'C0123456789\r\n'
data += f'--{boundary}\r\n'.encode()
data += 'Content-Disposition: form-data; name="filename"\r\n\r\n'.encode()
data += b'Q3_Proposal.md\r\n'
data += f'--{boundary}\r\n'.encode()
data += 'Content-Disposition: form-data; name="initial_comment"\r\n\r\n'.encode()
data += b'Here is the updated Q3 proposal.\r\n'
data += f'--{boundary}\r\n'.encode()
data += 'Content-Disposition: form-data; name="file"; filename="Q3_Proposal.md"\r\n'.encode()
data += 'Content-Type: text/markdown\r\n\r\n'.encode()
data += b'# Q3 Proposal\n\nBudget: $55,000\n\nUpdated per CFO review.\r\n'
data += f'--{boundary}--\r\n'.encode()

req = urllib.request.Request('https://gateway.maton.ai/slack/api/files.upload', data=data)
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

#### List Files

```bash
GET /slack/api/files.list?channel=C0123456789&count=20
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/slack/api/files.list?count=10')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "ok": true,
  "files": [
    {
      "id": "F0123456789",
      "name": "Q3_Proposal.md",
      "title": "Q3 Proposal Document",
      "mimetype": "text/markdown",
      "size": 2048,
      "url_private": "https://files.slack.com/files-pri/...",
      "channels": ["C0123456789"],
      "created": 1717152000,
      "user": "U0123456789"
    }
  ]
}
```

#### Get File Info

```bash
GET /slack/api/files.info?file=F0123456789
```

#### Delete File

```bash
POST /slack/api/files.delete
Content-Type: application/json

{
  "file": "F0123456789"
}
```

#### Share File in Channel

```bash
POST /slack/api/files.sharedPublicURL
Content-Type: application/json

{
  "file": "F0123456789"
}
```

### Pins

#### Add Pin

```bash
POST /slack/api/pins.add
Content-Type: application/json

{
  "channel": "C0123456789",
  "timestamp": "1717152000.000001"
}
```

#### List Pins

```bash
GET /slack/api/pins.list?channel=C0123456789
```

#### Remove Pin

```bash
POST /slack/api/pins.remove
Content-Type: application/json

{
  "channel": "C0123456789",
  "timestamp": "1717152000.000001"
}
```

### Users

#### List Users

```bash
GET /slack/api/users.list?limit=100
```

#### Get User Info

```bash
GET /slack/api/users.info?user=U0123456789
```

### Search

#### Search Messages

```bash
GET /slack/api/search.messages?query=proposal&count=10
```

#### Search Files

```bash
GET /slack/api/search.files?query=Q3&count=10
```

## Code Examples

### JavaScript

```javascript
// Post a message
const response = await fetch(
  'https://gateway.maton.ai/slack/api/chat.postMessage',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      channel: 'C0123456789',
      text: 'Document has been updated.'
    })
  }
);
const data = await response.json();

// Upload a file (using FormData)
const formData = new FormData();
formData.append('channels', 'C0123456789');
formData.append('file', new Blob(['# Document content']), 'doc.md');
formData.append('initial_comment', 'New document uploaded.');

const uploadResponse = await fetch(
  'https://gateway.maton.ai/slack/api/files.upload',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`
    },
    body: formData
  }
);
```

### Python

```python
import os
import requests

# List channels
response = requests.get(
    'https://gateway.maton.ai/slack/api/conversations.list',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'},
    params={'types': 'public_channel', 'limit': 20}
)
channels = response.json()

# Post a message
response = requests.post(
    'https://gateway.maton.ai/slack/api/chat.postMessage',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={
        'channel': 'C0123456789',
        'text': 'The Q3 proposal has been finalized.'
    }
)

# Upload a file
response = requests.post(
    'https://gateway.maton.ai/slack/api/files.upload',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'},
    data={
        'channels': 'C0123456789',
        'filename': 'Proposal.md',
        'initial_comment': 'Latest version for review.'
    },
    files={'file': ('Proposal.md', '# Q3 Proposal\n\nFinal version.', 'text/markdown')}
)
```

## Notes

- Slack API methods use `https://slack.com/api/{method}` natively; the gateway is at `https://gateway.maton.ai/slack/api/{method}`
- File uploads use `multipart/form-data` content type
- Channel IDs start with `C`, user IDs with `U`, file IDs with `F`
- The `ts` (timestamp) field is used as a message identifier for threading and updates
- Use `types=public_channel,private_channel,mpim,im` to include all conversation types
- Slack rate limits vary by method; the API returns `Retry-After` headers when rate limited
- Messages can include Slack Block Kit blocks for rich formatting
- Bot tokens have different scopes than user tokens; ensure the integration has appropriate OAuth scopes
- IMPORTANT: When using curl commands, use `curl -g` when URLs contain brackets to disable glob parsing

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success; check `ok` field in response body |
| 400 | Bad request or missing Slack connection |
| 401 | Invalid or missing Maton API key |
| 403 | Forbidden - insufficient permissions |
| 404 | Resource not found |
| 429 | Rate limited (check Retry-After header) |
| 4xx/5xx | Passthrough error from Slack API |

Slack responses include an `ok` field indicating success:
```json
{
  "ok": true,
  "channel": "C0123456789",
  "ts": "1717152000.000001"
}
```

Error responses:
```json
{
  "ok": false,
  "error": "not_in_channel"
}
```

## Resources

- [Slack API Documentation](https://api.slack.com)
- [Slack Web API Methods](https://api.slack.com/methods)
- [Slack Block Kit Builder](https://app.slack.com/block-kit-builder)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
- [Maton Support](mailto:support@maton.ai)
