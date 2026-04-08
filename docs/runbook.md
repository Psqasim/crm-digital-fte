# NexaFlow FTE — Incident Runbook

Quick reference for on-call engineers responding to production incidents.

---

## Service Health Check

```bash
curl https://your-api-url/health
# Expected: {"status":"healthy","database":"connected","timestamp":"...PKT"}
```

---

## Common Incidents

### Agent stuck — ticket stays "open" > 5 minutes

**Symptoms:** Tickets in DB have `status = open` long after creation, Kafka consumer logs silent.

```bash
# 1. Check if consumer is running
ps aux | grep consumer

# 2. Restart consumer
python3 -m production.kafka.consumer

# 3. Force-process all pending tickets
curl -X POST http://localhost:8000/agent/process-pending
```

---

### Database connection failed

**Symptoms:** `/health` returns `"database":"disconnected"` or 500 errors on any endpoint.

```bash
# 1. Check Neon dashboard at neon.tech — look for outage notices
# 2. Verify env var is set
echo $DATABASE_URL

# 3. Test connection directly
psql $DATABASE_URL -c "SELECT 1"

# 4. If pooler endpoint is down, switch to direct connection URL in .env
#    (neon.tech → Connect → toggle "Pooler" off)
```

---

### Kafka consumer not receiving messages

**Symptoms:** Tickets created but never processed; consumer logs show no activity.

```bash
# 1. Check Confluent Cloud cluster status at confluent.io
# 2. Verify credentials
echo $KAFKA_BOOTSTRAP_SERVERS
echo $KAFKA_API_KEY

# 3. Recreate topic if missing
python3 production/kafka/setup_topics.py

# 4. Check consumer group lag in Confluent Cloud → Consumer Groups
```

---

### High escalation rate (> 25%)

**Symptoms:** `/metrics/summary` shows `escalation_rate > 0.25`.

```bash
# 1. Check current metrics
curl http://localhost:8000/metrics/summary

# 2. Check per-channel breakdown
curl http://localhost:8000/metrics/channels

# 3. Verify knowledge base has content
psql $DATABASE_URL -c "SELECT COUNT(*) FROM knowledge_base;"
# If 0 → re-seed:
DATABASE_URL=... OPENAI_API_KEY=... python3 -m production.database.seed_knowledge_base

# 4. Review recent escalated tickets for patterns
psql $DATABASE_URL -c "SELECT message FROM tickets WHERE status='escalated' ORDER BY created_at DESC LIMIT 10;"
```

---

### WhatsApp webhook not receiving messages

**Symptoms:** No incoming WhatsApp tickets; Twilio console shows failed deliveries.

```bash
# 1. Verify webhook URL in Twilio console points to your /webhooks/whatsapp endpoint
# 2. Check TWILIO_AUTH_TOKEN is current (tokens can be regenerated)
# 3. Test webhook manually:
curl -X POST http://localhost:8000/webhooks/whatsapp \
  -d "From=whatsapp:+1234567890&Body=Test&MessageSid=SM123&AccountSid=$TWILIO_ACCOUNT_SID"
```

---

## Monitoring URLs

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Service + DB status |
| `GET /metrics/summary` | Total tickets, resolution rate, escalation rate |
| `GET /metrics/channels` | Per-channel ticket breakdown |
| `GET /docs` | FastAPI Swagger UI |
