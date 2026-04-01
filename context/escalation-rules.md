# NexaFlow — Escalation Rules

## Overview
The AI support agent must automatically escalate a ticket to a human support agent when any of the following conditions are met. Escalation means: flagging the ticket in the queue, notifying the on-call human agent via Slack (#support-escalations), and sending the customer an acknowledgment message with a human response ETA.

---

## Escalation Triggers

### 1. Sentiment Score Below Threshold
- **Condition:** Customer sentiment score < 0.3 (on a 0.0–1.0 scale)
- **Rationale:** Highly negative/frustrated customers require empathy and judgment that AI handles poorly at extremes
- **Action:** Escalate immediately; do not attempt AI resolution; send empathy acknowledgment

### 2. Refund Requested
- **Condition:** Customer explicitly requests a refund (any amount, any reason)
- **Rationale:** Refund decisions require human authorization and policy interpretation
- **Action:** Acknowledge receipt, inform customer a human will review within [plan SLA], escalate to billing team channel (#billing-escalations)

### 3. Legal or Compliance Question
- **Condition:** Message contains references to: GDPR, CCPA, data breach, legal action, lawsuit, subpoena, regulatory inquiry, data deletion rights, data processing agreement (DPA)
- **Rationale:** Legal risk; requires review by legal/compliance team before any response
- **Action:** Escalate immediately; do not provide any information; acknowledge only that the query is being reviewed

### 4. Pricing Negotiation Attempt
- **Condition:** Customer asks for a discount, requests custom pricing, asks to match a competitor's price, or inquires about deals not listed on the website
- **Rationale:** Pricing decisions require sales team involvement; AI must not commit to non-standard pricing
- **Action:** Acknowledge interest, escalate to sales/CSM team; do not reveal internal pricing strategies

### 5. Three or More Unanswered Follow-Ups
- **Condition:** Same customer (identified by email) has sent 3 or more messages without a satisfactory resolution (tracked via ticket thread)
- **Rationale:** Repeated follow-ups signal AI resolution failure or customer frustration
- **Action:** Escalate to human agent; review prior AI responses before responding

### 6. Explicit Human Agent Request
- **Condition:** Customer explicitly asks to speak with a human, a person, a real agent, or a manager
- **Rationale:** Customer autonomy; forcing AI on customers who want humans increases churn
- **Action:** Acknowledge immediately, inform of human availability hours (Mon–Fri 9am–6pm PKT), escalate

### 7. Data Breach Concern
- **Condition:** Customer reports unauthorized access to their account, suspects data theft, or reports seeing another customer's data
- **Rationale:** Security incidents require immediate triage by security team
- **Action:** Escalate to #security-incidents immediately; do not ask for more details via chat; acknowledge urgency

### 8. Enterprise Plan SLA Breach Risk
- **Condition:** Enterprise plan customer ticket has been open for 3+ hours without resolution (SLA is 4 hours)
- **Rationale:** Enterprise SLA breach results in contractual compensation liability
- **Action:** Page the on-call CSM; mark ticket as P1; send proactive update to customer

---

## Escalation Response Templates

### Immediate Escalation (Sentiment/Security/Legal)
> "Thank you for reaching out, [FirstName]. I've escalated your message to our specialist team right away. You'll hear from a human agent shortly. We take this seriously and appreciate your patience."

### Scheduled Escalation (Refund/Pricing)
> "Hi [FirstName], I've flagged your request for our billing team to review. Based on your plan ([PlanName]), you can expect a response within [SLA]. We'll be in touch soon."

### Human Request Acknowledgment
> "Absolutely, [FirstName] — I've passed this to a human agent. Our team is available Monday–Friday, 9 AM–6 PM PKT. If it's outside these hours, they'll follow up first thing next business day."

---

## Non-Escalation Guidance
The agent should NOT escalate for:
- Simple how-to questions (even if the customer is frustrated in tone but not below 0.3 sentiment)
- Password reset requests
- Plan feature inquiries
- Standard bug reports that have known fixes
- Integration setup help

---

## Escalation Logging
Every escalation must be logged to the database with:
- `ticket_id`, `customer_email`, `escalation_reason` (enum: sentiment/refund/legal/pricing/followup/human_request/security/sla_breach)
- `escalated_at` (UTC timestamp)
- `ai_conversation_summary` (last 3 AI messages)
- `assigned_to` (human agent username, populated after assignment)
