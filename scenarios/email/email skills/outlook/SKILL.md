---
name: outlook
description: |
  Microsoft Outlook Email and Calendar API integration with managed OAuth. Access emails, folders, contacts, calendar events, attachments, and manage mail rules. Use this skill when users want to send and receive emails, manage calendar events, organize folders, or handle contacts in Microsoft 365 / Outlook. For other third party apps, use the api-gateway skill (https://clawhub.ai/byungkyu/api-gateway).
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

# Outlook

Access the Microsoft Outlook Email and Calendar API with managed OAuth authentication. Manage emails, folders, contacts, calendar events, attachments, and mail rules through the Maton gateway.

## Quick Start

```bash
# List recent emails
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/messages?$top=10&$orderby=receivedDateTime desc')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/outlook/{native-api-path}
```

Replace `{native-api-path}` with the actual Microsoft Graph API endpoint path (e.g., `v1.0/me/messages`). The gateway proxies requests to Microsoft Graph and automatically injects your OAuth token.

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

Manage your Outlook OAuth connections at `https://ctrl.maton.ai`.

### List Connections

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=outlook&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Create Connection

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({'app': 'outlook'}).encode()
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
    "app": "outlook",
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

If you have multiple Outlook connections, specify which one to use with the `Maton-Connection` header:

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/messages')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Maton-Connection', '21fd90f9-5935-43cd-b6c8-bde9d915ca80')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

If omitted, the gateway uses the default (oldest) active connection.

## API Reference

### Emails (Messages)

#### List Emails

```bash
GET /outlook/v1.0/me/messages
```

Query parameters (OData system query options):
- `$top` - Number of records to return (max 1000)
- `$skip` - Number of records to skip
- `$orderby` - Sort field (e.g., `receivedDateTime desc`, `subject asc`)
- `$filter` - Filter results (e.g., `contains(subject,'meeting')`)
- `$search` - Search emails (e.g., `"priority"`)
- `$select` - Specific fields (e.g., `subject,receivedDateTime,from`)
- `$expand` - Expand navigation properties

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/messages?$top=20&$orderby=receivedDateTime desc&$select=subject,from,receivedDateTime')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "@odata.context": "https://graph.microsoft.com/v1.0/$metadata#users('me')/messages(subject,from,receivedDateTime)",
  "@odata.nextLink": "https://graph.microsoft.com/v1.0/me/messages?$top=20&$skip=20",
  "value": [
    {
      "@odata.etag": "W/\"ABC123\"",
      "id": "AAMkAGI...",
      "subject": "Weekly Team Standup",
      "from": {
        "emailAddress": {
          "name": "Manager",
          "address": "manager@company.com"
        }
      },
      "receivedDateTime": "2025-02-01T09:30:00Z"
    }
  ]
}
```

#### Get an Email

```bash
GET /outlook/v1.0/me/messages/{message_id}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/messages/AAMkAGI...')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

#### Send an Email

```bash
POST /outlook/v1.0/me/sendMail
Content-Type: application/json

{
  "message": {
    "subject": "Project Update",
    "body": {
      "contentType": "HTML",
      "content": "<h1>Project Update</h1><p>The project is on track for Q1 delivery.</p>"
    },
    "toRecipients": [
      {
        "emailAddress": {
          "address": "recipient@company.com",
          "name": "Recipient Name"
        }
      }
    ],
    "ccRecipients": [
      {
        "emailAddress": {
          "address": "cc@company.com",
          "name": "CC Name"
        }
      }
    ],
    "bccRecipients": [],
    "attachments": [
      {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": "report.pdf",
        "contentType": "application/pdf",
        "contentBytes": "base64_encoded_content"
      }
    ],
    "importance": "normal",
    "isDeliveryReceiptRequested": false,
    "isReadReceiptRequested": false
  },
  "saveToSentItems": true
}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({
    'message': {
        'subject': 'Hello from Outlook API',
        'body': {'contentType': 'Text', 'content': 'This is a test email sent via the Maton Outlook gateway.'},
        'toRecipients': [{'emailAddress': {'address': 'user@example.com'}}]
    },
    'saveToSentItems': true
}).encode()
req = urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/sendMail', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

Returns `202 Accepted` on success.

#### Create a Draft

```bash
POST /outlook/v1.0/me/messages
Content-Type: application/json

{
  "subject": "Draft Proposal",
  "body": {
    "contentType": "HTML",
    "content": "<p>Draft content for review...</p>"
  },
  "toRecipients": [
    {"emailAddress": {"address": "client@example.com"}}
  ]
}
```

#### Send a Draft

```bash
POST /outlook/v1.0/me/messages/{message_id}/send
```

#### Reply to a Message

```bash
POST /outlook/v1.0/me/messages/{message_id}/reply
Content-Type: application/json

{
  "message": {
    "body": {
      "contentType": "Text",
      "content": "Thank you for your email. I will review and get back to you."
    }
  },
  "comment": "Including the team in this reply."
}
```

#### Reply All

```bash
POST /outlook/v1.0/me/messages/{message_id}/replyAll
```

#### Forward a Message

```bash
POST /outlook/v1.0/me/messages/{message_id}/forward
Content-Type: application/json

{
  "toRecipients": [
    {"emailAddress": {"address": "forward@company.com"}}
  ],
  "comment": "Please take a look at this email."
}
```

#### Delete an Email

```bash
DELETE /outlook/v1.0/me/messages/{message_id}
```

#### Move an Email

```bash
POST /outlook/v1.0/me/messages/{message_id}/move
Content-Type: application/json

{
  "destinationId": "destination_folder_id"
}
```

#### Mark as Read / Unread

```bash
PATCH /outlook/v1.0/me/messages/{message_id}
Content-Type: application/json

{
  "isRead": true
}
```

### Folders

#### List Folders (Mailbox)

```bash
GET /outlook/v1.0/me/mailFolders
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/mailFolders')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "value": [
    {"id": "inbox", "displayName": "Inbox", "totalItemCount": 150, "unreadItemCount": 12},
    {"id": "sentitems", "displayName": "Sent Items", "totalItemCount": 500},
    {"id": "drafts", "displayName": "Drafts", "totalItemCount": 3},
    {"id": "deleteditems", "displayName": "Deleted Items", "totalItemCount": 200}
  ]
}
```

#### Create a Folder

```bash
POST /outlook/v1.0/me/mailFolders
Content-Type: application/json

{
  "displayName": "Project Archive",
  "isHidden": false
}
```

#### Get Child Folders

```bash
GET /outlook/v1.0/me/mailFolders/{folder_id}/childFolders
```

#### List Messages in a Folder

```bash
GET /outlook/v1.0/me/mailFolders/{folder_id}/messages
```

### Calendar

#### List Events

```bash
GET /outlook/v1.0/me/events?$top=10&$orderby=start/dateTime asc
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/events?$top=10&$orderby=start/dateTime asc')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "value": [
    {
      "id": "AAMkAGI...",
      "subject": "Team Standup",
      "start": {"dateTime": "2025-02-03T09:00:00", "timeZone": "UTC"},
      "end": {"dateTime": "2025-02-03T09:30:00", "timeZone": "UTC"},
      "attendees": [
        {"emailAddress": {"address": "user@company.com"}, "type": "required", "status": {"response": "accepted"}}
      ],
      "isOnlineMeeting": true,
      "onlineMeetingUrl": "https://teams.microsoft.com/meeting/..."
    }
  ]
}
```

#### Create an Event

```bash
POST /outlook/v1.0/me/events
Content-Type: application/json

{
  "subject": "Product Review Meeting",
  "body": {
    "contentType": "HTML",
    "content": "Monthly product review"
  },
  "start": {
    "dateTime": "2025-03-01T10:00:00",
    "timeZone": "UTC"
  },
  "end": {
    "dateTime": "2025-03-01T11:00:00",
    "timeZone": "UTC"
  },
  "attendees": [
    {"emailAddress": {"address": "colleague@company.com"}, "type": "required"}
  ],
  "isOnlineMeeting": true,
  "location": {
    "displayName": "Microsoft Teams"
  }
}
```

#### Update an Event

```bash
PATCH /outlook/v1.0/me/events/{event_id}
```

#### Delete an Event

```bash
DELETE /outlook/v1.0/me/events/{event_id}
```

#### Get Calendar View

```bash
GET /outlook/v1.0/me/calendarView?startDateTime=2025-02-01T00:00:00Z&endDateTime=2025-02-28T23:59:59Z
```

#### List Calendars

```bash
GET /outlook/v1.0/me/calendars
```

### Contacts

#### List Contacts

```bash
GET /outlook/v1.0/me/contacts?$top=50
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/outlook/v1.0/me/contacts?$top=50')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "value": [
    {
      "id": "AAMkAGI...",
      "displayName": "Jane Doe",
      "emailAddresses": [
        {"name": "Jane Doe", "address": "jane@company.com"}
      ],
      "mobilePhone": "+1 555-1234",
      "businessPhone": "+1 555-5678"
    }
  ]
}
```

#### Create a Contact

```bash
POST /outlook/v1.0/me/contacts
Content-Type: application/json

{
  "givenName": "John",
  "surname": "Smith",
  "emailAddresses": [
    {"address": "john.smith@company.com"}
  ],
  "businessPhones": ["+1 555-0000"],
  "companyName": "Acme Corp"
}
```

#### Update a Contact

```bash
PATCH /outlook/v1.0/me/contacts/{contact_id}
```

#### Delete a Contact

```bash
DELETE /outlook/v1.0/me/contacts/{contact_id}
```

## Code Examples

### JavaScript

```javascript
// List emails
const response = await fetch(
  'https://gateway.maton.ai/outlook/v1.0/me/messages?$top=10',
  {
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`
    }
  }
);
const data = await response.json();

// Send an email
const sendResponse = await fetch(
  'https://gateway.maton.ai/outlook/v1.0/me/sendMail',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      message: {
        subject: 'Hello',
        body: {contentType: 'Text', content: 'Hello from Outlook'},
        toRecipients: [{emailAddress: {address: 'user@example.com'}}]
      }
    })
  }
);
```

### Python

```python
import os
import requests

# List recent emails
response = requests.get(
    'https://gateway.maton.ai/outlook/v1.0/me/messages',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'},
    params={'$top': 10, '$orderby': 'receivedDateTime desc'}
)
data = response.json()

# Send an email
response = requests.post(
    'https://gateway.maton.ai/outlook/v1.0/me/sendMail',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={
        'message': {
            'subject': 'Meeting Reminder',
            'body': {'contentType': 'Text', 'content': 'Reminder: Team meeting at 2pm'},
            'toRecipients': [{'emailAddress': {'address': 'team@company.com'}}]
        }
    }
)

# Create a draft
response = requests.post(
    'https://gateway.maton.ai/outlook/v1.0/me/messages',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={
        'subject': 'Draft Report',
        'body': {'contentType': 'Text', 'content': 'Draft content...'},
        'toRecipients': [{'emailAddress': {'address': 'manager@company.com'}}]
    }
)
```

## Notes

- Outlook uses OData system query options (`$top`, `$skip`, `$filter`, `$orderby`, `$select`, `$search`)
- Message IDs are opaque strings (base64-encoded identifiers)
- `sendMail` returns `202 Accepted` — the actual send is asynchronous
- The `saveToSentItems` parameter controls whether a copy is saved to Sent Items
- Calendar events use dateTime with timeZone — always specify both
- Use `$filter` with `contains(subject,'keyword')` for case-insensitive subject search
- Folders use well-known IDs: `inbox`, `drafts`, `sentitems`, `deleteditems`
- Attachments use `@odata.type` to distinguish file vs item attachments
- IMPORTANT: When using curl commands, use `curl -g` when URLs contain `$` characters or brackets to disable glob parsing

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success with response body |
| 201 | Created successfully |
| 202 | Accepted (sendMail queued) |
| 204 | Success with no content (DELETE operations) |
| 400 | Bad request or missing Outlook connection |
| 401 | Invalid or missing Maton API key |
| 403 | Forbidden - insufficient permissions |
| 404 | Resource not found |
| 413 | Request entity too large |
| 429 | Rate limited |
| 4xx/5xx | Passthrough error from Microsoft Graph API |

Outlook API error responses:

```json
{
  "error": {
    "code": "ErrorInvalidProperty",
    "message": "The property 'invalid_field' does not exist on type 'message'.",
    "innerError": {
      "date": "2025-01-15T12:00:00Z",
      "request-id": "abc123-456def",
      "client-request-id": "abc123-456def"
    }
  }
}
```

## Resources

- [Microsoft Graph API Documentation](https://docs.microsoft.com/en-us/graph/)
- [Outlook Mail API Reference](https://docs.microsoft.com/en-us/graph/api/resources/mail-api-overview)
- [Outlook Calendar API Reference](https://docs.microsoft.com/en-us/graph/api/resources/calendar-api-overview)
- [Microsoft Graph Explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
- [Maton Support](mailto:support@maton.ai)
