---
name: activecampaign
description: |
  ActiveCampaign Marketing Automation & CRM API integration with managed OAuth. Access contacts, lists, automations, campaigns, deals, tasks, and email tracking data. Use this skill when users want to manage marketing automation, CRM workflows, or customer engagement sequences. For other third party apps, use the api-gateway skill.
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

# ActiveCampaign

Access the ActiveCampaign Marketing Automation & CRM API with managed OAuth authentication. Manage contacts, lists, automations, campaigns, deals, tasks, and email tracking data through the Maton gateway.

## Quick Start

```bash
# List contacts
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/activecampaign/api/3/contacts')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/activecampaign/{native-api-path}
```

Replace `{native-api-path}` with the actual ActiveCampaign API endpoint path (e.g., `api/3/contacts`). The gateway proxies requests to ActiveCampaign and automatically injects your OAuth token.

## Authentication

All requests require the Maton API key in the Authorization header:

```
Authorization: Bearer $MATON_API_KEY
```

## Connection Management

Manage your ActiveCampaign OAuth connections at `https://ctrl.maton.ai`.

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=activecampaign&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## API Reference

### Contacts

#### List Contacts

```bash
GET /activecampaign/api/3/contacts
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/activecampaign/api/3/contacts')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "contacts": [
    {
      "id": "1",
      "email": "user@example.com",
      "firstName": "John",
      "lastName": "Doe",
      "phone": "+15551234567",
      "orgid": "1",
      "cdate": "2025-01-01T00:00:00-05:00",
      "udate": "2025-01-15T10:30:00-05:00",
      "links": {"automationEntries": "https://...", "deals": "https://..."}
    }
  ],
  "meta": {"total": "50"}
}
```

#### Create a Contact

```bash
POST /activecampaign/api/3/contacts
Content-Type: application/json

{
  "contact": {
    "email": "newuser@example.com",
    "firstName": "Jane",
    "lastName": "Smith",
    "phone": "+15559876543",
    "fieldValues": [
      {"field": "1", "value": "Company Name"},
      {"field": "2", "value": "CEO"}
    ]
  }
}
```

#### Get a Contact

```bash
GET /activecampaign/api/3/contacts/{contact_id}
```

#### Update a Contact

```bash
PUT /activecampaign/api/3/contacts/{contact_id}
Content-Type: application/json

{
  "contact": {
    "firstName": "Jane",
    "lastName": "Doe",
    "phone": "+15550000000"
  }
}
```

#### Delete a Contact

```bash
DELETE /activecampaign/api/3/contacts/{contact_id}
```

#### Sync a Contact

```bash
POST /activecampaign/api/3/contact/sync
Content-Type: application/json

{
  "contact": {
    "email": "existing@example.com",
    "firstName": "Updated"
  }
}
```

Creates or updates a contact by email (idempotent).

### Contact Lists

#### List Contact Lists

```bash
GET /activecampaign/api/3/contactLists
```

#### Add Contact to List

```bash
POST /activecampaign/api/3/contactLists
Content-Type: application/json

{
  "contactList": {
    "list": "1",
    "contact": "1",
    "status": 1
  }
}
```

Status: `1` = subscribed, `2` = unsubscribed, `3` = bounce.

#### Remove Contact from List

```bash
DELETE /activecampaign/api/3/contactLists/{id}
```

### Lists

#### List All Lists

```bash
GET /activecampaign/api/3/lists
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/activecampaign/api/3/lists')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "lists": [
    {
      "id": "1",
      "name": "Newsletter",
      "stringid": "newsletter",
      "cdate": "2025-01-01T00:00:00-05:00",
      "subscriber_count": 1500
    }
  ]
}
```

#### Create a List

```bash
POST /activecampaign/api/3/lists
Content-Type: application/json

{
  "list": {
    "name": "VIP Customers",
    "stringid": "vip-customers",
    "sender_name": "Company",
    "sender_addr1": "123 Main St",
    "sender_city": "New York",
    "sender_state": "NY",
    "sender_zip": "10001",
    "sender_country": "US"
  }
}
```

#### Delete a List

```bash
DELETE /activecampaign/api/3/lists/{list_id}
```

### Automations

Automations are triggered sequences of actions.

#### List Automations

```bash
GET /activecampaign/api/3/automations
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/activecampaign/api/3/automations')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "automations": [
    {
      "id": "1",
      "name": "Welcome Series",
      "status": 1,
      "cdate": "2025-01-01T00:00:00-05:00",
      "entered": 500,
      "exited": 300
    }
  ]
}
```

Status: `0` = disabled, `1` = enabled, `2` = inactive.

#### Get an Automation

```bash
GET /activecampaign/api/3/automations/{automation_id}
```

#### Start an Automation

```bash
POST /activecampaign/api/3/automations/{automation_id}/start
```

#### Stop an Automation

```bash
POST /activecampaign/api/3/automations/{automation_id}/stop
```

### Automation Entries

Add contacts to automations.

#### Create Automation Entry

```bash
POST /activecampaign/api/3/automationEntries
Content-Type: application/json

{
  "automationEntry": {
    "automation": "1",
    "contact": "1"
  }
}
```

Adds a contact to an automation workflow trigger.

### Campaigns (Email)

#### List Campaigns

```bash
GET /activecampaign/api/3/campaigns
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/activecampaign/api/3/campaigns')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "campaigns": [
    {
      "id": "1",
      "name": "March Newsletter",
      "type": "single",
      "status": 2,
      "sdate": "2025-03-01T10:00:00-05:00",
      "send_amt": 1000,
      "total_amt": 1000,
      "opens": 250,
      "uniqueopens": 200,
      "clicks": 75
    }
  ]
}
```

#### Create a Campaign

```bash
POST /activecampaign/api/3/campaigns
Content-Type: application/json

{
  "campaign": {
    "type": "single",
    "name": "April Newsletter",
    "sdate": "2025-04-01T10:00:00",
    "status": 0,
    "listid": "1",
    "fromaddr": "newsletter@company.com",
    "fromname": "Company",
    "reply2": "reply@company.com",
    "subject": "April Newsletter",
    "message": "<html><body><h1>April Update</h1></body></html>",
    "text": "April Update - Text version"
  }
}
```

#### Send a Campaign

```bash
POST /activecampaign/api/3/campaigns/{campaign_id}/send
```

### Deals (CRM)

ActiveCampaign includes a built-in CRM.

#### List Deals

```bash
GET /activecampaign/api/3/deals
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/activecampaign/api/3/deals')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "deals": [
    {
      "id": "1",
      "title": "Enterprise Contract",
      "contact": "1",
      "value": 50000,
      "currency": "usd",
      "stage": "1",
      "status": 0,
      "cdate": "2025-01-10T00:00:00-05:00"
    }
  ]
}
```

#### Create a Deal

```bash
POST /activecampaign/api/3/deals
Content-Type: application/json

{
  "deal": {
    "title": "Enterprise License",
    "contact": "1",
    "value": 99000,
    "currency": "usd",
    "stage": "1"
  }
}
```

#### Update a Deal

```bash
PUT /activecampaign/api/3/deals/{deal_id}
```

#### Delete a Deal

```bash
DELETE /activecampaign/api/3/deals/{deal_id}
```

### Tags

#### List Tags

```bash
GET /activecampaign/api/3/tags
```

#### Create a Tag

```bash
POST /activecampaign/api/3/tags
Content-Type: application/json

{
  "tag": {
    "tag": "VIP",
    "tagType": "contact",
    "description": "VIP customer"
  }
}
```

#### Apply Tag to Contact

```bash
POST /activecampaign/api/3/contactTags
Content-Type: application/json

{
  "contactTag": {
    "contact": "1",
    "tag": "1"
  }
}
```

### Tasks

#### List Tasks

```bash
GET /activecampaign/api/3/tasks
```

#### Create a Task

```bash
POST /activecampaign/api/3/tasks
Content-Type: application/json

{
  "task": {
    "title": "Follow up with lead",
    "reltype": "deal",
    "relid": "1",
    "status": 0,
    "duedate": "2025-02-01"
  }
}
```

### Email Activities & Tracking

#### Get Email Bounces

```bash
GET /activecampaign/api/3/email/bounces
```

#### Get Email Stats

```bash
GET /activecampaign/api/3/email/stats
```

### Webhooks

#### Create a Webhook

```bash
POST /activecampaign/api/3/webhooks
Content-Type: application/json

{
  "webhook": {
    "name": "Contact Sync",
    "url": "https://myapp.com/webhooks/ac",
    "method": "post",
    "list": "1",
    "events": ["subscribe", "unsubscribe", "bounce"]
  }
}
```

## Code Examples

### Python

```python
import os
import requests

# List contacts
response = requests.get(
    'https://gateway.maton.ai/activecampaign/api/3/contacts',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'}
)
data = response.json()

# Create contact
response = requests.post(
    'https://gateway.maton.ai/activecampaign/api/3/contacts',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={
        'contact': {'email': 'user@example.com', 'firstName': 'John'}
    }
)
```

## Notes

- ActiveCampaign uses a RESTful API at `/api/3/` — all endpoints start with this prefix
- Contact sync (`/contact/sync`) is idempotent: creates if new, updates if existing (matched by email)
- List subscription status: `1` = subscribed, `2` = unsubscribed, `3` = bounce
- Automation status: `0` = disabled, `1` = enabled, `2` = inactive
- Deal stages are customizable per pipeline
- Custom field values are passed as an array of `{field, value}` objects
- ActiveCampaign combines marketing automation, email marketing, and CRM in one platform
- Timestamps are in ISO 8601 format with timezone offset (e.g., `-05:00`)

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No content |
| 400 | Bad request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not found |
| 422 | Validation error |

## Resources

- [ActiveCampaign API Documentation](https://developers.activecampaign.com)
- [ActiveCampaign API Reference](https://developers.activecampaign.com/reference)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
