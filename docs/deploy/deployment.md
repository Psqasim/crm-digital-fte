# Deployment Guide

How to deploy CRM Digital FTE Factory to production.

---

## Frontend — Vercel (Next.js Web Form)

### Deploy

1. Push your repo to GitHub
2. Go to https://vercel.com → **New Project** → import your repo
3. Set **Root Directory** to `src/web-form` (or wherever your Next.js app is)
4. Add environment variables (see below)
5. Click **Deploy**

### Environment Variables for Vercel

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_API_URL` | Your Hugging Face Spaces URL (e.g. `https://psqasim-nexaflow-api.hf.space`) |

### Custom Domain (optional)

Vercel → Project → Settings → Domains → Add domain

---

## Backend — Hugging Face Spaces (FastAPI)

### Deploy

1. Go to https://huggingface.co/spaces → **Create new Space**
2. Choose **Docker** as SDK
3. Name it e.g. `nexaflow-api`
4. Add a `Dockerfile` at the repo root that serves the FastAPI app:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY production/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 7860
CMD ["uvicorn", "production.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

5. Push to the Space's git remote

### Environment Variables for Hugging Face Spaces

Set these in **Settings → Repository secrets**:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenAI API key |
| `KAFKA_BOOTSTRAP_SERVERS` | Confluent Cloud bootstrap server |
| `KAFKA_API_KEY` | Confluent Cloud API key |
| `KAFKA_API_SECRET` | Confluent Cloud API secret |
| `KAFKA_TOPIC` | `support-tickets` |
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `TWILIO_WHATSAPP_NUMBER` | `whatsapp:+14155238886` |

### Notes

- Hugging Face Spaces free tier sleeps after inactivity — use a paid Space or ping `/health` periodically
- The public URL will be `https://<username>-<space-name>.hf.space`

---

## Kubernetes (Oracle Cloud VM / Minikube)

For full production Kubernetes deployment, manifests are in `production/k8s/`:

```bash
# Apply all manifests
kubectl apply -f production/k8s/

# Check pod status
kubectl get pods -n nexaflow

# View logs
kubectl logs -n nexaflow deployment/nexaflow-api
```

See `production/k8s/` for individual manifest files (deployments, services, configmaps).
