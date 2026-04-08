# Channel Response Templates

Channel-specific response templates for the NexaFlow Customer Success FTE.
The AI agent selects the appropriate template based on the incoming channel.

---

## Email Channel (`channel = "email"`)

**Tone:** Professional, full paragraphs, formal salutation  
**Max length:** ~500 words  
**Format:** Greeting → body → clear next steps → signature

### Standard Resolution
```
Dear {customer_name},

Thank you for reaching out to NexaFlow Support.

{resolution_body}

If you have any further questions, please don't hesitate to reply to this email.

Best regards,
NexaFlow Support Team
support@nexaflow.io
https://nexaflow.com
```

### Escalation
```
Dear {customer_name},

Thank you for your patience. I've reviewed your request and escalated it
to our specialist team for priority handling.

Ticket Reference: {ticket_id}
Expected response time: 2–4 business hours (Mon–Fri, 9am–6pm PKT)

You will receive a follow-up at this email address shortly.

Best regards,
NexaFlow Support Team
support@nexaflow.io
```

### Billing Query
```
Dear {customer_name},

Thank you for contacting NexaFlow regarding your billing inquiry.

{billing_details}

For urgent billing changes or refund requests, our specialist team
handles these within 1 business day.

Best regards,
NexaFlow Support Team
billing@nexaflow.io
```

---

## WhatsApp Channel (`channel = "whatsapp"`)

**Tone:** Conversational, friendly, concise  
**Max length:** ~160 characters preferred; 3 sentences max  
**Format:** First-name greeting → direct answer → single CTA  
**Emoji:** Allowed, 1–2 max

### Standard Resolution
```
Hi {first_name}! 👋 {short_resolution}. Let me know if you need anything else!
```

### Escalation
```
Hi {first_name}! I've passed this to our team — Ticket {ticket_id}.
Expect a reply within 2–4 hrs (business hours PKT) 🙏
```

### Billing Query
```
Hi {first_name}! For billing changes, our team handles this directly.
Ticket {ticket_id} raised — response within 1 business day.
```

### Non-English / Urdu
```
آپ کا شکریہ۔ ہم نے آپ کی درخواست وصول کر لی ہے۔
ٹکٹ نمبر: {ticket_id} | جواب: 2-4 گھنٹے (کاروباری اوقات)
```

---

## Web Form Channel (`channel = "web_form"`)

**Tone:** Semi-formal, structured, action-oriented  
**Max length:** ~300 words  
**Format:** Greeting → brief ack → numbered steps → ticket reference

### Standard Resolution
```
Hello {customer_name},

Thanks for reaching out through our support form.

{resolution_body}

Steps to resolve:
1. {step_1}
2. {step_2}
3. {step_3}

Your ticket reference is **{ticket_id}**. You can track its status at:
nexaflow.com/ticket/{ticket_id}

— NexaFlow Support
```

### Escalation
```
Hello {customer_name},

I've escalated your request to our specialist team.

Ticket: **{ticket_id}**
Expected response: 2–4 hours (business hours, Mon–Fri 9am–6pm PKT)

You can track status at nexaflow.com/ticket/{ticket_id}

— NexaFlow Support
```

---

## Escalation Template (All Channels)

Used whenever `escalated = true` regardless of channel — content adapted to channel format above.

**Core message:**
```
I've escalated your request to our specialist team.
Ticket #{ticket_id} | Expected response: 2–4 hours (business hours PKT)
```

---

## Sentiment-Based Tone Adjustments

| Sentiment | Adjustment |
|-----------|-----------|
| `positive` | Mirror enthusiasm; acknowledge the positive framing |
| `neutral` | Default templates above |
| `negative` | Lead with empathy: "I understand this has been frustrating..." |
| `escalation` | Acknowledge urgency; do not dismiss; escalate immediately |
