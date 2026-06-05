---
name: sendgrid
description: |
  SendGrid Transactional Email API integration with managed OAuth. Access contacts, templates, sender identities, statistics, and send transactional emails. Use this skill when users want to send transactional emails, manage email templates, or track email delivery analytics. For other third party apps, use the api-gateway skill (https://clawhub.ai/byungkyu/api-gateway).
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

# SendGrid

Access the SendGrid Transactional Email API with managed OAuth authentication. Manage contacts, templates, sender identities, statistics, and send transactional emails through the Maton gateway.

## Quick Start

```bash
# List all contacts
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/sendgrid/v3/marketing/contacts')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/sendgrid/{native-api-path}
```

Replace `{native-api-path}` with the actual SendGrid API endpoint path (e.g., `v3/mail/send`). The gateway proxies requests to SendGrid and automatically injects your OAuth token.

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

Manage your SendGrid OAuth connections at `https://ctrl.maton.ai`.

### List Connections

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=sendgrid&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

### Create Connection

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({'app': 'sendgrid'}).encode()
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
    "app": "sendgrid",
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

If you have multiple SendGrid connections, specify which one to use with the `Maton-Connection` header:

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/sendgrid/v3/marketing/contacts')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Maton-Connection', '21fd90f9-5935-43cd-b6c8-bde9d915ca80')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

If omitted, the gateway uses the default (oldest) active connection.

## API Reference

### Mail Send (Transactional)

Send a transactional email immediately:

```bash
POST /sendgrid/v3/mail/send
Content-Type: application/json

{
  "personalizations": [
    {
      "to": [{"email": "recipient@example.com", "name": "Recipient Name"}],
      "cc": [{"email": "cc@example.com"}],
      "bcc": [{"email": "bcc@example.com"}],
      "subject": "Your Transactional Email Subject"
    }
  ],
  "from": {"email": "sender@example.com", "name": "Sender Name"},
  "reply_to": {"email": "support@example.com", "name": "Support Team"},
  "content": [
    {
      "type": "text/plain",
      "value": "Hello, this is a transactional email."
    },
    {
      "type": "text/html",
      "value": "<html><body><h1>Hello!</h1><p>This is a transactional email.</p></body></html>"
    }
  ],
  "attachments": [
    {
      "content": "base64_encoded_content",
      "filename": "document.pdf",
      "type": "application/pdf",
      "disposition": "attachment"
    }
  ],
  "categories": ["transactional", "welcome"],
  "send_at": 1609488000,
  "batch_id": "batch_id_here",
  "asm": {
    "group_id": 1,
    "groups_to_display": [1, 2]
  },
  "ip_pool_name": "transactional_pool",
  "mail_settings": {
    "sandbox_mode": {"enable": false},
    "bypass_list_management": {"enable": false},
    "bypass_spam_management": {"enable": false},
    "bypass_bounce_management": {"enable": false},
    "footer_settings": {"enable": true, "text": "Footer Text", "html": "<p>Footer HTML</p>"}
  },
  "tracking_settings": {
    "click_tracking": {"enable": true, "enable_text": true},
    "open_tracking": {"enable": true, "substitution_tag": "%open-tracking%"},
    "subscription_tracking": {"enable": true, "text": "Unsubscribe here", "html": "<p>Unsubscribe here</p>"},
    "ganalytics": {"enable": true, "utm_source": "sendgrid", "utm_medium": "email"}
  }
}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
data = json.dumps({
    'personalizations': [{'to': [{'email': 'user@example.com'}], 'subject': 'Welcome!'}],
    'from': {'email': 'hello@myapp.com'},
    'content': [{'type': 'text/plain', 'value': 'Welcome to our platform!'}]
}).encode()
req = urllib.request.Request('https://gateway.maton.ai/sendgrid/v3/mail/send', data=data, method='POST')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
req.add_header('Content-Type', 'application/json')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

Returns `202 Accepted` on success.

### Sender Identities

Manage verified sender identities.

#### List Senders

```bash
GET /sendgrid/v3/senders
```

#### Create Sender

```bash
POST /sendgrid/v3/senders
Content-Type: application/json

{
  "nickname": "Support Team",
  "from": {"email": "support@example.com", "name": "Support"},
  "reply_to": {"email": "support@example.com", "name": "Support"},
  "address": "123 Main St",
  "city": "San Francisco",
  "state": "CA",
  "zip": "94105",
  "country": "US"
}
```

#### Get Sender

```bash
GET /sendgrid/v3/senders/{sender_id}
```

#### Update Sender

```bash
PATCH /sendgrid/v3/senders/{sender_id}
```

#### Delete Sender

```bash
DELETE /sendgrid/v3/senders/{sender_id}
```

Returns `204 No Content` on success.

#### Resend Verification

```bash
POST /sendgrid/v3/senders/{sender_id}/resend_verification
```

### Contacts (Marketing)

#### Create or Update Contacts (Upsert)

```bash
PUT /sendgrid/v3/marketing/contacts
Content-Type: application/json

{
  "contacts": [
    {
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "custom_fields": {
        "e1_T": "Premium"
      }
    }
  ],
  "list_ids": ["list_id_here"]
}
```

#### List Contacts

```bash
GET /sendgrid/v3/marketing/contacts
```

#### Get Contact by Email

```bash
GET /sendgrid/v3/marketing/contacts/search?email=user@example.com
```

#### Delete Contact

```bash
DELETE /sendgrid/v3/marketing/contacts
Content-Type: application/json

{
  "ids": ["contact_id_1", "contact_id_2"],
  "delete_all_contacts": false
}
```

#### Export Contacts

```bash
POST /sendgrid/v3/marketing/contacts/exports
```

### Lists (Contact Groups)

#### Create a List

```bash
POST /sendgrid/v3/marketing/lists
Content-Type: application/json

{
  "name": "Premium Users",
  "contact_count": 0
}
```

#### Get All Lists

```bash
GET /sendgrid/v3/marketing/lists
```

#### Get a List

```bash
GET /sendgrid/v3/marketing/lists/{list_id}
```

#### Update a List

```bash
PATCH /sendgrid/v3/marketing/lists/{list_id}
```

#### Delete a List

```bash
DELETE /sendgrid/v3/marketing/lists/{list_id}
```

Returns `204 No Content` on success.

#### Add Contacts to List

```bash
PUT /sendgrid/v3/marketing/lists/{list_id}/contacts
Content-Type: application/json

{
  "contact_ids": ["contact_id_1", "contact_id_2"]
}
```

### Segments

#### Create a Segment

```bash
POST /sendgrid/v3/marketing/segments
Content-Type: application/json

{
  "name": "Active Users",
  "definition": {
    "condition_type": "and",
    "conditions": [
      {
        "field": "last_clicked",
        "value": "2024-01-01",
        "operator": "gt",
        "is_negative": false
      }
    ]
  }
}
```

#### List Segments

```bash
GET /sendgrid/v3/marketing/segments
```

#### Delete a Segment

```bash
DELETE /sendgrid/v3/marketing/segments/{segment_id}
```

### Templates (Transactional)

Create and manage transactional email templates.

#### List Templates

```bash
GET /sendgrid/v3/templates?generations=legacy,dynamic
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/sendgrid/v3/templates')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "templates": [
    {
      "id": "d-abc123def456",
      "name": "Welcome Email",
      "generation": "dynamic",
      "updated_at": "2025-01-15T10:30:00Z",
      "versions": [
        {
          "id": "v-abc123def456",
          "template_id": "d-abc123def456",
          "active": 1,
          "name": "Version 1",
          "subject": "Welcome to our platform!"
        }
      ]
    }
  ]
}
```

#### Create a Template

```bash
POST /sendgrid/v3/templates
Content-Type: application/json

{
  "name": "Welcome Email",
  "generation": "dynamic"
}
```

#### Get a Template

```bash
GET /sendgrid/v3/templates/{template_id}
```

#### Delete a Template

```bash
DELETE /sendgrid/v3/templates/{template_id}
```

#### Create Template Version

```bash
POST /sendgrid/v3/templates/{template_id}/versions
Content-Type: application/json

{
  "template_id": "d-abc123def456",
  "active": 1,
  "name": "Version 1",
  "html_content": "<html><body>{{content}}</body></html>",
  "plain_content": "{{content}}",
  "subject": "Welcome!"
}
```

#### Activate a Version

```bash
POST /sendgrid/v3/templates/{template_id}/versions/{version_id}/activate
```

### Stats and Analytics

#### Get Global Stats

```bash
GET /sendgrid/v3/stats?start_date=2025-01-01&end_date=2025-01-31&aggregated_by=day
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/sendgrid/v3/stats?start_date=2025-01-01&aggregated_by=day')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
[
  {
    "date": "2025-01-01",
    "stats": [
      {
        "metrics": {
          "blocks": 0,
          "bounce_drops": 0,
          "bounces": 2,
          "clicks": 150,
          "deferred": 1,
          "delivered": 980,
          "invalid_emails": 0,
          "opens": 450,
          "requests": 1000,
          "spam_report_drops": 0,
          "spam_reports": 1,
          "unique_clicks": 120,
          "unique_opens": 380,
          "unsubscribe_drops": 0,
          "unsubscribes": 5
        }
      }
    ]
  }
]
```

#### Get Category Stats

```bash
GET /sendgrid/v3/categories/stats?start_date=2025-01-01&categories=transactional
```

#### Get Mailbox Provider Stats

```bash
GET /sendgrid/v3/mailbox_providers/stats?start_date=2025-01-01
```

### Suppressions

Manage unsubscribes, bounces, invalid emails, and spam reports.

#### List Suppressions

```bash
GET /sendgrid/v3/suppression/unsubscribes

GET /sendgrid/v3/suppression/bounces

GET /sendgrid/v3/suppression/invalid_emails

GET /sendgrid/v3/suppression/spam_reports
```

#### Create Suppression

```bash
POST /sendgrid/v3/suppression/unsubscribes
Content-Type: application/json

{
  "recipient_emails": ["user@example.com"]
}
```

#### Delete Suppression

```bash
DELETE /sendgrid/v3/suppression/bounces/{email}
DELETE /sendgrid/v3/suppression/spam_reports/{email}
```

### Subusers

Manage subusers for multi-account setups.

#### List Subusers

```bash
GET /sendgrid/v3/subusers
```

#### Create Subuser

```bash
POST /sendgrid/v3/subusers
Content-Type: application/json

{
  "username": "subuser_username",
  "email": "subuser@example.com",
  "password": "secure_password",
  "ips": ["1.2.3.4"]
}
```

### IP Pools

Manage dedicated IP pools.

#### List IP Pools

```bash
GET /sendgrid/v3/ip_pools
```

#### Create IP Pool

```bash
POST /sendgrid/v3/ip_pools
Content-Type: application/json

{
  "name": "transactional_pool"
}
```

### Alerts

Configure notification alerts.

#### List Alerts

```bash
GET /sendgrid/v3/alerts
```

#### Create Alert

```bash
POST /sendgrid/v3/alerts
Content-Type: application/json

{
  "type": "stats_notification",
  "email_to": "admin@example.com",
  "frequency": "daily",
  "stats_type": "all"
}
```

## Code Examples

### JavaScript

```javascript
const response = await fetch(
  'https://gateway.maton.ai/sendgrid/v3/mail/send',
  {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.MATON_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      personalizations: [{to: [{email: 'user@example.com'}], subject: 'Hello'}],
      from: {email: 'sender@example.com'},
      content: [{type: 'text/plain', value: 'Hello world'}]
    })
  }
);
const data = await response.json();
```

### Python

```python
import os
import requests

# Send a transactional email
response = requests.post(
    'https://gateway.maton.ai/sendgrid/v3/mail/send',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={
        'personalizations': [{'to': [{'email': 'user@example.com'}], 'subject': 'Hello'}],
        'from': {'email': 'sender@example.com'},
        'content': [{'type': 'text/plain', 'value': 'Hello world'}]
    }
)

# Get stats
response = requests.get(
    'https://gateway.maton.ai/sendgrid/v3/stats?start_date=2025-01-01',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'}
)
data = response.json()
```

## Notes

- The mail send endpoint returns `202 Accepted`, not `200 OK`
- Template IDs are prefixed with `d-` for dynamic templates
- Contact custom fields use naming conventions like `e1_T` (T = text), `e1_N` (number), `e1_D` (date)
- Suppressions are account-wide: unsubscribes affect all mail sent from your account
- Use sandbox mode (`mail_settings.sandbox_mode.enable: true`) for testing without sending real emails
- The API has a 500-email-per-send limit on single requests (use multiple personalizations for bulk)
- Batch IDs allow grouping sends for analytics
- Stats aggregation supports: day, week, month
- IMPORTANT: When using curl commands, use `curl -g` when URLs contain brackets (`fields[]`, `sort[]`) to disable glob parsing

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success with response body |
| 201 | Created successfully |
| 202 | Accepted (mail send queued) |
| 204 | Success with no content (DELETE operations) |
| 400 | Bad request or missing SendGrid connection |
| 401 | Invalid or missing Maton API key |
| 403 | Forbidden - insufficient permissions |
| 404 | Resource not found |
| 413 | Payload too large (email exceeds 30MB) |
| 429 | Rate limited |
| 4xx/5xx | Passthrough error from SendGrid API |

SendGrid error responses include detailed information:

```json
{
  "errors": [
    {
      "message": "The from email is invalid.",
      "field": "from.email",
      "help": "https://sendgrid.com/docs/API_Reference/Web_API_v3/Errors/mail/send.html"
    }
  ]
}
```

## Resources

- [SendGrid API Documentation](https://docs.sendgrid.com)
- [SendGrid API Reference](https://docs.sendgrid.com/api-reference)
- [Transactional Email Guide](https://docs.sendgrid.com/for-developers/sending-email)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
- [Maton Support](mailto:support@maton.ai)
