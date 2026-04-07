# NexaFlow Web Support Form

Next.js 16 (App Router) frontend for the NexaFlow CRM Digital FTE Factory.

## Pages

| Route | Description |
|-------|-------------|
| `/` | Landing page — hero + feature cards |
| `/support` | Support ticket submission form |
| `/ticket/[id]` | Ticket status with live polling |
| `/dashboard` | Support metrics dashboard |

## Lighthouse Scores (last run: 2026-04-07)

| Page | Performance | Accessibility | Best Practices | SEO |
|------|-------------|---------------|----------------|-----|
| `/` | 95 | 95 | 100 | 100 |
| `/support` | 93 | 97 | 100 | 100 |
| `/ticket/[id]` | 94 | 96 | 100 | 100 |
| `/dashboard` | 92 | 95 | 100 | 100 |

## Setup

```bash
npm install
cp .env.example .env.local
# Set FASTAPI_URL=http://localhost:8000 in .env.local
npm run dev
```

## Stack

- Next.js 16.2 (App Router, Turbopack)
- Tailwind CSS v4 (CSS-native @theme config)
- shadcn/ui v4 (@base-ui/react components)
- Framer Motion (with prefers-reduced-motion support)
- React Hook Form + Zod
- canvas-confetti
- next-themes (dark mode)
