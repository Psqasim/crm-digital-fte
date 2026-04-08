# CRM Digital FTE Factory

**GIAIC Hackathon 5 — Production AI Customer Success Agent**

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)
![Kafka](https://img.shields.io/badge/Kafka-Confluent_Cloud-red?logo=apachekafka)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-green?logo=postgresql)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110-teal?logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## What is This?

**CRM Digital FTE Factory** is a production-grade AI Customer Success agent for **NexaFlow** — a B2B SaaS workflow automation platform. The AI acts as a full-time employee (FTE), autonomously handling ~800 support tickets/week across **3 channels** with a 75% AI resolution rate — no human needed for most tickets.

---

## Architecture

```
┌─────────────┐   ┌──────────────┐   ┌──────────────────┐
│   Gmail      │   │  WhatsApp    │   │  Next.js Web Form │
│  (Email)     │   │  (Twilio)    │   │  (3-step form)   │
└──────┬───────┘   └──────┬───────┘   └────────┬─────────┘
       │                  │                    │
       └──────────────────┼────────────────────┘
                          │
                   ┌──────▼──────┐
                   │    Kafka     │  ← Confluent Cloud
                   │  (Queue)     │
                   └──────┬───────┘
                          │
                   ┌──────▼──────────────────────┐
                   │   FastAPI Orchestration      │
                   │   + OpenAI Agents SDK        │
                   │   + 7 tools (KB, escalation) │
                   └──────┬───────────────────────┘
                          │
              ┌───────────┼───────────┐
              │                       │
     ┌────────▼──────┐   ┌────────────▼────────┐
     │  Neon          │   │  Human Escalation    │
     │  PostgreSQL    │   │  (Mon-Fri 9-6 PKT)   │
     │  + pgvector    │   └─────────────────────┘
     └───────────────┘
```

---

## Features

- **3-channel support:** Gmail (email), WhatsApp (Twilio), Next.js web form
- **AI agent with 7 tools:** knowledge base search, ticket creation, customer lookup, escalation, sentiment analysis, SLA check, history retrieval
- **Real-time status:** ticket status polling via web form frontend
- **Kafka streaming:** decoupled, scalable message queue (Confluent Cloud)
- **pgvector semantic search:** OpenAI embeddings for knowledge base queries
- **Structured logging:** JSON logs per request to stderr
- **Monitoring:** `/health`, `/metrics/summary`, `/metrics/channels` endpoints
- **Containerized:** Docker + Docker Compose + Kubernetes manifests

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Runtime | Python 3.12 + OpenAI Agents SDK |
| API Server | FastAPI |
| Database | Neon PostgreSQL + pgvector |
| Message Queue | Apache Kafka (Confluent Cloud) |
| Frontend | Next.js 15 App Router |
| Email Channel | Gmail API (OAuth 2.0) |
| WhatsApp Channel | Twilio WhatsApp Business API |
| Containers | Docker + Docker Compose |
| Orchestration | Kubernetes (Minikube / Oracle Cloud VM) |

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Psqasim/crm-digital-fte.git && cd crm-digital-fte

# 2. Python setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r production/requirements.txt

# 3. Environment
cp .env.example .env   # fill in DATABASE_URL + OPENAI_API_KEY at minimum

# 4. Start FastAPI
uvicorn production.api.main:app --reload --port 8000

# 5. Verify
curl http://localhost:8000/health
```

Full setup instructions → [docs/setup/setup.md](docs/setup/setup.md)

---

## Project Structure

```
crm-digital-fte/
├── context/              # NexaFlow company + product docs
├── docs/                 # Documentation
│   ├── README.md         # Docs index
│   ├── setup/            # Setup guide
│   ├── env/              # Environment variables
│   ├── api/              # API reference
│   ├── deploy/           # Deployment guide
│   └── web-form/         # Web form integration
├── production/
│   ├── agent/            # AI agent (OpenAI Agents SDK)
│   ├── api/              # FastAPI app + routes
│   ├── channels/         # Gmail, WhatsApp, Web Form handlers
│   ├── database/         # Schema, queries, seed script
│   ├── kafka/            # Kafka consumer
│   ├── monitoring/       # Metrics + alerts
│   ├── tests/            # Production + E2E tests
│   ├── workers/          # Background workers
│   ├── k8s/              # Kubernetes manifests
│   └── docker-compose.yml
├── src/
│   ├── agent/            # Core agent models + prototype
│   └── web-form/         # Next.js 15 frontend
├── specs/                # Spec-Kit Plus specs per phase
├── tests/                # Unit tests
└── LICENSE
```

---

## Screenshots

> _Add screenshots here — web form, ticket status page, agent response._

---

## Documentation

Full docs in [`docs/`](docs/README.md):

| Guide | Link |
|-------|------|
| Setup | [docs/setup/setup.md](docs/setup/setup.md) |
| Env Variables | [docs/env/env.md](docs/env/env.md) |
| API Reference | [docs/api/api.md](docs/api/api.md) |
| Deployment | [docs/deploy/deployment.md](docs/deploy/deployment.md) |
| Web Form | [docs/web-form/README.md](docs/web-form/README.md) |

---

## Tests

```bash
# 165+ unit + integration tests
pytest tests/ production/tests/ -v --ignore=production/tests/test_e2e.py

# E2E tests (requires running server + DB)
TEST_DATABASE_URL="..." pytest production/tests/test_e2e.py -v
```

---

## License

[MIT](LICENSE) — Muhammad Qasim, 2026
