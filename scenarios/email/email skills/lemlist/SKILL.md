---
name: lemlist
description: |
  Lemlist Cold Email Outreach & Sales Engagement API integration with managed OAuth. Access campaigns, leads, email accounts, activities, templates, and A/B testing for cold email and sales sequences. Use this skill when users want to run cold email campaigns, manage lead sequences, or automate multi-channel sales outreach. For other third party apps, use the api-gateway skill.
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

# Lemlist

Access the Lemlist Cold Email Outreach & Sales Engagement API with managed OAuth authentication. Manage campaigns, leads, email accounts, activities, templates, and A/B testing through the Maton gateway.

## Quick Start

```bash
# List campaigns
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/lemlist/api/campaigns')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## Base URL

```
https://gateway.maton.ai/lemlist/{native-api-path}
```

Replace `{native-api-path}` with the actual Lemlist API endpoint path (e.g., `api/campaigns`). The gateway proxies requests to Lemlist and automatically injects your OAuth token.

## Authentication

All requests require the Maton API key in the Authorization header:

```
Authorization: Bearer $MATON_API_KEY
```

## Connection Management

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://ctrl.maton.ai/connections?app=lemlist&status=ACTIVE')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

## API Reference

### Campaigns

#### List Campaigns

```bash
GET /lemlist/api/campaigns
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/lemlist/api/campaigns')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "campaigns": [
    {
      "_id": "abc123def456",
      "name": "Q1 Outreach - SaaS",
      "status": "active",
      "dailyLimit": 100,
      "totalLeads": 500,
      "totalSent": 320,
      "totalOpened": 144,
      "totalReplied": 26,
      "totalClicked": 80,
      "totalBounced": 12,
      "createdAt": "2025-01-15T10:00:00.000Z"
    }
  ]
}
```

#### Create a Campaign

```bash
POST /lemlist/api/campaigns
Content-Type: application/json

{
  "name": "Q2 Outreach",
  "dailyLimit": 50,
  "sendStrategy": "sequential",
  "personalization": {
    "firstName": "{{firstName}}",
    "companyName": "{{companyName}}"
  }
}
```

#### Get a Campaign

```bash
GET /lemlist/api/campaigns/{campaign_id}
```

#### Update a Campaign

```bash
PATCH /lemlist/api/campaigns/{campaign_id}
Content-Type: application/json

{
  "dailyLimit": 75,
  "sendStrategy": "sequential"
}
```

#### Start a Campaign

```bash
POST /lemlist/api/campaigns/{campaign_id}/start
```

#### Pause a Campaign

```bash
POST /lemlist/api/campaigns/{campaign_id}/pause
```

#### Delete a Campaign

```bash
DELETE /lemlist/api/campaigns/{campaign_id}
```

### Leads

#### List Leads

```bash
GET /lemlist/api/leads?campaignId={campaign_id}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/lemlist/api/leads?campaignId=abc123def456')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "leads": [
    {
      "_id": "lead_xyz789",
      "email": "contact@company.com",
      "firstName": "John",
      "lastName": "Smith",
      "companyName": "Acme Corp",
      "campaignId": "abc123def456",
      "status": "pending",
      "personalization": {"industry": "SaaS", "role": "CTO"},
      "addedAt": "2025-01-20T14:30:00.000Z"
    }
  ],
  "total": 500
}
```

#### Create a Lead

```bash
POST /lemlist/api/leads
Content-Type: application/json

{
  "email": "prospect@company.com",
  "firstName": "Alice",
  "lastName": "Johnson",
  "companyName": "TechCorp",
  "campaignId": "abc123def456",
  "personalization": {
    "industry": "SaaS",
    "role": "VP Engineering"
  }
}
```

#### Create Leads (Bulk)

```bash
POST /lemlist/api/leads/bulk
Content-Type: application/json

{
  "campaignId": "abc123def456",
  "leads": [
    {
      "email": "lead1@company.com",
      "firstName": "Alice",
      "companyName": "TechCorp"
    },
    {
      "email": "lead2@company.com",
      "firstName": "Bob",
      "companyName": "DataInc"
    }
  ]
}
```

#### Update a Lead

```bash
PATCH /lemlist/api/leads/{lead_id}
Content-Type: application/json

{
  "firstName": "Alice",
  "companyName": "New Corp"
}
```

#### Delete a Lead

```bash
DELETE /lemlist/api/leads/{lead_id}
```

#### Unsubscribe a Lead

```bash
POST /lemlist/api/leads/{lead_id}/unsubscribe
```

### Sequences

#### List Sequence Steps

```bash
GET /lemlist/api/sequences/{campaign_id}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/lemlist/api/sequences/abc123def456')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "steps": [
    {
      "_id": "step_111aaa",
      "type": "email",
      "index": 0,
      "subject": "Quick question about {companyName}",
      "template": "Hi {firstName},\n\nI saw that {companyName} has been...",
      "delay": 0,
      "abTest": false
    },
    {
      "_id": "step_222bbb",
      "type": "email",
      "index": 1,
      "subject": "Re: Quick question about {companyName}",
      "template": "Following up on my previous email...",
      "delay": 3,
      "abTest": true,
      "abTestVariants": [
        {"subject": "Did you see my last email?", "template": "Alternative version..."},
        {"subject": "Quick question about {companyName}", "template": "Control version..."}
      ]
    },
    {
      "_id": "step_333ccc",
      "type": "linkedin",
      "index": 2,
      "template": "Hi {firstName}, I noticed your work at {companyName}...",
      "delay": 5
    }
  ]
}
```

#### Create Sequence Step

```bash
POST /lemlist/api/sequences/{campaign_id}
Content-Type: application/json

{
  "type": "email",
  "index": 2,
  "subject": "Last try reaching out",
  "template": "Hi {firstName}, just one last try...",
  "delay": 5
}
```

#### Update Sequence Step

```bash
PATCH /lemlist/api/sequences/{campaign_id}/steps/{step_id}
```

#### Delete Sequence Step

```bash
DELETE /lemlist/api/sequences/{campaign_id}/steps/{step_id}
```

### Email Accounts

#### List Email Accounts

```bash
GET /lemlist/api/accounts
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/lemlist/api/accounts')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "accounts": [
    {
      "_id": "acc_456def",
      "email": "sales@mycompany.com",
      "provider": "gmail",
      "dailyLimit": 50,
      "status": "connected",
      "warmup": "completed"
    }
  ]
}
```

#### Connect Email Account

```bash
POST /lemlist/api/accounts
Content-Type: application/json

{
  "email": "outreach@company.com",
  "provider": "gmail",
  "smtpHost": "smtp.gmail.com",
  "smtpPort": 587
}
```

#### Delete Email Account

```bash
DELETE /lemlist/api/accounts/{account_id}
```

### Activities (Analytics)

#### Get Campaign Activities

```bash
GET /lemlist/api/activities/{campaign_id}
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/lemlist/api/activities/abc123def456')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "activities": [
    {
      "leadId": "lead_xyz789",
      "type": "sent",
      "timestamp": "2025-01-21T10:00:00.000Z",
      "subject": "Quick question about Acme Corp"
    },
    {
      "leadId": "lead_xyz789",
      "type": "opened",
      "timestamp": "2025-01-21T14:30:00.000Z"
    },
    {
      "leadId": "lead_xyz789",
      "type": "replied",
      "timestamp": "2025-01-22T09:15:00.000Z",
      "replyText": "Thanks for reaching out!"
    }
  ]
}
```

#### Get Campaign Stats

```bash
GET /lemlist/api/stats/{campaign_id}
```

### Templates

#### List Templates

```bash
GET /lemlist/api/templates
```

**Example:**

```bash
python <<'EOF'
import urllib.request, os, json
req = urllib.request.Request('https://gateway.maton.ai/lemlist/api/templates')
req.add_header('Authorization', f'Bearer {os.environ["MATON_API_KEY"]}')
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2))
EOF
```

**Response:**
```json
{
  "templates": [
    {
      "_id": "tmpl_aaa111",
      "name": "Initial Outreach",
      "subject": "Quick question about {companyName}",
      "body": "Hi {firstName}, ...",
      "usedInCampaigns": 3
    }
  ]
}
```

#### Create a Template

```bash
POST /lemlist/api/templates
Content-Type: application/json

{
  "name": "Follow Up Template",
  "subject": "Following up",
  "body": "Hi {firstName},\n\nJust checking in..."
}
```

#### Delete a Template

```bash
DELETE /lemlist/api/templates/{template_id}
```

### Team

#### List Team Members

```bash
GET /lemlist/api/team
```

## Code Examples

### Python

```python
import os
import requests

# List campaigns
response = requests.get(
    'https://gateway.maton.ai/lemlist/api/campaigns',
    headers={'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}'}
)

# Create lead
response = requests.post(
    'https://gateway.maton.ai/lemlist/api/leads',
    headers={
        'Authorization': f'Bearer {os.environ["MATON_API_KEY"]}',
        'Content-Type': 'application/json'
    },
    json={
        'email': 'prospect@company.com',
        'firstName': 'Alice',
        'campaignId': 'abc123def456'
    }
)
```

## Notes

- Lemlist supports multi-channel sequences (email + LinkedIn)
- A/B testing is available at the sequence step level with `abTest: true` and `abTestVariants`
- Personalization uses `{{variable}}` syntax (e.g., `{{firstName}}`, `{{companyName}}`)
- Activity types include: sent, opened, clicked, replied, bounced, unsubscribed, completed
- The warmup feature gradually increases email volume to protect sender reputation
- Daily limits are per email account, not per campaign
- Campaigns can be `active`, `paused`, or `draft`
- LinkedIn actions require connected LinkedIn accounts
- Bulk lead creation uses the `/leads/bulk` endpoint for efficiency

## Response Codes

| Status | Meaning |
|--------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No content |
| 400 | Bad request |
| 401 | Unauthorized |
| 404 | Not found |
| 429 | Rate limited |

## Resources

- [Lemlist API Documentation](https://docs.lemlist.com)
- [Lemlist API Reference](https://docs.lemlist.com/api-reference)
- [Maton Community](https://discord.com/invite/dBfFAcefs2)
