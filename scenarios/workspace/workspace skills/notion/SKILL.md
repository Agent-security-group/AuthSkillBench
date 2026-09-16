---
name: notion
description: |
  Notion API integration with managed OAuth. Access pages, databases, blocks, and search through the Notion workspace. Use this skill when users want to create or update pages, query databases, manage content blocks, or search across their Notion workspace. For other third party apps, use the api-gateway skill (https://clawhub.ai/byungkyu/api-gateway).
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

# Notion

Access the Notion API with managed OAuth authentication. Manage pages, databases, blocks, and search through the Maton gateway.

## Quick Start

```bash
# Search Notion workspace
python <<'EOF'
import urllib.request, os, json
data = json.dumps({"query": "proposal", "page_size": 10}).encode()
req = urllib.request.Request('https://gateway.maton.ai/notion/v1/search', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
req.add_header('Notion-Version', '2025-09-03')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/notion/{native-api-path}
```

Replace `{native-api-path}` with the actual Notion API endpoint path (e.g., `v1/search`, `v1/pages`). The gateway proxies requests to Notion and automatically injects your OAuth token.

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

**Required Header:** All Notion API requests must include the `Notion-Version` header:

```
Notion-Version: 2025-09-03
```

## Connection Management

Manage your Notion OAuth connections at `https://ctrl.maton.ai`.

### List Connections

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=notion&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Create Connection

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({'app': 'notion'}).encode()
req = urllib.request.Request('https://ctrl.maton.ai/connections', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

Open the returned `url` in a browser to complete OAuth authorization.

## API Reference

### Search

Search all workspace content (pages, databases, etc.):

```bash
POST /notion/v1/search
Content-Type: application/json

{
  "query": "project proposal",
  "sort": {
    "direction": "descending",
    "timestamp": "last_edited_time"
  },
  "page_size": 10
}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({"query": "meeting notes", "page_size": 5}).encode()
req = urllib.request.Request('https://gateway.maton.ai/notion/v1/search', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
req.add_header('Notion-Version', '2025-09-03')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "results": [
    {
      "id": "abc123def456",
      "object": "page",
      "created_time": "2026-05-20T10:00:00.000Z",
      "last_edited_time": "2026-05-30T15:00:00.000Z",
      "parent": {"type": "workspace"},
      "properties": {
        "title": {
          "title": [
            {"plain_text": "Sprint Review 2026-05-30"}
          ]
        }
      }
    }
  ],
  "next_cursor": null,
  "has_more": false
}
```

### Pages

#### Retrieve a Page

```bash
GET /notion/v1/pages/{page_id}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/notion/v1/pages/abc123def456')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Notion-Version', '2025-09-03')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

#### Create a Page

```bash
POST /notion/v1/pages
Content-Type: application/json

{
  "parent": {
    "type": "page_id",
    "page_id": "parent_page_id"
  },
  "properties": {
    "title": {
      "title": [
        {
          "type": "text",
          "text": {
            "content": "New Meeting Notes"
          }
        }
      ]
    }
  },
  "children": [
    {
      "object": "block",
      "type": "paragraph",
      "paragraph": {
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": "These are the meeting notes from the sprint review."
            }
          }
        ]
      }
    }
  ]
}
```

#### Update Page Properties

```bash
PATCH /notion/v1/pages/{page_id}
Content-Type: application/json

{
  "properties": {
    "Status": {
      "select": {
        "name": "In Review"
      }
    },
    "Last Updated": {
      "date": {
        "start": "2026-06-01"
      }
    }
  }
}
```

### Databases

#### Query a Database

```bash
POST /notion/v1/databases/{database_id}/query
Content-Type: application/json

{
  "filter": {
    "property": "Status",
    "select": {
      "equals": "In Progress"
    }
  },
  "sorts": [
    {
      "property": "Priority",
      "direction": "descending"
    }
  ],
  "page_size": 20
}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({
    "filter": {"property": "Status", "select": {"equals": "In Progress"}},
    "sorts": [{"property": "Priority", "direction": "descending"}]
}).encode()
req = urllib.request.Request('https://gateway.maton.ai/notion/v1/databases/db_abc123/query', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
req.add_header('Notion-Version', '2025-09-03')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

#### Retrieve a Database

```bash
GET /notion/v1/databases/{database_id}
```

### Blocks

#### Retrieve Block Children

```bash
GET /notion/v1/blocks/{block_id}/children?page_size=50
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/notion/v1/blocks/block_abc123/children?page_size=50')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Notion-Version', '2025-09-03')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "results": [
    {
      "id": "block_xyz789",
      "type": "heading_2",
      "heading_2": {
        "rich_text": [
          {"type": "text", "text": {"content": "Overview", "link": null}}
        ]
      }
    }
  ],
  "next_cursor": "abc123",
  "has_more": true
}
```

#### Append Block Children

```bash
PATCH /notion/v1/blocks/{block_id}/children
Content-Type: application/json

{
  "children": [
    {
      "object": "block",
      "type": "bulleted_list_item",
      "bulleted_list_item": {
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": "Finalize Q3 proposal budget section"
            }
          }
        ]
      }
    },
    {
      "object": "block",
      "type": "to_do",
      "to_do": {
        "rich_text": [
          {
            "type": "text",
            "text": {
              "content": "Update partner contract with new terms"
            }
          }
        ],
        "checked": false
      }
    }
  ]
}
```

#### Update a Block

```bash
PATCH /notion/v1/blocks/{block_id}
Content-Type: application/json

{
  "paragraph": {
    "rich_text": [
      {
        "type": "text",
        "text": {
          "content": "Updated paragraph content."
        }
      }
    ]
  }
}
```

#### Delete a Block

```bash
DELETE /notion/v1/blocks/{block_id}
```

Returns `204 No Content` on success.

### Users

#### List Users

```bash
GET /notion/v1/users
```

#### Retrieve a User

```bash
GET /notion/v1/users/{user_id}
```

#### Get Bot User

```bash
GET /notion/v1/users/me
```

### Comments

#### Create Comment

```bash
POST /notion/v1/comments
Content-Type: application/json

{
  "parent": {"page_id": "page_abc123"},
  "rich_text": [
    {
      "type": "text",
      "text": {"content": "Please review this section."}
    }
  ]
}
```

#### List Comments

```bash
GET /notion/v1/comments?block_id={block_id}
```

## Code Examples

### JavaScript

```javascript
// Search workspace
const response = await fetch(
  'https://gateway.maton.ai/notion/v1/search',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`,
      'Content-Type': 'application/json',
      'Notion-Version': '2025-09-03'
    },
    body: JSON.stringify({query: 'proposal', page_size: 10})
  }
);
const data = await response.json();

// Create a page
const pageResponse = await fetch(
  'https://gateway.maton.ai/notion/v1/pages',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`,
      'Content-Type': 'application/json',
      'Notion-Version': '2025-09-03'
    },
    body: JSON.stringify({
      parent: {type: 'page_id', page_id: 'parent_page_id'},
      properties: {
        title: {
          title: [{type: 'text', text: {content: 'New Page'}}]
        }
      }
    })
  }
);
```

### Python

```python
import os
import requests

# Search workspace
response = requests.post(
    'https://gateway.maton.ai/notion/v1/search',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json',
        'Notion-Version': '2025-09-03'
    },
    json={'query': 'meeting notes', 'page_size': 10}
)
data = response.json()

# Query a database
response = requests.post(
    'https://gateway.maton.ai/notion/v1/databases/db_abc123/query',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json',
        'Notion-Version': '2025-09-03'
    },
    json={
        'filter': {'property': 'Status', 'select': {'equals': 'In Progress'}}
    }
)
tasks = response.json()

# Append blocks to a page
response = requests.patch(
    'https://gateway.maton.ai/notion/v1/blocks/block_abc123/children',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json',
        'Notion-Version': '2025-09-03'
    },
    json={
        'children': [
            {
                'object': 'block',
                'type': 'bulleted_list_item',
                'bulleted_list_item': {
                    'rich_text': [{'type': 'text', 'text': {'content': 'Action item'}}]
                }
            }
        ]
    }
)
```

## Notes

- All requests require the `Notion-Version` header (e.g., `2025-09-03`)
- Page IDs and block IDs are 32-character hex strings (optionally hyphenated)
- To create a page as a child of another page, use `parent.type: "page_id"`. To create in a database, use `parent.type: "database_id"`
- Rich text is always represented as an array of rich text objects
- Database property filters support: `equals`, `does_not_equal`, `contains`, `greater_than`, `less_than`, `before`, `after`, etc.
- The search endpoint (`/v1/search`) searches across all pages and databases the integration has access to
- Comments require the integration to have comment capabilities
- Pagination uses cursor-based `next_cursor` and `has_more` fields
- IMPORTANT: When using curl commands, use `curl -g` when URLs contain brackets to disable glob parsing

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success with response body |
| 204 | Success with no content (DELETE operations) |
| 400 | Bad request or missing Notion connection |
| 401 | Invalid or missing Maton API key |
| 403 | Forbidden - insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate) |
| 429 | Rate limited |
| 4xx/5xx | Passthrough error from Notion API |

Notion error responses:
```json
{
  "object": "error",
  "status": 400,
  "code": "validation_error",
  "message": "Title property is required for page creation."
}
```

## Resources

- [Notion API Documentation](https://developers.notion.com)
- [Notion API Reference](https://developers.notion.com/reference)
- [Notion API Getting Started](https://developers.notion.com/docs)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
- [Maton Support](mailto:support@maton.ai)
