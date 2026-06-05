---
name: front
description: |
  Front Shared Inbox API integration with managed OAuth. Access conversations, messages, contacts, inboxes, teammates, rules, and tags for shared inbox collaboration. Use this skill when users want to manage customer conversations, triage support tickets, automate inbox workflows, or collaborate on emails in a shared inbox. For other third party apps, use the api-gateway skill (https://clawhub.ai/byungkyu/api-gateway).
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

# Front

Access the Front Shared Inbox API with managed OAuth authentication. Manage conversations, messages, contacts, inboxes, teammates, rules, and tags for team-based email collaboration and customer support workflows.

## Quick Start

```bash
# List all conversations
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/conversations')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/front/{native-api-path}
```

Replace `{native-api-path}` with the actual Front API endpoint path (e.g., `conversations`). The gateway proxies requests to Front and automatically injects your OAuth token.

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

Manage your Front OAuth connections at `https://ctrl.maton.ai`.

### List Connections

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=front&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Create Connection

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({'app': 'front'}).encode()
req = urllib.request.Request('https://ctrl.maton.ai/connections', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Get Connection

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections/{connection_id}')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "connection": {
    "connection_id": "21fd90f9-5935-43cd-b6c8-bde9d915ca80",
    "status": "ACTIVE",
    "creation_time": "2025-12-08T07:20:53.488460Z",
    "last_updated_time": "2026-01-31T20:03:32.593153Z",
    "url": "https://connect.maton.ai/?session_token=...",
    "app": "front",
    "metadata": {}
  }
}
```

Open the returned `url` in a browser to complete OAuth authorization.

### Delete Connection

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections/{connection_id}', method='DELETE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Specifying Connection

If you have multiple Front connections, specify which one to use with the `Maton-Connection` header:

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/conversations')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Maton-Connection', '21fd90f9-5935-43cd-b6c8-bde9d915ca80')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

If omitted, the gateway uses the default (oldest) active connection.

## API Reference

### Conversations

Conversations are threads of messages in a shared inbox.

#### List Conversations

```bash
GET /front/conversations
```

Query parameters:
- `q` - Search query
- `inbox_id` - Filter by inbox
- `status` - Filter by status (assign, unassigned, archived, deleted, spam)
- `sort_by` - Sort field (created_at, updated_at, custom)
- `sort_order` - Sort order (asc, desc)
- `limit` - Number of records to return (default 25, max 100)
- `page_token` - Pagination token

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/conversations?status=unassigned&limit=25')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "_pagination": {
    "next_page_token": "eyJpdiI6Ik1...",
    "prev_page_token": null
  },
  "_results": [
    {
      "id": "cnv_abc123",
      "subject": "Help with account setup",
      "status": "unassigned",
      "assignee": null,
      "recipient": {
        "name": "Support Team",
        "handle": "support@mycompany.com",
        "role": " recipient"
      },
      "last_message": {
        "id": "msg_xyz789",
        "type": "email",
        "author": {
          "name": "John Doe",
          "email": "john@example.com"
        },
        "body": "I'm having trouble setting up my account...",
        "created_at": 1705315200
      },
      "created_at": 1705315200,
      "updated_at": 1705315500
    }
  ]
}
```

#### Get a Conversation

```bash
GET /front/conversations/{conversation_id}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/conversations/cnv_abc123')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

#### Update a Conversation

```bash
PATCH /front/conversations/{conversation_id}
Content-Type: application/json

{
  "assignee_id": "tea_xyz789",
  "status": "assigned",
  "tags": ["priority", "account-setup"]
}
```

#### Update Conversation Assignee

```bash
PATCH /front/conversations/{conversation_id}/assignee
Content-Type: application/json

{
  "assignee_id": "tea_xyz789"
}
```

#### Update Conversation Tags

```bash
PATCH /front/conversations/{conversation_id}/tags
Content-Type: application/json

{
  "tag_ids": ["tag_111", "tag_222"],
  "teammate_ids": ["tea_xyz789"]
}
```

#### Mark Conversation as Seen

```bash
POST /front/conversations/{conversation_id}/seen
```

#### Mark Conversation as Archived

```bash
POST /front/conversations/{conversation_id}/archive
```

#### Delete (Spam) a Conversation

```bash
POST /front/conversations/{conversation_id}/spam
```

#### Untrash a Conversation

```bash
PATCH /front/conversations/{conversation_id}/untrash
```

### Messages

Individual messages within conversations.

#### List Messages in a Conversation

```bash
GET /front/conversations/{conversation_id}/messages
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/conversations/cnv_abc123/messages')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "_pagination": {...},
  "_results": [
    {
      "id": "msg_xyz789",
      "type": "email",
      "author": {
        "author_id": "tea_xyz789",
        "name": "Support Agent",
        "email": "agent@mycompany.com"
      },
      "body": "Hi John, I'd be happy to help you with your account...",
      "text": "Hi John, I'd be happy to help you with your account...",
      "attachments": [],
      "metadata": {
        "target_type": "email",
        "target": "john@example.com"
      },
      "created_at": 1705315800
    }
  ]
}
```

#### Get a Message

```bash
GET /front/messages/{message_id}
```

#### Send a Reply

```bash
POST /front/conversations/{conversation_id}/messages
Content-Type: application/json

{
  "author_id": "tea_xyz789",
  "body": "Thank you for reaching out. Let me look into this for you.",
  "text": "Thank you for reaching out. Let me look into this for you.",
  "options": {
    "archive": false,
    "signature": true
  }
}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({
    'author_id': 'tea_xyz789',
    'body': '<p>Thank you for your patience. The issue has been resolved.</p>',
    'text': 'Thank you for your patience. The issue has been resolved.',
    'options': {'archive': false, 'signature': true}
}).encode()
req = urllib.request.Request('https://gateway.maton.ai/front/conversations/cnv_abc123/messages', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

#### Send a New Message

```bash
POST /front/messages
Content-Type: application/json

{
  "author_id": "tea_xyz789",
  "subject": "Thank you for your inquiry",
  "body": "<p>Dear Customer, thank you for reaching out...</p>",
  "text": "Dear Customer, thank you for reaching out...",
  "to": ["customer@example.com"],
  "cc": ["manager@mycompany.com"],
  "options": {
    "archive": false,
    "signature": true
  }
}
```

#### Create a Draft

```bash
POST /front/conversations/{conversation_id}/drafts
Content-Type: application/json

{
  "author_id": "tea_xyz789",
  "body": "<p>Let me check on this and get back to you...</p>",
  "text": "Let me check on this and get back to you..."
}
```

### Contacts

Manage customer contacts.

#### List Contacts

```bash
GET /front/contacts
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/contacts?limit=50')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "_pagination": {...},
  "_results": [
    {
      "id": "con_abc456",
      "name": "John Doe",
      "description": "Premium customer",
      "handles": [
        {"handle": "john@example.com", "source": "email"}
      ],
      "groups": [
        {"id": "grp_001", "name": "Premium"}
      ],
      "links": [],
      "updated_at": 1705315200
    }
  ]
}
```

#### Get a Contact

```bash
GET /front/contacts/{contact_id}
```

#### Create a Contact

```bash
POST /front/contacts
Content-Type: application/json

{
  "name": "Jane Smith",
  "description": "New customer inquiry",
  "handles": [
    {"handle": "jane@example.com", "source": "email"}
  ],
  "groups": ["grp_001"]
}
```

#### Update a Contact

```bash
PATCH /front/contacts/{contact_id}
Content-Type: application/json

{
  "name": "Jane Smith-Updated",
  "description": "Returning customer",
  "groups": ["grp_001", "grp_002"]
}
```

#### Delete a Contact

```bash
DELETE /front/contacts/{contact_id}
```

#### Merge Contacts

```bash
POST /front/contacts/{contact_id}/merge
Content-Type: application/json

{
  "contact_ids": ["con_abc456", "con_def789"]
}
```

#### Add Contact Handle

```bash
POST /front/contacts/{contact_id}/handles
Content-Type: application/json

{
  "handle": "jane@company.com",
  "source": "email"
}
```

#### List Contact Conversations

```bash
GET /front/contacts/{contact_id}/conversations
```

### Inboxes

Manage shared inboxes.

#### List Inboxes

```bash
GET /front/inboxes
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/inboxes')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "_results": [
    {
      "id": "inb_abc789",
      "name": "Support Inbox",
      "type": "smtp",
      "address": "support@mycompany.com",
      "send_as": ["support@mycompany.com"],
      "teammate_ids": ["tea_xyz789", "tea_abc123"]
    }
  ]
}
```

#### Get an Inbox

```bash
GET /front/inboxes/{inbox_id}
```

#### List Inbox Conversations

```bash
GET /front/inboxes/{inbox_id}/conversations
```

#### List Inbox Messages

```bash
GET /front/inboxes/{inbox_id}/messages
```

### Teammates

Manage team members.

#### List Teammates

```bash
GET /front/teammates
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/teammates')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "_results": [
    {
      "id": "tea_xyz789",
      "email": "agent@mycompany.com",
      "username": "support_agent",
      "first_name": "Alice",
      "last_name": "Johnson",
      "is_admin": false,
      "is_available": true,
      "inbox_ids": ["inb_abc789"]
    }
  ]
}
```

#### Update Teammate

```bash
PATCH /front/teammates/{teammate_id}
```

### Tags

Manage conversation tags.

#### List Tags

```bash
GET /front/tags
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/front/tags')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "_results": [
    {
      "id": "tag_111",
      "name": "priority",
      "color": "red",
      "highlight": "red"
    },
    {
      "id": "tag_222",
      "name": "billing",
      "color": "blue",
      "highlight": null
    }
  ]
}
```

#### Create a Tag

```bash
POST /front/tags
Content-Type: application/json

{
  "name": "escalation",
  "color": "orange"
}
```

### Rules

Manage automation rules.

#### List Rules

```bash
GET /front/rules
```

#### Create a Rule

```bash
POST /front/rules
Content-Type: application/json

{
  "name": "Auto-assign priority tickets",
  "actions": [
    {"type": "assign_teammate", "teammate_id": "tea_xyz789"}
  ],
  "conditions": [
    {"type": "tag_has", "tag_id": "tag_111"}
  ]
}
```

## Code Examples

### JavaScript

```javascript
// List unassigned conversations
const response = await fetch(
  'https://gateway.maton.ai/front/conversations?status=unassigned',
  {
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`
    }
  }
);
const data = await response.json();

// Send a reply
const replyResponse = await fetch(
  'https://gateway.maton.ai/front/conversations/cnv_abc123/messages',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      author_id: 'tea_xyz789',
      body: '<p>Thanks for reaching out. We will help you shortly.</p>',
      text: 'Thanks for reaching out. We will help you shortly.'
    })
  }
);
```

### Python

```python
import os
import requests

# List conversations
response = requests.get(
    'https://gateway.maton.ai/front/conversations',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'},
    params={'status': 'unassigned', 'limit': 25}
)
data = response.json()

# Send a reply
response = requests.post(
    f'https://gateway.maton.ai/front/conversations/cnv_abc123/messages',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={
        'author_id': 'tea_xyz789',
        'body': '<p>Your issue has been resolved.</p>',
        'text': 'Your issue has been resolved.'
    }
)

# Get a specific conversation
conversation = requests.get(
    'https://gateway.maton.ai/front/conversations/cnv_abc123',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'}
).json()
```

## Notes

- Front uses cursor-based pagination via `page_token` parameters
- Conversation statuses: `assign`, `unassigned`, `archived`, `deleted`, `spam`
- Sending a reply auto-assigns the conversation to the sender if not already assigned
- Use `options.archive: true` when replying to automatically archive the conversation
- Tags must exist before they can be assigned to conversations
- When sending messages, `body` is HTML and `text` is plain text (both can be provided)
- Contact handles are not automatically deduplicated; check for existing contacts before creating
- IMPORTANT: When using curl commands, use `curl -g` when URLs contain brackets to disable glob parsing

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success with response body |
| 201 | Created successfully |
| 204 | Success with no content (DELETE operations) |
| 400 | Bad request or missing Front connection |
| 401 | Invalid or missing Maton API key |
| 403 | Forbidden - insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate resource, merge conflict) |
| 429 | Rate limited |
| 4xx/5xx | Passthrough error from Front API |

Front error responses include detailed information:

```json
{
  "status": 400,
  "title": "Bad Request",
  "message": "The request body is missing required fields: author_id",
  "_links": {
    "related": "https://dev.frontapp.com/reference/errors"
  }
}
```

## Resources

- [Front API Documentation](https://dev.frontapp.com)
- [Front API Reference](https://dev.frontapp.com/reference)
- [Front Developer Portal](https://dev.frontapp.com)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
- [Maton Support](mailto:support@maton.ai)
