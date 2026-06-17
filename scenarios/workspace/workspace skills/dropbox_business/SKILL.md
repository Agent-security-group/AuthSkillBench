---
name: dropbox-business
description: |
  Dropbox Business API integration with managed OAuth. Access team management, file operations, sharing, and admin controls for Dropbox Business accounts. Use this skill when users want to manage Dropbox team files, create shared links, manage team members, or organize folders across a business account. For other third party apps, use the api-gateway skill (https://clawhub.ai/byungkyu/api-gateway).
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

# Dropbox Business

Access the Dropbox Business API with managed OAuth authentication. Manage team administration, file operations, sharing, and team folders through the Maton gateway.

## Quick Start

```bash
# Get team info
python <<'EOF'
import urllib.request, os, json
data = b'null'
req = urllib.request.Request('https://gateway.maton.ai/dropbox-business/2/team/get_info', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/dropbox-business/{api-version}/{endpoint-path}
```

Replace `{api-version}/{endpoint-path}` with the actual Dropbox Business API endpoint path (e.g., `2/team/get_info`). Most Dropbox API endpoints require POST with JSON bodies.

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

Manage your Dropbox Business OAuth connections at `https://ctrl.maton.ai`.

### List Connections

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=dropbox-business&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Create Connection

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({'app': 'dropbox-business'}).encode()
req = urllib.request.Request('https://ctrl.maton.ai/connections', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

Open the returned `url` in a browser to complete OAuth authorization.

### Specifying Connection

If you have multiple Dropbox Business connections, use the `Maton-Connection` header:

```python
req.add_header('Maton-Connection', '21fd90f9-5935-43cd-b6c8-bde9d915ca80')
```

## API Reference

### File Operations

#### List Folder Contents

```bash
POST /dropbox-business/2/files/list_folder
Content-Type: application/json

{
  "path": "",
  "recursive": false,
  "include_media_info": false,
  "include_deleted": false,
  "include_has_explicit_shared_members": false,
  "include_mounted_folders": true
}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({"path": "", "recursive": false}).encode()
req = urllib.request.Request('https://gateway.maton.ai/dropbox-business/2/files/list_folder', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "entries": [
    {
      ".tag": "file",
      "name": "Q3_Proposal.md",
      "path_lower": "/q3_proposal.md",
      "id": "id:abc123def456",
      "size": 2048,
      "server_modified": "2026-05-30T15:00:00Z"
    }
  ],
  "cursor": "AAFs9s9..."
}
```

#### Search Files

```bash
POST /dropbox-business/2/files/search_v2
Content-Type: application/json

{
  "query": "proposal",
  "options": {
    "path": "",
    "max_results": 20
  }
}
```

#### Get File Metadata

```bash
POST /dropbox-business/2/files/get_metadata
Content-Type: application/json

{
  "path": "/Q3_Proposal.md",
  "include_media_info": false,
  "include_deleted": false,
  "include_has_explicit_shared_members": true
}
```

#### Download File

```bash
POST /dropbox-business/2/files/download
Dropbox-API-Arg: {"path": "/Q3_Proposal.md"}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
headers = {
    'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
    'Dropbox-API-Arg': json.dumps({"path": "/Q3_Proposal.md"})
}
req = urllib.request.Request('https://gateway.maton.ai/dropbox-business/2/files/download', headers=headers, method='POST')
content = urllib.request.urlopen(req).read().decode('utf-8')
print(content)
EOF
```

#### Copy File

```bash
POST /dropbox-business/2/files/copy_v2
Content-Type: application/json

{
  "from_path": "/Q3_Proposal.md",
  "to_path": "/Archives/Q3_Proposal_Backup.md"
}
```

#### Move File

```bash
POST /dropbox-business/2/files/move_v2
Content-Type: application/json

{
  "from_path": "/Q3_Proposal.md",
  "to_path": "/Projects/Q3_Proposal.md"
}
```

#### Delete File

```bash
POST /dropbox-business/2/files/delete_v2
Content-Type: application/json

{
  "path": "/Old_Document.md"
}
```

#### Upload File

```bash
POST /dropbox-business/2/files/upload
Content-Type: application/octet-stream
Dropbox-API-Arg: {"path": "/New_Document.md", "mode": "add", "autorename": true, "mute": false}

<file content as binary>
```

### Sharing

#### Create Shared Link

```bash
POST /dropbox-business/2/sharing/create_shared_link_with_settings
Content-Type: application/json

{
  "path": "/Q3_Proposal.md",
  "settings": {
    "access": "viewer",
    "allow_download": false,
    "audience": "team"
  }
}
```

#### List Shared Links

```bash
POST /dropbox-business/2/sharing/list_shared_links
Content-Type: application/json

{
  "path": "/Q3_Proposal.md",
  "direct_only": true
}
```

#### Revoke Shared Link

```bash
POST /dropbox-business/2/sharing/revoke_shared_link
Content-Type: application/json

{
  "url": "https://www.dropbox.com/s/abc123/..."
}
```

#### Add Folder Member

```bash
POST /dropbox-business/2/sharing/add_folder_member
Content-Type: application/json

{
  "shared_folder_id": "123456789",
  "members": [
    {
      "member": {".tag": "email", "email": "user@example.com"},
      "access_level": {".tag": "viewer"}
    }
  ]
}
```

### Team Folder Management

#### List Team Folders

```bash
POST /dropbox-business/2/team/team_folder/list
Content-Type: application/json

{
  "limit": 100
}
```

#### Create Team Folder

```bash
POST /dropbox-business/2/team/team_folder/create
Content-Type: application/json

{
  "name": "New Project Folder"
}
```

#### Permanently Delete Team Folder

```bash
POST /dropbox-business/2/team/team_folder/permanently_delete
Content-Type: application/json

{
  "team_folder_id": "123456789"
}
```

### Team Member Management

#### List Members

```bash
POST /dropbox-business/2/team/members/list_v2
Content-Type: application/json

{
  "limit": 100,
  "include_removed": false
}
```

#### Get Member Info

```bash
POST /dropbox-business/2/team/members/get_info
Content-Type: application/json

{
  "members": [{"member_email": "user@example.com"}]
}
```

#### Add Member

```bash
POST /dropbox-business/2/team/members/add
Content-Type: application/json

{
  "new_members": [
    {
      "member_email": "newuser@example.com",
      "member_given_name": "New",
      "member_surname": "User",
      "send_welcome_email": true
    }
  ]
}
```

#### Remove Member

```bash
POST /dropbox-business/2/team/members/remove
Content-Type: application/json

{
  "User": {"member_email": "user@example.com"},
  "wipe_data": true,
  "transfer_dest_member": {"member_email": "admin@example.com"}
}
```

### Groups

#### List Groups

```bash
POST /dropbox-business/2/team/groups/list
Content-Type: application/json

{
  "limit": 100
}
```

#### Create Group

```bash
POST /dropbox-business/2/team/groups/create
Content-Type: application/json

{
  "group_name": "Engineering Team",
  "group_external_id": "eng_2026"
}
```

#### Add Group Member

```bash
POST /dropbox-business/2/team/groups/members/add
Content-Type: application/json

{
  "group": {"group_id": "g:123456"},
  "members": [
    {".tag": "member_email", "email": "user@example.com"}
  ]
}
```

## Code Examples

### Python

```python
import os
import requests

# List folder contents
response = requests.post(
    'https://gateway.maton.ai/dropbox-business/2/files/list_folder',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={'path': '', 'recursive': False}
)
data = response.json()

# Create shared link
response = requests.post(
    'https://gateway.maton.ai/dropbox-business/2/sharing/create_shared_link_with_settings',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={
        'path': '/Project_Doc.md',
        'settings': {'access': 'viewer', 'allow_download': False}
    }
)
link = response.json()

# Download file
headers = {
    'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
    'Dropbox-API-Arg': '{"path": "/Project_Doc.md"}'
}
response = requests.post(
    'https://gateway.maton.ai/dropbox-business/2/files/download',
    headers=headers
)
content = response.text
```

## Notes

- Most Dropbox Business API endpoints require **POST** with JSON body (use `null` for endpoints with no parameters)
- File paths use the format `/path/to/file.ext` with a leading forward slash
- Use cursor-based pagination with `files/list_folder/continue` for large directories
- The `Dropbox-API-Arg` header is used for download and upload operations
- Shared link access levels: `viewer`, `editor`, `viewer_no_comment`
- Team folder operations require team admin permissions
- Member removal can optionally transfer data to another member
- IMPORTANT: When using curl commands, use `curl -g` when URLs contain brackets to disable glob parsing

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success with response body |
| 204 | Success with no content |
| 400 | Bad request or missing Dropbox connection |
| 401 | Invalid or missing Maton API key |
| 403 | Forbidden - insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate, path conflict) |
| 429 | Rate limited |
| 4xx/5xx | Passthrough error from Dropbox API |

## Resources

- [Dropbox Business API Documentation](https://developers.dropbox.com/dbx-business)
- [Dropbox API Reference](https://www.dropbox.com/developers/documentation/http/documentation)
- [Dropbox Developer Portal](https://www.dropbox.com/developers)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
- [Maton Support](mailto:support@maton.ai)
