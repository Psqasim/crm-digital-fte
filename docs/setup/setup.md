# Setup Guide

Step-by-step local development setup for CRM Digital FTE Factory.

## Prerequisites

- Python 3.12+
- Node.js 18+
- Git

---

## Step 1 — Clone the Repo

```bash
git clone https://github.com/Psqasim/crm-digital-fte.git
cd crm-digital-fte
```

---

## Step 2 — Python Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

pip install -r requirements.txt
pip install -r production/requirements.txt
```

---

## Step 3 — Node.js Setup (Web Form)

```bash
cd src/web-form
npm install
cd ../..
```

---

## Step 4 — Required Accounts

| Service | Purpose | URL |
|---------|---------|-----|
| Neon | PostgreSQL database | https://neon.tech |
| OpenAI | AI agent + embeddings | https://platform.openai.com |
| Confluent Cloud | Apache Kafka | https://confluent.io |
| Twilio | WhatsApp channel | https://twilio.com |

See [env/env.md](../env/env.md) for how to get each credential.

---

## Step 5 — Environment Variables

```bash
cp .env.example .env
# Edit .env and fill in your values
```

---

## Step 6 — Run Database Migrations

```bash
psql "your_neon_url" -f production/database/schema.sql
```

Or with Python:

```bash
source .venv/bin/activate
python3 -c "
import asyncio, asyncpg
from pathlib import Path

async def run():
    sql = Path('production/database/schema.sql').read_text()
    conn = await asyncpg.connect('your_neon_url')
    await conn.execute(sql)
    await conn.close()
    print('Done')

asyncio.run(run())
"
```

---

## Step 7 — Seed Knowledge Base

Chunks `context/product-docs.md`, generates OpenAI embeddings, and stores them in Neon:

```bash
source .venv/bin/activate
DATABASE_URL="..." OPENAI_API_KEY="..." python3 -m production.database.seed_knowledge_base
```

Expected output:
```
11 chunks identified.
Embedded batch 1 (11 chunks)...
Seeded 11 chunks into knowledge_base
```

---

## Step 8 — Start All Services

**Terminal 1 — FastAPI backend:**
```bash
source .venv/bin/activate
uvicorn production.api.main:app --reload --port 8000
```

**Terminal 2 — Kafka consumer worker:**
```bash
source .venv/bin/activate
python3 -m production.workers.kafka_consumer
```

**Terminal 3 — Next.js web form:**
```bash
cd src/web-form
npm run dev
```

---

## Verify

```bash
# Health check
curl http://localhost:8000/health
# → {"status":"healthy","database":"connected","timestamp":"...PKT"}

# Submit a test ticket
curl -X POST http://localhost:8000/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "How do I set up automation rules?",
    "category": "general",
    "priority": "medium",
    "message": "I need help setting up automation rules in my NexaFlow workspace."
  }'
```

---

## Tests

```bash
# All tests (excluding E2E)
pytest tests/ production/tests/ -v --ignore=production/tests/test_e2e.py

# E2E tests (requires running server)
TEST_DATABASE_URL="..." pytest production/tests/test_e2e.py -v
```

---

## Docker (Alternative)

```bash
docker-compose -f production/docker-compose.yml up --build
```

---

## Running All Services

Open three separate terminals:

```bash
# Terminal 1 — FastAPI backend
cd /home/ps_qasim/projects/crm-digital-fte
source .venv/bin/activate
uvicorn production.api.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Kafka consumer worker
cd /home/ps_qasim/projects/crm-digital-fte
source .venv/bin/activate
python3 -m production.kafka.consumer

# Terminal 3 — Next.js frontend
cd /home/ps_qasim/projects/crm-digital-fte/src/web-form
npm run dev
# Opens at http://localhost:3000
```

---

## Running Tests

```bash
# Full test suite
cd /home/ps_qasim/projects/crm-digital-fte
source .venv/bin/activate
pytest tests/ production/tests/ -v --tb=short

# Expected result: 166 passed, 19 skipped, 0 failed
# Skipped = E2E tests that need TEST_DATABASE_URL (CI-safe)

# Run E2E tests with real DB
TEST_DATABASE_URL=$DATABASE_URL pytest production/tests/test_e2e.py -v

# Run a specific test file
pytest production/tests/test_agent_tools.py -v
pytest tests/test_cross_channel.py -v
```

---

## Manual E2E Test Flow

1. Start all 3 terminals (see above)
2. Open `http://localhost:3000`
3. Click **Get Support**
4. Fill form: any name/email, subject "test", category General, priority Low, message `"How do I set up automation rules in NexaFlow?"`
5. Submit → confetti fires → redirects to `/ticket/TKT-XXXXXXXX`
6. Watch status: **Open** → _(Kafka consumer picks up)_ → **Resolved** (within ~60s)
7. Check dashboard: `http://localhost:3000/dashboard`
8. Verify metrics updated

**Direct API test:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/metrics/summary
curl -X POST http://localhost:8000/agent/process-pending
```
