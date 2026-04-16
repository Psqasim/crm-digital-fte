# Gmail Channel Setup Guide

> Tested and working as of April 2026 (OAuth2 user credentials + Pub/Sub push).

---

## Prerequisites

- Google account to use as the support inbox
- Access to Google Cloud Console (free tier is enough)

---

## Step 1: Create Google Cloud Project

1. Go to https://console.cloud.google.com
2. Click the project dropdown (top left) → **New Project**
3. Name: `crm-digital-fte` → **Create**
4. Note your **Project ID** (e.g. `crm-digital-fte-493507`)

---

## Step 2: Enable APIs

1. Go to **APIs & Services → Library**
2. Search and enable:
   - **Gmail API**
   - **Cloud Pub/Sub API**

---

## Step 3: Create Pub/Sub Topic

1. Go to **Pub/Sub → Topics → Create Topic**
2. Topic ID: `gmail-notifications` → **Create**
3. Click the topic → **Permissions** tab → **Grant Access**
4. New principal: `gmail-api-push@system.gserviceaccount.com`
5. Role: **Pub/Sub Publisher** (search for it in the role dropdown)
6. **Save**

> This allows Gmail to push notifications to your topic.

---

## Step 4: Create Push Subscription

1. Go to **Pub/Sub → Subscriptions → Create Subscription**
2. Fill in:
   - Subscription ID: `gmail-push-sub`
   - Topic: `gmail-notifications`
   - Delivery type: **Push**
   - Endpoint URL: `https://psqasim-crm-digital-fte-api.hf.space/webhooks/gmail`
3. Leave all other settings as default → **Create**

---

## Step 5: Create OAuth2 Credentials

1. Go to **APIs & Services → OAuth consent screen**
   - User type: **External** → **Create**
   - App name: `NexaFlow CRM`, support email → **Save**
   - Skip scopes → **Save**
   - Add your Gmail address as a **Test user** → **Save**

2. Go to **APIs & Services → Credentials**
   - **Create Credentials → OAuth client ID**
   - Application type: **Desktop app**
   - Name: `gmail-crm-client` → **Create**
   - **Download JSON** → save file

---

## Step 6: Run OAuth Flow (one-time, on your local machine)

```bash
source .venv/bin/activate

# Copy credentials file to project folder
cp /path/to/downloaded-client-secret.json ./gmail-client-secret.json

# Run OAuth flow
python gmail_oauth.py
```

> This opens a browser → log in with your support Gmail → click Allow.
> Creates `gmail-authorized.json` with your tokens.

```bash
cat gmail-authorized.json   # copy the full output
```

---

## Step 7: Add Environment Variables to HF Spaces

Go to your HF Space → **Settings → Secrets**, add:

| Secret Name | Value |
|-------------|-------|
| `GOOGLE_CLOUD_PROJECT_ID` | your project ID from Step 1 |
| `GMAIL_USER_EMAIL` | the Gmail address you authenticated with |
| `GMAIL_CREDENTIALS_JSON_CONTENT` | paste the full JSON from `gmail-authorized.json` |

> **Note:** Do not use the client secret JSON — use `gmail-authorized.json` (the one with the access and refresh tokens).

---

## Step 8: Deploy & Verify

1. Push code to HF Spaces: `git push huggingface main`
2. Wait ~1 min for rebuild → check logs for:
   ```
   [gmail_handler] credentials loaded OK
   [gmail_handler] watch registered, historyId=XXXXXXX
   ```
3. If you see those — Gmail is connected ✅

---

## Step 9: Test

1. Send an email to your support Gmail address
2. Wait ~30 seconds → AI reply arrives in sender's inbox
3. Check admin dashboard → ticket with `channel=email` created

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `credentials loaded OK` but no `watch registered` | Wrong API call | Already fixed in latest code |
| `403 User not authorized` on watch | gmail-api-push service account missing Publisher role on topic | Repeat Step 3 |
| `400 Recipient address required` on send_reply | Processing own sent email as new message | Fixed — non-INBOX messages skipped |
| Duplicate AI responses in ticket | Two Pub/Sub notifications (inbox + sent) | Fixed — labelIds=INBOX filter applied |
| `access_denied` in browser during OAuth | Gmail not added as test user | Add to OAuth consent screen test users |
| Token expired | Access token has 1hr expiry | google-auth auto-refreshes using refresh_token |

---

## Token Renewal

The Gmail watch expires after **7 days**. The watch is re-registered automatically every time HF Spaces restarts (it's called in the lifespan startup). If you need to force renewal, do a factory reboot of the HF Space.

---

## How It Works (actual flow)

```
Customer sends email to support Gmail
        ↓
Gmail detects new INBOX message
        ↓
Gmail → Pub/Sub topic (gmail-notifications)
        ↓
Pub/Sub → POST /webhooks/gmail
        ↓
Decode historyId → call history.list API
        ↓
For each INBOX message: DB dedup check (claim message_id)
        ↓
Create customer + conversation + ticket in Neon DB
        ↓
AI Agent (OpenAI Agents SDK, gpt-4o-mini)
  → searches knowledge base (pgvector)
  → generates reply or escalates
        ↓
send_reply() → Gmail API → threaded reply to customer
```
