# CRM Digital FTE Factory

**GIAIC Hackathon 5 — Production AI Customer Success Agent**

---

## What is This?

CRM Digital FTE Factory is a production-grade AI-powered Customer Success agent built for **NexaFlow** — a fictional B2B SaaS workflow automation platform. The system acts as a full-time employee (FTE) for NexaFlow's support team, autonomously handling customer support tickets 24/7 across three channels.

---

## What is NexaFlow?

NexaFlow is a B2B SaaS workflow automation platform serving 3,000 business customers. It allows teams to build automations, connect tools like Slack, Jira, GitHub, and Google Calendar, and manage projects without writing code. Plans range from a free Starter tier to a $199/month Enterprise plan with API access and dedicated Customer Success Managers.

---

## 3-Channel Architecture

```
                        ┌─────────────────────────┐
                        │   NexaFlow AI Support    │
                        │      Agent (Core)        │
                        │  OpenAI Agents SDK +     │
                        │  FastAPI + Kafka          │
                        └────────┬────────┬────────┘
                                 │        │
            ┌────────────────────┼────────┼────────────────────┐
            │                   │        │                    │
            ▼                   ▼        ▼                    ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐
    │   Gmail       │  │  WhatsApp    │  │  Web Support │  │  Human   │
    │   Channel     │  │  (Twilio)    │  │  Form        │  │  Escalat │
    │  (Email)      │  │  Channel     │  │  (Next.js)   │  │  -ion    │
    └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘
```

Each channel ingests tickets into a **Kafka message queue**, which feeds the AI agent. The agent classifies, responds, and escalates tickets using:
- **Neon PostgreSQL + pgvector** for context storage and semantic search
- **OpenAI Agents SDK** for reasoning and tool use
- **Escalation rules** for routing to human agents

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Runtime | Python 3.12 + OpenAI Agents SDK |
| API Server | FastAPI |
| Database | Neon PostgreSQL + pgvector |
| Message Queue | Apache Kafka |
| Web Support Form | Next.js 15 (App Router) |
| Email Channel | Gmail API (OAuth 2.0) |
| WhatsApp Channel | Twilio WhatsApp Business API |
| Containerization | Docker + Docker Compose |
| Orchestration | Kubernetes (Minikube local / Oracle Cloud VM prod) |
| Spec Methodology | Spec-Kit Plus (Panaversity) |

---

## Project Structure

```
crm-digital-fte/
├── context/              # NexaFlow company & product context files
├── src/
│   ├── channels/         # Gmail, WhatsApp, Web Form channel connectors
│   ├── agent/            # Core AI agent (OpenAI Agents SDK)
│   └── web-form/         # Next.js 15 support form frontend
├── tests/                # Unit and integration tests
├── specs/                # Spec-Kit Plus specification files
├── production/
│   ├── agent/            # Dockerized agent service
│   ├── channels/         # Channel services
│   ├── workers/          # Kafka consumer workers
│   ├── api/              # FastAPI service
│   ├── database/         # Migrations and schemas
│   └── k8s/              # Kubernetes manifests
└── .claude/
    └── skills/           # Claude Code custom skills
```

---

## Setup

See deployment guide (Phase 5 — Implementation).

---

## Hackathon Context

This project is built for **GIAIC (Governor Initiative for AI and Computing) Hackathon 5**, demonstrating a production-ready multi-channel AI customer success system using modern cloud-native tooling and the OpenAI Agents SDK.
