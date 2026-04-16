# WhatsApp Channel Setup Guide

> Tested and working as of April 2026 (Twilio Sandbox).

---

## Prerequisites

- Twilio account (free at console.twilio.com)
- A phone number that has WhatsApp installed

---

## Step 1: Create Twilio Account

1. Go to https://console.twilio.com → sign up free
2. Verify your phone number during signup
3. Copy your **Account SID** and **Auth Token** from the dashboard homepage

---

## Step 2: Enable WhatsApp Sandbox

1. Twilio Console → **Messaging → Try it out → Send a WhatsApp message**
2. Note the sandbox join word shown (e.g. "join trouble-matter")
3. From your WhatsApp, send that join message to **+1 415 523 8886**
4. You'll receive a confirmation: "You are all set!"

> **Important:** Every test phone number must join the sandbox once before it can send/receive messages.

---

## Step 3: Configure Webhook

1. Twilio Console → **Messaging → Try it out → Send a WhatsApp message**
2. Scroll to **Sandbox Settings**
3. Set **"When a message comes in"**:
   - URL: `https://psqasim-crm-digital-fte-api.hf.space/webhooks/whatsapp`
   - Method: `POST`
4. Leave **Status callback URL** empty
5. Click **Save**

---

## Step 4: Add Environment Variables

Add to `.env` locally and to HF Spaces secrets:

```env
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
ADMIN_WHATSAPP_NUMBER=+92XXXXXXXXXX
```

> `TWILIO_WHATSAPP_NUMBER` needs the `whatsapp:` prefix.
> `ADMIN_WHATSAPP_NUMBER` is just the phone number — no prefix. This number receives escalation alerts.
> The admin number must also join the sandbox to receive messages.

---

## Step 5: Test

1. Send any WhatsApp message to **+1 415 523 8886**
2. Wait ~20 seconds → AI reply arrives on your phone
3. Check admin dashboard → ticket created with `channel=whatsapp`

### Test escalation
Send: *"I want a full refund immediately and cancel my account"*
- AI escalates → you get a 🚨 alert on your ADMIN_WHATSAPP_NUMBER

### Test human reply
1. Open the ticket in the dashboard
2. Type a reply in the Agent Reply box → Send
3. Your reply arrives on the customer's WhatsApp

---

## Sandbox Limits

| Limit | Value |
|-------|-------|
| Outbound messages per day | 5 |
| Session window | 24 hours |
| Numbers that must join | All test numbers |

> These limits are **sandbox only**. In production with a real approved WhatsApp Business number, there are no joining requirements and the daily limit is removed.

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `400 The 'To' number is not valid` | 24hr session window expired | Re-send "join trouble-matter" to re-open window |
| `429 exceeded 5 daily messages` | Sandbox daily limit hit | Wait until next day |
| No reply received | Webhook URL wrong | Check Twilio sandbox settings |
| Double replies | Old in-memory dedup | Fixed — now uses DB-level dedup |

---

## How It Works (actual flow)

```
Customer WhatsApp message
        ↓
Twilio → POST /webhooks/whatsapp (HMAC-SHA1 validated)
        ↓
Webhook returns 200 immediately (prevents Twilio retry)
        ↓
Background: DB dedup check (claim MessageSid)
        ↓
Create customer + conversation + ticket in Neon DB
        ↓
AI Agent (OpenAI Agents SDK, gpt-4o-mini)
  → searches knowledge base (pgvector)
  → generates reply or escalates
        ↓
send_reply() → Twilio API → customer's WhatsApp
        ↓
If escalated → 🚨 alert to ADMIN_WHATSAPP_NUMBER
```
