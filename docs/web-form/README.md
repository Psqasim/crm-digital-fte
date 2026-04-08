# Web Form Integration Guide

Next.js 15 support form for CRM Digital FTE Factory.

---

## Overview

The web form is a Next.js 15 App Router application that:
1. Presents a 4-page support form (contact info → issue details → submission → status)
2. POSTs to the FastAPI backend at `POST /support/submit`
3. Polls `GET /support/ticket/{id}` for real-time status updates

---

## Environment Variables

Create `src/web-form/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

For production, set `NEXT_PUBLIC_API_URL` to your deployed API URL (e.g. Hugging Face Spaces URL).

---

## Running Locally

```bash
cd src/web-form
npm install
npm run dev
# → http://localhost:3000
```

---

## API Proxy Setup

To avoid CORS issues in production, add a Next.js API route proxy in `src/web-form/app/api/proxy/route.ts`:

```typescript
import { NextRequest, NextResponse } from 'next/server'

export async function POST(req: NextRequest) {
  const body = await req.json()
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const res = await fetch(`${apiUrl}/support/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
```

Then in your form, POST to `/api/proxy` instead of directly to the backend.

---

## Embedding the Form

To embed the form in another site via iframe:

```html
<iframe
  src="https://your-vercel-app.vercel.app/support"
  width="100%"
  height="700"
  frameborder="0"
  title="NexaFlow Support"
></iframe>
```

---

## Form Pages

| Route | Description |
|-------|-------------|
| `/support` | Page 1 — Contact info (name, email) |
| `/support/issue` | Page 2 — Issue details (subject, category, priority, message) |
| `/support/submit` | Page 3 — Submits to API, shows ticket ID |
| `/support/status` | Page 4 — Real-time ticket status polling |
