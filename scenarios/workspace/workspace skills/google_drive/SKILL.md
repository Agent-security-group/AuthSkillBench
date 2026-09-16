---
name: google-drive
description: |
  Google Drive API integration with managed OAuth. Access files, folders, permissions, revisions, and exports in Google Drive. Use this skill when users want to upload, download, organize, share, or manage files and folders in Google Drive. For other third party apps, use the api-gateway skill (https://clawhub.ai/byungkyu/api-gateway).
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

# Google Drive

Access the Google Drive API with managed OAuth authentication. Manage files, folders, permissions, revisions, and exports through the Maton gateway.

## Quick Start

```bash
# List files in Drive
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/google-drive/drive/v3/files?pageSize=10')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/google-drive/{native-api-path}
```

Replace `{native-api-path}` with the actual Google Drive API endpoint path (e.g., `drive/v3/files`). The gateway proxies requests to Google Drive and automatically injects your OAuth token.

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

Manage your Google Drive OAuth connections at `https://ctrl.maton.ai`.

### List Connections

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=google-drive&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Create Connection

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({'app': 'google-drive'}).encode()
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
    "app": "google-drive",
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

If you have multiple Google Drive connections, specify which one to use with the `Maton-Connection` header:

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/google-drive/drive/v3/files')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Maton-Connection', '21fd90f9-5935-43cd-b6c8-bde9d915ca80')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

If omitted, the gateway uses the default (oldest) active connection.

## API Reference

### Files

#### List Files

```bash
GET /google-drive/drive/v3/files?pageSize=10
```

Query parameters:
- `pageSize` - Maximum number of files to return (default 100, max 1000)
- `q` - Query string for filtering (see Google Drive query format)
- `fields` - Selector specifying which fields to include
- `orderBy` - Sort order (e.g., `modifiedTime desc,name`)
- `pageToken` - Pagination token

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/google-drive/drive/v3/files?q=mimeType!="application/vnd.google-apps.folder"&pageSize=10&fields=files(id,name,mimeType,modifiedTime)')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "files": [
    {
      "id": "1abc123def456",
      "name": "Q3_Proposal.md",
      "mimeType": "text/markdown",
      "modifiedTime": "2026-05-30T15:00:00.000Z"
    }
  ]
}
```

#### Get File Metadata

```bash
GET /google-drive/drive/v3/files/{file_id}?fields=id,name,mimeType,size,owners,permissions,modifiedTime
```

#### Download File Content

```bash
GET /google-drive/drive/v3/files/{file_id}?alt=media
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/google-drive/drive/v3/files/1abc123def456?alt=media')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
content = req.open(req).read().decode('utf-8')
print(content)
EOF
```

#### Create File (Upload)

```bash
POST /google-drive/upload/drive/v3/files?uploadType=multipart
Content-Type: multipart/related; boundary=boundary

--boundary
Content-Type: application/json; charset=UTF-8

{
  "name": "Document.md",
  "parents": ["folder_id_here"]
}

--boundary
Content-Type: text/markdown

# New Document

Content goes here.
--boundary--
```

#### Copy File

```bash
POST /google-drive/drive/v3/files/{file_id}/copy
Content-Type: application/json

{
  "name": "Copy of Document.md",
  "parents": ["target_folder_id"]
}
```

#### Update File

```bash
PATCH /google-drive/drive/v3/files/{file_id}
Content-Type: application/json

{
  "name": "Renamed_Document.md",
  "description": "Updated description"
}
```

#### Delete File

```bash
DELETE /google-drive/drive/v3/files/{file_id}
```

Returns `204 No Content` on success.

#### Export File

Export a Google Workspace file (Docs, Sheets, Slides) to a specific MIME type:

```bash
GET /google-drive/drive/v3/files/{file_id}/export?mimeType=application/pdf
```

Supported export formats:
- Google Docs: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`
- Google Sheets: `application/pdf`, `text/csv`, `application/x-vnd.oasis.opendocument.spreadsheet`
- Google Slides: `application/pdf`, `text/plain`

### Permissions

#### List Permissions

```bash
GET /google-drive/drive/v3/files/{file_id}/permissions
```

#### Create Permission

```bash
POST /google-drive/drive/v3/files/{file_id}/permissions
Content-Type: application/json

{
  "role": "reader",
  "type": "user",
  "emailAddress": "user@example.com"
}
```

Roles: `owner`, `organizer`, `fileOrganizer`, `writer`, `commenter`, `reader`

#### Update Permission

```bash
PATCH /google-drive/drive/v3/files/{file_id}/permissions/{permission_id}
Content-Type: application/json

{
  "role": "writer"
}
```

#### Delete Permission

```bash
DELETE /google-drive/drive/v3/files/{file_id}/permissions/{permission_id}
```

### Revisions

#### List Revisions

```bash
GET /google-drive/drive/v3/files/{file_id}/revisions
```

#### Get Revision

```bash
GET /google-drive/drive/v3/files/{file_id}/revisions/{revision_id}
```

### About

Get Drive storage quota and usage:

```bash
GET /google-drive/drive/v3/about?fields=storageQuota
```

## Code Examples

### JavaScript

```javascript
// List files
const response = await fetch(
  'https://gateway.maton.ai/google-drive/drive/v3/files?pageSize=10',
  {
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`
    }
  }
);
const data = await response.json();

// Upload a file
const form = new FormData();
form.append('metadata', new Blob([JSON.stringify({name: 'test.md'})], {type: 'application/json'}));
form.append('file', new Blob(['# Hello World'], {type: 'text/markdown'}));
const uploadResponse = await fetch(
  'https://gateway.maton.ai/google-drive/upload/drive/v3/files?uploadType=multipart',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`
    },
    body: form
  }
);
```

### Python

```python
import os
import requests

# List files
response = requests.get(
    'https://gateway.maton.ai/google-drive/drive/v3/files',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'},
    params={'pageSize': 10, 'fields': 'files(id,name,mimeType)'}
)
data = response.json()

# Download a file
response = requests.get(
    'https://gateway.maton.ai/google-drive/drive/v3/files/1abc123def456?alt=media',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'}
)
content = response.text

# Create a shared link
response = requests.post(
    'https://gateway.maton.ai/google-drive/drive/v3/files/1abc123def456/permissions',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={'role': 'reader', 'type': 'anyone'}
)
```

## Notes

- Use `alt=media` to download file content; omit to get file metadata
- The `files.list` endpoint requires the `q` parameter for efficient filtering
- Google Workspace files (Docs, Sheets, Slides) must be exported via the `export` endpoint; they cannot be downloaded directly with `alt=media`
- File IDs are unique and persistent; directory/Drive IDs use the same format
- The `parents` array specifies the folder containing the file
- Uploads support `uploadType=multipart` (metadata + content) or `uploadType=resumable` (large files)
- Permissions are inherited from parent folders unless explicitly overridden
- IMPORTANT: When using curl commands, use `curl -g` when URLs contain brackets to disable glob parsing

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success with response body |
| 204 | Success with no content (DELETE operations) |
| 206 | Partial content (range request) |
| 400 | Bad request or missing Google Drive connection |
| 401 | Invalid or missing Maton API key |
| 403 | Forbidden - insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate name, stale revision) |
| 429 | Rate limited |
| 4xx/5xx | Passthrough error from Google Drive API |

## Resources

- [Google Drive API Documentation](https://developers.google.com/drive)
- [Google Drive API Reference](https://developers.google.com/drive/api/v3/reference)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
- [Maton Support](mailto:support@maton.ai)
