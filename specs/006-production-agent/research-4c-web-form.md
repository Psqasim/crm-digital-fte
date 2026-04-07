# Research: Phase 4C-iii — Web Support Form

**Branch**: `006-production-agent` | **Date**: 2026-04-05
**Phase**: Phase 0 output for `/sp.plan` (Phase 4C-iii)

All unknowns from Technical Context resolved below.

---

## R-001: Next.js 15 App Creation in a Subdirectory

**Unknown**: Can `create-next-app` target `src/web-form/` inside an existing mono-repo
without polluting the root with `package.json`?

**Decision**: Yes — `npx create-next-app@latest src/web-form --typescript --tailwind
--app --no-src-dir --import-alias "@/*"` creates a self-contained Next.js project
at `src/web-form/` with its own `package.json`, `tsconfig.json`, `next.config.ts`,
and `node_modules/`. The root Python repo is unaffected.

**Rationale**: Context7 `/vercel/next.js` confirms `--app` flag enables App Router.
The `--no-src-dir` flag keeps files at `src/web-form/app/` (not
`src/web-form/src/app/`). This matches the spec `src/web-form/` location requirement.

---

## R-002: shadcn/ui Init Inside src/web-form

**Unknown**: Does `npx shadcn@latest init` work inside a subdirectory project?

**Decision**: Yes — run from `src/web-form/`: `cd src/web-form && npx shadcn@latest init`.
Answer prompts: base color `slate`, global CSS `app/globals.css`, CSS variables: yes.
This creates `components/ui/` and `lib/utils.ts` relative to `src/web-form/`.

**Required components to add**:
```
npx shadcn@latest add form input textarea select button badge card table toast skeleton
```

**Rationale**: Context7 `/shadcn-ui/ui` confirms the init workflow and that the Form
component wraps React Hook Form `Controller` with `FormField`, `FormItem`, `FormLabel`,
`FormMessage` for accessible validation messages.

---

## R-003: canvas-confetti TypeScript Types

**Unknown**: Does `canvas-confetti` ship TypeScript types or need `@types/`?

**Decision**: Install `canvas-confetti` + `@types/canvas-confetti` separately.
Usage: `import confetti from 'canvas-confetti'`.

**Pattern for success animation**:
```typescript
import confetti from 'canvas-confetti'

confetti({
  particleCount: 80,
  spread: 60,
  origin: { y: 0.6 },
  colors: ['#3B82F6', '#ffffff', '#0F172A'],
})
```
Call once on successful POST response, not on page load/refresh.

---

## R-004: next-themes Dark Mode Default

**Unknown**: How to set dark mode as default with next-themes and prevent flash of
unstyled content (FOUC)?

**Decision**: In `app/layout.tsx`, wrap `<html>` with `<ThemeProvider attribute="class"
defaultTheme="dark" enableSystem={false}>`. Add `suppressHydrationWarning` to `<html>`.

**Tailwind config**: Add `darkMode: "class"` to `tailwind.config.ts`.

**Pattern**:
```tsx
// app/layout.tsx
import { ThemeProvider } from 'next-themes'

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
```

---

## R-005: 5-Second Polling in Next.js Client Component

**Unknown**: Is `useEffect` + `setInterval` the correct pattern for 5-second polling,
or should we use Server-Sent Events / React Query?

**Decision**: `useEffect` + `setInterval` calling `fetch()` directly. Simple, no extra
library, matches spec requirement ("polling every 5 seconds — not WebSocket, simpler,
reliable").

**Pattern**:
```typescript
'use client'
import { useEffect, useState, useCallback } from 'react'

export function TicketPoller({ ticketId }: { ticketId: string }) {
  const [ticket, setTicket] = useState(null)

  const fetchTicket = useCallback(async () => {
    const res = await fetch(`/api/tickets/${ticketId}`)
    if (res.ok) setTicket(await res.json())
  }, [ticketId])

  useEffect(() => {
    fetchTicket() // initial load
    const id = setInterval(fetchTicket, 5000)
    return () => clearInterval(id)   // cleanup on unmount
  }, [fetchTicket])

  return <>{/* render ticket */}</>
}
```
Stop polling when status is "resolved" or "escalated" to avoid unnecessary requests.

---

## R-006: TKT-XXX Display ID Generation

**Unknown**: How should the human-readable ticket ID (TKT-XXX) be generated?
Sequential integer or derived from UUID?

**Decision**: Derive from the existing UUID primary key using
`'TKT-' || upper(substring(id::text, 1, 8))`. No extra column needed.
The FastAPI endpoint computes this on read and returns it in every ticket response.

**Rationale**: The tickets table uses UUID primary keys (existing schema). Adding a serial
column requires a migration. UUID substring is deterministic, unique within practical
limits for hackathon scale (~800 tickets/week), and requires no schema change.

**Format**: `TKT-A3F2C1B0` (TKT- prefix + first 8 chars of UUID, uppercase).

---

## R-007: Priority Field — Schema Gap

**Unknown**: The existing tickets table (Phase 4A schema) has: `id`, `conversation_id`,
`customer_id`, `channel`, `subject`, `category`, `status`, `created_at`, `updated_at`,
`resolved_at`, `escalation_reason`, `resolution_summary`. There is no `priority` column.
The web form collects priority. Where does it go?

**Decision**: Add `priority VARCHAR(20) DEFAULT 'medium'` to the tickets table via
`ALTER TABLE`. Update `queries.create_ticket()` to accept and store `priority`.
This is a backwards-compatible, additive change (DEFAULT means existing rows unaffected).

**Migration**: One-liner in Block 1, Task 1:
```sql
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'medium';
```

---

## R-008: Framer Motion with Next.js 15 App Router

**Unknown**: Does Framer Motion work with React Server Components, or do animated
components need `'use client'`?

**Decision**: All Framer Motion components MUST be Client Components (`'use client'`).
Server Components cannot use `motion.*` because Framer Motion uses browser APIs and
React hooks internally.

**Pattern**: Create thin Client Component wrappers for animated sections:
```tsx
// components/animations/FadeIn.tsx
'use client'
import { motion } from 'framer-motion'

export function FadeIn({ children, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      {children}
    </motion.div>
  )
}
```
Landing page uses `FadeIn` wrappers. Server Components pass data as props.

---

## R-009: FastAPI Lifespan — DB Pool for Web Form Endpoints

**Unknown**: The existing `production/api/main.py` uses `lifespan` only for Kafka
shutdown. Web form endpoints need a DB pool. How to wire it?

**Decision**: Use `asyncpg` lazy pool via `queries.get_db_pool()` (already implemented
in `production/database/queries.py`). The pool is initialised on first call and shared
across requests via the module-level `_pool` variable. No lifespan change needed.

**FastAPI dependency**:
```python
from production.database.queries import get_db_pool

async def get_pool():
    return await get_db_pool()

@router.post("/support/submit")
async def submit_web_form(body: WebFormInput, pool=Depends(get_pool)):
    ...
```

---

## R-010: Next.js API Proxy — Error Passthrough

**Unknown**: When FastAPI returns 404 or 422, should the Next.js proxy pass through
the status code, or always return 200?

**Decision**: Pass through status codes faithfully. The Next.js proxy reads the FastAPI
response status and returns it unchanged to the browser client.

**Pattern**:
```typescript
// app/api/tickets/[id]/route.ts
export async function GET(req: NextRequest, { params }) {
  const { id } = await params
  const res = await fetch(`${process.env.FASTAPI_URL}/support/ticket/${id}`)
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
```
404 from FastAPI → Next.js proxy → 404 to browser → `not-found.tsx` renders.
