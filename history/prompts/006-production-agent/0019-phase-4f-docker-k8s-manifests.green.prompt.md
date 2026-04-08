---
id: "0019"
title: Phase 4F Docker K8s Manifests
stage: green
date: 2026-04-08
surface: agent
model: claude-sonnet-4-6
feature: 006-production-agent
branch: 009-docker-k8s
user: Muhammad Qasim
command: /sp.implement
labels: ["docker", "kubernetes", "phase-4f", "dockerfile", "k8s", "devops"]
links:
  spec: null
  ticket: null
  adr: null
  pr: https://github.com/Psqasim/crm-digital-fte/pull/7
files:
  - production/Dockerfile
  - production/docker-compose.yml
  - production/k8s/namespace.yaml
  - production/k8s/secret.yaml
  - production/k8s/configmap.yaml
  - production/k8s/api-deployment.yaml
  - production/k8s/api-service.yaml
  - production/k8s/worker-deployment.yaml
  - production/k8s/web-deployment.yaml
  - production/k8s/web-service.yaml
  - production/k8s/hpa.yaml
  - src/web-form/Dockerfile
  - src/web-form/next.config.ts
  - .dockerignore
  - .gitignore
tests:
  - kubectl apply --dry-run=client -f production/k8s/ (9 manifests, all PASS)
  - docker compose build (production-api, production-worker, production-web — all built successfully)
---

## Prompt

```text
## CONTEXT
Project: CRM Digital FTE Factory — GIAIC Hackathon 5
Location: /home/ps_qasim/projects/crm-digital-fte
Phase: 4F — Docker + Kubernetes Manifests

All services working locally:
- FastAPI on port 8000
- Next.js on port 3000
- Kafka consumer (production/kafka/consumer.py)
- Neon PostgreSQL (external, no container needed)
- Confluent Cloud Kafka (external, no container needed)

Read before starting:
- .claude/skills/kafka-event-driven/ (K8s patterns)
- production/Dockerfile (placeholder — implement now)
- production/docker-compose.yml (placeholder — implement now)

## MANDATORY — USE CONTEXT7 BEFORE ANY CODE
Search:
1. "fastapi dockerfile python multi-stage build"
2. "next.js dockerfile standalone output"
3. "kubernetes deployment service configmap secret"

## TASK
Create branch: 009-docker-k8s from main

### Step 1: production/Dockerfile (FastAPI) — multi-stage build
### Step 2: src/web-form/Dockerfile (Next.js standalone)
### Step 3: production/docker-compose.yml (api + worker + web)
### Step 4: production/k8s/ — namespace, secret, configmap, api-deployment,
            api-service, worker-deployment, web-deployment, web-service, hpa
### Step 5: kubectl dry-run validation
### Step 6: docker compose build test
### Step 7: Commit, push, PR, merge
```

## Response snapshot

- Context7 queried for FastAPI Docker and Next.js standalone docs before any code
- Created branch 009-docker-k8s from main
- Implemented production/Dockerfile: python:3.12-slim multi-stage (builder installs deps, runtime copies site-packages + app)
- Implemented src/web-form/Dockerfile: node:20-alpine multi-stage with standalone output
- Updated src/web-form/next.config.ts: added `output: 'standalone'`
- Implemented production/docker-compose.yml: api (healthcheck), worker (depends_on api), web — all with env_file/restart
- Created 9 K8s manifests in production/k8s/: namespace, secret (placeholder values), configmap, api-deployment (2 replicas, probes, resources), api-service (ClusterIP:8000), worker-deployment (1 replica), web-deployment (2 replicas), web-service (LoadBalancer:80→3000), hpa (autoscaling/v2, 2-5 replicas, 70% CPU)
- Created .dockerignore excluding .env, pycache, node_modules, .git
- Fixed .gitignore to allow .dockerignore to be tracked
- kubectl dry-run: all 9 manifests PASS
- docker compose build: all 3 images built successfully (production-api, production-worker, production-web)
- Committed 15 files, pushed branch, created PR #7, merged to main

## Outcome

- ✅ Impact: Full containerization + K8s orchestration ready for Phase 4G (Monitoring)
- 🧪 Tests: kubectl dry-run (9/9 PASS), docker compose build (3/3 images built)
- 📁 Files: 15 files changed (14 new, 1 modified next.config.ts)
- 🔁 Next prompts: Phase 4G — Prometheus/Grafana monitoring, alerting
- 🧠 Reflection: docker-compose.yml needed `context: ..` (repo root) since it lives in production/ subdir; .gitignore had .dockerignore excluded — fixed to allow tracking

## Evaluation notes (flywheel)

- Failure modes observed: .gitignore was blocking .dockerignore from being staged; fixed by commenting out that entry
- Graders run and results (PASS/FAIL): kubectl dry-run PASS, docker compose build PASS
- Prompt variant (if applicable): none
- Next experiment (smallest change to try): Add health endpoint to Next.js web service for K8s probes
