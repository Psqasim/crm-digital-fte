# Tasks: Phase 4C-iii — NexaFlow Web Support Form

**Input**: `specs/006-production-agent/`
**Branch**: `006-production-agent`
**Plan**: `specs/006-production-agent/plan-4c-web-form.md`
**Spec**: `specs/006-production-agent/spec-4c-web-form.md`
**Phase**: 4C-iii (Next.js Web Support Form)
**Phase 4C-i/ii baseline**: Gmail + WhatsApp handlers complete; 142/142 Python tests passing

> **Legend**
> - `⚠️ HIGH RISK` — must not break 142 existing Python tests; run `pytest` gate before touching frontend
> - `[P]` — parallelisable (different files, no incomplete dependencies)
> - `[US1]` — Customer submits ticket (P1); `[US2]` — Ticket status polling (P2); `[US3]` — Dashboard (P3); `[US4]` — Landing page (P4)
> - **Recommended order**: Phase 1 → Phase 2 (Python + Next.js scaffold in parallel) → T036 gate → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (US4) → Phase 7 (Polish)
> - Tests NOT requested; Python regression gate (T036) is the only test checkpoint

---

## Phase 1: Setup — Database Migration

**Purpose**: Backwards-compatible schema change that unlocks priority field for all user stories.
**⚠️ CRITICAL**: Must complete before any Python backend code that touches `tickets` table.

- [X] T001 Create migration file `production/database/migrations/add_ticket_priority.sql` with `ALTER TABLE tickets ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'medium'`
  - **File**: `production/database/migrations/add_ticket_priority.sql` (NEW)
  - **Acceptance**: File contains exactly one DDL statement; `IF NOT EXISTS` guard present; `DEFAULT 'medium'` present
  - **Depends on**: None
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T002 Apply migration to Neon PostgreSQL: `psql $DATABASE_URL -f production/database/migrations/add_ticket_priority.sql`
  - **File**: Neon PostgreSQL `tickets` table (SCHEMA CHANGE)
  - **Acceptance**: `psql` returns `ALTER TABLE` (not an error); `\d tickets` shows `priority` column with `character varying(20)` type and `'medium'` default
  - **Depends on**: T001
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T003 Update `queries.create_ticket()` signature: add `priority: str = "medium"` parameter and include in INSERT: `(... priority) VALUES (... $6)` with `RETURNING id, priority`
  - **File**: `production/database/queries.py` (UPDATE)
  - **Acceptance**: Function signature is `async def create_ticket(pool, conv_id, customer_id, channel, subject, category, priority="medium") -> dict`; INSERT includes `priority` column; `RETURNING id, priority` appended
  - **Depends on**: T002
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T004 Verify backwards compatibility: existing callers of `create_ticket()` (Gmail handler, WhatsApp handler) pass no `priority` arg and still work; default `"medium"` applies
  - **File**: `production/channels/gmail_handler.py`, `production/channels/whatsapp_handler.py` (INSPECT only — no edits needed)
  - **Acceptance**: `grep -n "create_ticket" production/channels/gmail_handler.py production/channels/whatsapp_handler.py` shows calls without `priority` argument; no `TypeError` when called; all 142 existing tests still pass after T003 change
  - **Depends on**: T003
  - **Test needed**: No
  - **HIGH RISK**: No

---

## Phase 2: Foundational — Python Queries + Next.js Scaffold + Shared Components

**Purpose**: All blocking prerequisites for user story phases. Python queries (T005-T006) and the Next.js scaffold (T007-T010) can proceed in parallel. Components depend on the scaffold.
**⚠️ CRITICAL**: T036 Python regression gate must pass before any frontend user story begins.

### 2A — Python DB Queries (can run in parallel with 2B)

- [X] T005 [P] Add `get_ticket_by_display_id(pool, ticket_id: str) -> dict | None` to `production/database/queries.py`: if `ticket_id.startswith("TKT-")` query `WHERE upper(substring(id::text, 1, 8)) = $1` (pass 8-char suffix); else query `WHERE id::text = $1`; JOIN `customers` on `customer_id` for `name`, `email`; JOIN first `role='customer'` `messages` row for original `body`; return dict with `ticket_id` (display), `internal_id`, `status`, `category`, `priority`, `subject`, `message`, `customer_name`, `customer_email`, `created_at`, `updated_at`, `resolved_at`; display ID computed as `'TKT-' + str(row['id'])[:8].upper()`
  - **File**: `production/database/queries.py` (UPDATE)
  - **Acceptance**: `get_ticket_by_display_id(pool, "TKT-ABCD1234")` returns dict with all 13 fields; `get_ticket_by_display_id(pool, "nonexistent-uuid")` returns `None`; no new imports required beyond existing asyncpg usage
  - **Depends on**: T002
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T006 [P] Add `get_metrics_summary(pool) -> dict` to `production/database/queries.py`: single COUNT FILTER query for total/open/in_progress/resolved/escalated; GROUP BY channel query for channel breakdown; JOIN customers query for recent 10 tickets (ORDER BY created_at DESC, LIMIT 10); compute `escalation_rate = round((escalated / total) * 100, 1)` when total > 0 else `0.0`; return complete metrics dict matching `contracts/web-form-api.md`
  - **File**: `production/database/queries.py` (UPDATE)
  - **Acceptance**: Returns dict with keys `total`, `open`, `in_progress`, `resolved`, `escalated`, `escalation_rate`, `channels` (dict), `recent_tickets` (list of ≤10); `escalation_rate` is float; no AttributeError when table is empty (handle zero division)
  - **Depends on**: T002
  - **Test needed**: No
  - **HIGH RISK**: No

### 2B — Next.js Scaffold ⚠️ HIGH RISK

- [X] T007 ⚠️ HIGH RISK — Create Next.js app from repo root: `mkdir -p src/web-form && cd src/web-form && npx create-next-app@latest . --typescript --tailwind --eslint --app --no-git --import-alias "@/*"` — `--no-git` prevents nested git repo inside `src/web-form/`
  - **File**: `src/web-form/` directory (NEW — full scaffold)
  - **Acceptance**: `src/web-form/app/layout.tsx` exists; `src/web-form/package.json` exists; `src/web-form/tsconfig.json` exists; `src/web-form/tailwind.config.ts` exists; no `.git` folder inside `src/web-form/`
  - **Depends on**: None
  - **Test needed**: No
  - **HIGH RISK**: Yes — path errors or conflicting tsconfig block all frontend work; use exact command above

- [X] T008 Install additional npm packages from `src/web-form/`: `npm install framer-motion canvas-confetti next-themes react-hook-form @hookform/resolvers zod && npm install --save-dev @types/canvas-confetti`
  - **File**: `src/web-form/package.json` + `src/web-form/node_modules/` (UPDATE)
  - **Acceptance**: `package.json` lists all 6 runtime deps + 1 devDep; `node_modules/framer-motion`, `node_modules/canvas-confetti`, `node_modules/next-themes`, `node_modules/react-hook-form`, `node_modules/zod` all exist
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T009 Run shadcn/ui init from `src/web-form/`: `npx shadcn@latest init` (base color: `slate`, CSS variables: yes); then add components: `npx shadcn@latest add form input textarea select button badge card table toast skeleton`
  - **File**: `src/web-form/components/ui/` (GENERATED), `src/web-form/lib/utils.ts` (GENERATED), `src/web-form/app/globals.css` (UPDATED with shadcn CSS vars)
  - **Acceptance**: `src/web-form/components/ui/` contains: `form.tsx`, `input.tsx`, `textarea.tsx`, `select.tsx`, `button.tsx`, `badge.tsx`, `card.tsx`, `table.tsx`, `toast.tsx`, `skeleton.tsx`; `lib/utils.ts` exports `cn()` helper
  - **Depends on**: T008
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T010 Verify dev server starts: from `src/web-form/` run `PORT=3001 npm run dev` — must open on `localhost:3001` with no TypeScript errors and no console errors; stop with Ctrl+C after confirming
  - **File**: N/A (verification step)
  - **Acceptance**: Terminal shows `✓ Ready in` message; `http://localhost:3001` returns HTTP 200; no red errors in terminal output
  - **Depends on**: T009
  - **Test needed**: No
  - **HIGH RISK**: Yes — if dev server fails, diagnose before proceeding; do NOT skip

### 2C — Tailwind Config (depends on T007)

- [X] T011 [P] Add `darkMode: "class"` to `src/web-form/tailwind.config.ts`
  - **File**: `src/web-form/tailwind.config.ts` (UPDATE)
  - **Acceptance**: `tailwind.config.ts` contains `darkMode: "class"` at top level of config object
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T012 [P] Extend `theme.extend.colors` in `src/web-form/tailwind.config.ts` with NexaFlow brand: `nexaflow: { bg: '#0F172A', accent: '#3B82F6', 'accent-hover': '#2563EB' }`
  - **File**: `src/web-form/tailwind.config.ts` (UPDATE)
  - **Acceptance**: Colors nested under `theme.extend.colors.nexaflow`; existing shadcn CSS variable colors untouched; `bg-nexaflow-bg` class compiles without error
  - **Depends on**: T009
  - **Test needed**: No
  - **HIGH RISK**: No

### 2D — Global Layout (depends on T009)

- [X] T013 Add `ThemeProvider` from `next-themes` to `src/web-form/app/layout.tsx`: wrap `{children}` with `<ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>`
  - **File**: `src/web-form/app/layout.tsx` (UPDATE)
  - **Acceptance**: `ThemeProvider` imported from `next-themes`; `defaultTheme="dark"` set; `enableSystem={false}`; no hydration warning in browser console on first load
  - **Depends on**: T008
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T014 Add `suppressHydrationWarning` attribute to `<html>` tag in `src/web-form/app/layout.tsx` to prevent FOUC (Flash of Unstyled Content) from theme switching
  - **File**: `src/web-form/app/layout.tsx` (UPDATE)
  - **Acceptance**: `<html lang="en" suppressHydrationWarning>` present; no hydration mismatch warning in browser console
  - **Depends on**: T013
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T015 Add `<Navbar />` component above `{children}` in `<body>` in `src/web-form/app/layout.tsx` (Navbar component created in T022)
  - **File**: `src/web-form/app/layout.tsx` (UPDATE)
  - **Acceptance**: Import `Navbar` from `"@/components/Navbar"`; `<Navbar />` rendered before `{children}` in body
  - **Depends on**: T013, T022
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T016 Add `<Toaster />` from shadcn sonner below `{children}` in `src/web-form/app/layout.tsx` for toast notifications
  - **File**: `src/web-form/app/layout.tsx` (UPDATE)
  - **Acceptance**: `Toaster` imported from `"@/components/ui/sonner"` or `"sonner"`; rendered after `{children}` in body; toasts dismiss on Escape
  - **Depends on**: T009, T013
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T017 Add `generateMetadata` export to `src/web-form/app/layout.tsx`: `title: "NexaFlow Support"`, `description: "AI-powered customer support for NexaFlow"`, `og:type: "website"`, `og:title`, `og:description`
  - **File**: `src/web-form/app/layout.tsx` (UPDATE)
  - **Acceptance**: `export const metadata: Metadata` (not `generateMetadata` — root layout uses static export); `<title>NexaFlow Support</title>` in rendered HTML `<head>`; OG tags present in `<head>`
  - **Depends on**: T013
  - **Test needed**: No
  - **HIGH RISK**: No

### 2E — Environment Config (depends on T007)

- [X] T018 [P] Create `src/web-form/.env.example` with `FASTAPI_URL=http://localhost:8000`
  - **File**: `src/web-form/.env.example` (NEW)
  - **Acceptance**: File exists; contains `FASTAPI_URL=http://localhost:8000`; no actual secrets; committed to git
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T019 [P] Create `src/web-form/.env.local` with `FASTAPI_URL=http://localhost:8000` (gitignored by default Next.js .gitignore)
  - **File**: `src/web-form/.env.local` (NEW — gitignored)
  - **Acceptance**: File exists locally; `src/web-form/.gitignore` already contains `.env.local` (created-next-app adds this); file NOT committed; `process.env.FASTAPI_URL` resolves in API routes
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T020 [P] Update `src/web-form/next.config.ts`: add `images: { unoptimized: true }` for Docker compatibility; no rewrites needed (proxy handled via API routes)
  - **File**: `src/web-form/next.config.ts` (UPDATE)
  - **Acceptance**: `nextConfig.images.unoptimized = true`; no rewrites block present; `npm run build` completes without error
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

### 2F — Shared Components (depends on T009)

- [X] T021 [P] Create `src/web-form/lib/types.ts` with shared TypeScript interfaces: `TicketStatus`, `TicketData`, `MetricsSummary`, `ChannelBreakdown`, `FormPayload`, `TicketResponse`
  - **File**: `src/web-form/lib/types.ts` (NEW)
  - **Acceptance**: All 6 interfaces exported; `TicketStatus` is `'open' | 'in_progress' | 'resolved' | 'escalated'`; `TicketData` has `ticket_id`, `internal_id`, `status: TicketStatus`, `category`, `priority`, `subject`, `message`, `customer_name`, `customer_email`, `created_at`; `MetricsSummary` has `total`, `open`, `in_progress`, `resolved`, `escalated`, `escalation_rate`, `channels`, `recent_tickets`; no `any` types
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T022 [P] Create `src/web-form/components/NexaFlowLogo.tsx`: inline SVG lightning bolt (24×24px, fill `#3B82F6`) + "NexaFlow" text (`font-bold text-xl`); responsive — hide text on `xs`, show on `sm+` using `hidden sm:inline`
  - **File**: `src/web-form/components/NexaFlowLogo.tsx` (NEW)
  - **Acceptance**: Server Component (no `'use client'`); SVG renders at 24×24; text hidden below `sm` breakpoint; component accepts optional `size?: 'sm' | 'lg'` prop for landing page large variant
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T023 [P] Create `src/web-form/components/Navbar.tsx`: sticky top nav with `bg-[#0F172A]/90 backdrop-blur-sm border-b border-slate-800`; `<NexaFlowLogo />` on left; "Get Support" `<Link href="/support">` button + `<ThemeToggle />` on right; Server Component (ThemeToggle is a Client child)
  - **File**: `src/web-form/components/Navbar.tsx` (NEW)
  - **Acceptance**: `sticky top-0 z-50` applied; NexaFlowLogo visible; "Get Support" links to `/support`; ThemeToggle renders on right; no `'use client'` on Navbar itself
  - **Depends on**: T022, T024
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T024 [P] Create `src/web-form/components/ThemeToggle.tsx`: Client Component (`'use client'`); `useTheme()` from `next-themes`; Button with Lucide `Sun` icon (light mode) / `Moon` icon (dark mode); render `null` on initial mount to avoid hydration mismatch; `aria-label="Switch to light/dark mode"`
  - **File**: `src/web-form/components/ThemeToggle.tsx` (NEW)
  - **Acceptance**: `'use client'` directive present; toggles between `dark` and `light` class on `<html>`; initial render returns `null` (no flash); `aria-label` present on button
  - **Depends on**: T009
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T025 [P] Create `src/web-form/components/StatusBadge.tsx`: Server Component; props `{ status: TicketStatus }`; color map: `open` → `bg-blue-500/20 text-blue-400 border-blue-500/30`, `in_progress` → `bg-yellow-500/20 text-yellow-400 border-yellow-500/30`, `resolved` → `bg-green-500/20 text-green-400 border-green-500/30`, `escalated` → `bg-red-500/20 text-red-400 border-red-500/30`; display labels: "Open", "In Progress", "Resolved", "Escalated"
  - **File**: `src/web-form/components/StatusBadge.tsx` (NEW)
  - **Acceptance**: No `'use client'`; `border` class applied for outline pill style; label text matches display names above; unknown status falls back to neutral styling without crash
  - **Depends on**: T021
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T026 [P] Create `src/web-form/components/LoadingSkeleton.tsx` with two named exports: `TicketStatusSkeleton` — skeleton matching ticket status page layout (ID bar, badge, 3 metadata rows, message block); `DashboardSkeleton` — 4 card skeletons + 5 table row skeletons; use shadcn `<Skeleton>` component
  - **File**: `src/web-form/components/LoadingSkeleton.tsx` (NEW)
  - **Acceptance**: Both exports present; uses `<Skeleton className="...">` from `"@/components/ui/skeleton"`; no `'use client'` needed (Skeleton is a pure UI component); dimensions approximate the real content
  - **Depends on**: T009
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T027 [P] Create `src/web-form/components/animations/FadeIn.tsx`: Client Component; `motion.div` from `framer-motion` with `initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay }}`; props: `children: React.ReactNode`, `delay?: number`; respect `prefers-reduced-motion` via `useReducedMotion()` — if true, render children without motion wrapper
  - **File**: `src/web-form/components/animations/FadeIn.tsx` (NEW)
  - **Acceptance**: `'use client'` present; `useReducedMotion()` imported from `framer-motion`; when reduced motion is true, children render without animation (instant); `delay` defaults to `0`
  - **Depends on**: T008
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T028 [P] Create `src/web-form/components/animations/SlideUp.tsx`: Client Component; `motion.div` with `initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay }}`; same `prefers-reduced-motion` guard as FadeIn
  - **File**: `src/web-form/components/animations/SlideUp.tsx` (NEW)
  - **Acceptance**: `'use client'` present; `y: 24` initial y-offset; reduced motion renders instantly; `delay` prop forwarded to transition
  - **Depends on**: T008
  - **Test needed**: No
  - **HIGH RISK**: No

- [X] T036 ⚠️ PYTHON REGRESSION GATE — Run `pytest tests/ production/tests/ -v` from repo root; must show exactly `142 passed, 0 failed` before any frontend user story work begins
  - **File**: N/A (gate checkpoint — no file changes)
  - **Acceptance**: `pytest` exits with code 0; output shows `142 passed`; if any test fails, fix regression before proceeding to Phase 3
  - **Depends on**: T003, T004 (all Python changes complete)
  - **Test needed**: Yes — this IS the test
  - **HIGH RISK**: Yes — frontend work must not begin until this passes

---

## Phase 3: User Story 1 — Customer Submits Support Ticket (Priority: P1) ⚠️ HIGH RISK

**Goal**: Customer fills `/support` form → POST to FastAPI → ticket persisted in DB + published to Kafka → ticket ID returned → confetti + toast → redirect to `/ticket/[id]`.

**Independent Test**: Navigate to `/support`. Fill all 6 fields with valid data. Click Submit. Assert: (a) button enters "Submitting..." disabled state immediately; (b) within 3 seconds a success toast appears with "Ticket #TKT-XXX created!"; (c) confetti fires; (d) `/ticket/[id]` loads with correct details.

### 3A — WebFormHandler Python Backend ⚠️ HIGH RISK

- [ ] T037 Define `WebFormInput` Pydantic v2 model in `production/channels/web_form_handler.py`: `name: str = Field(min_length=1, max_length=200)`, `email: EmailStr`, `subject: str = Field(min_length=5, max_length=200)`, `category: Literal["billing", "technical", "account", "general"]`, `priority: Literal["low", "medium", "high", "urgent"]`, `message: str = Field(min_length=20, max_length=2000)`
  - **File**: `production/channels/web_form_handler.py` (REPLACE stub)
  - **Acceptance**: Model imports `BaseModel`, `Field`, `EmailStr`, `Literal` from correct Pydantic v2 paths; invalid email raises `ValidationError`; message < 20 chars raises `ValidationError`; unknown category raises `ValidationError`
  - **Depends on**: T036
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T038 [US1] ⚠️ HIGH RISK — Subtask A: Implement `get_or_create_customer` step in `submit_ticket(pool, body: WebFormInput)` — call `await queries.get_or_create_customer(pool, email=body.email, name=body.name)`; if raises exception → log to stderr and re-raise (outer try/except handles rollback)
  - **File**: `production/channels/web_form_handler.py` (UPDATE)
  - **Acceptance**: Step 1 uses existing `queries.get_or_create_customer()`; returns `customer` dict with `id` key; on DB error re-raises (does NOT swallow); no orphaned records created yet at this step
  - **Depends on**: T037
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T039 [US1] ⚠️ HIGH RISK — Subtask B: Implement `create_conversation` step in `submit_ticket()` — call `await queries.create_conversation(pool, customer_id=customer['id'], channel="web_form")`; returns `conv_id`
  - **File**: `production/channels/web_form_handler.py` (UPDATE)
  - **Acceptance**: `channel="web_form"` hardcoded (not passed from body); `conv_id` used in subsequent steps; on failure re-raises for outer catch
  - **Depends on**: T038
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T040 [US1] ⚠️ HIGH RISK — Subtask C: Implement `add_message` step in `submit_ticket()` — call `await queries.add_message(pool, conv_id, role="customer", content=body.message, channel="web_form")`; returns `msg_id`
  - **File**: `production/channels/web_form_handler.py` (UPDATE)
  - **Acceptance**: `role="customer"` set; `content=body.message`; `channel="web_form"`; `msg_id` captured (used for audit); on failure re-raises
  - **Depends on**: T039
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T041 [US1] ⚠️ HIGH RISK — Subtask D: Implement `create_ticket` step in `submit_ticket()` — call `await queries.create_ticket(pool, conv_id, customer['id'], channel="web_form", subject=body.subject, category=body.category, priority=body.priority)`; returns `ticket_id_uuid` (UUID string)
  - **File**: `production/channels/web_form_handler.py` (UPDATE)
  - **Acceptance**: All 7 args passed including `priority=body.priority`; `ticket_id_uuid` is a UUID string (not display ID); on failure re-raises; if this step fails, conversation + message are orphaned (logged, acceptable per plan — no delete rollback needed)
  - **Depends on**: T040, T003
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T042 [US1] ⚠️ HIGH RISK — Subtask E: Publish to Kafka in `submit_ticket()` — build `TicketMessage(id=str(uuid4()), channel="web_form", customer_email=body.email, customer_name=body.name, subject=body.subject, message=body.message, received_at=datetime.now(ZoneInfo("Asia/Karachi")).isoformat(), metadata={})` then `await kafka_producer.publish_ticket(ticket_message)`; on Kafka failure: `print(f"[kafka_error] {e}", file=sys.stderr)` and do NOT re-raise (ticket already in DB — Kafka is best-effort)
  - **File**: `production/channels/web_form_handler.py` (UPDATE)
  - **Acceptance**: `received_at` uses `datetime.now(ZoneInfo("Asia/Karachi"))` (never guess date); Kafka failure does NOT raise — ticket ID still returned; topic is `"fte.tickets.incoming"`; `channel="web_form"` on TicketMessage
  - **Depends on**: T041
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T043 [US1] ⚠️ HIGH RISK — Subtask F: Return `ticket_id + estimated_response_time` from `submit_ticket()` — return `{ "ticket_id": "TKT-" + ticket_id_uuid[:8].upper(), "internal_id": ticket_id_uuid, "status": "open", "created_at": datetime.now(ZoneInfo("Asia/Karachi")).isoformat(), "estimated_response_time": "~4 hours" }`
  - **File**: `production/channels/web_form_handler.py` (UPDATE)
  - **Acceptance**: Display ID format is exactly `"TKT-" + first_8_chars_uppercase`; `status` is `"open"`; `estimated_response_time` is present; dict returned (not None) on full success
  - **Depends on**: T042
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T044 [US1] ⚠️ HIGH RISK — Wrap entire `submit_ticket()` body in `try/except Exception as e`: on exception `print(f"[web_form_error] {e}", file=sys.stderr)` and `return None`; rollback note: DB has no explicit transaction rollback — orphaned records are acceptable per plan; only ticket creation failure is critical (returns None → 500)
  - **File**: `production/channels/web_form_handler.py` (UPDATE)
  - **Acceptance**: Any exception in steps A–F causes function to return `None` (not raise); error logged to stderr with prefix `[web_form_error]`; partial DB records (customer, conv, message without ticket) are accepted orphans; complete function is inside the try block
  - **Depends on**: T043
  - **Test needed**: No
  - **HIGH RISK**: Yes

### 3B — FastAPI Web Form Router

- [ ] T045 [US1] Create `production/api/web_form_routes.py` with `router = APIRouter()` — no prefix on router (paths registered on router directly to produce clean `/support/submit` etc.)
  - **File**: `production/api/web_form_routes.py` (NEW)
  - **Acceptance**: `from fastapi import APIRouter`; `router = APIRouter()`; file importable without error; `WebFormInput` imported from `production.channels.web_form_handler`
  - **Depends on**: T037
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T046 [US1] Implement `POST /support/submit` in `web_form_routes.py`: validate body as `WebFormInput` (FastAPI auto-validates; 422 on schema failure); call `web_form_handler.submit_ticket(pool, body)`; return `JSONResponse(result, status_code=201)` on success; return `JSONResponse({"detail": "Internal server error"}, status_code=500)` when result is `None`
  - **File**: `production/api/web_form_routes.py` (UPDATE)
  - **Acceptance**: `@router.post("/support/submit")`; invalid body → 422 (automatic); `submit_ticket` returns None → 500 with `{"detail": "Internal server error"}`; success → 201 with full result dict
  - **Depends on**: T045, T044
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T047 [US1] Implement `GET /support/ticket/{ticket_id}` in `web_form_routes.py`: call `queries.get_ticket_by_display_id(pool, ticket_id)`; return 200 with ticket dict on success; return `JSONResponse({"detail": "Ticket not found"}, status_code=404)` when None
  - **File**: `production/api/web_form_routes.py` (UPDATE)
  - **Acceptance**: `@router.get("/support/ticket/{ticket_id}")`; valid TKT-XXXXXX → 200; unknown ID → 404 with `{"detail": "Ticket not found"}`; no 500 for normal not-found case
  - **Depends on**: T045, T005
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T048 [US1] Implement `GET /metrics/summary` in `web_form_routes.py`: call `queries.get_metrics_summary(pool)`; return 200 with metrics dict; set `Cache-Control: no-store` response header
  - **File**: `production/api/web_form_routes.py` (UPDATE)
  - **Acceptance**: `@router.get("/metrics/summary")`; returns 200 with full metrics dict; `Cache-Control: no-store` header present on response
  - **Depends on**: T045, T006
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T049 [US1] Register web form router in `production/api/main.py`: add `from production.api.web_form_routes import router as web_form_router` and `app.include_router(web_form_router)`
  - **File**: `production/api/main.py` (UPDATE)
  - **Acceptance**: Import line present; `app.include_router(web_form_router)` added after existing router registrations; existing `/webhooks/gmail` and `/webhooks/whatsapp` routes still accessible (no prefix collision); `uvicorn` starts without error
  - **Depends on**: T045
  - **Test needed**: No
  - **HIGH RISK**: No

### 3C — Next.js POST Proxy Route

- [ ] T050 [US1] Create `src/web-form/app/api/tickets/route.ts` — `POST` handler: parse request body as JSON; `fetch(\`${process.env.FASTAPI_URL}/support/submit\`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })`; pass through status + body via `return NextResponse.json(data, { status: res.status })`; catch network error → return `NextResponse.json({ detail: "Service unavailable" }, { status: 503 })`; add `export const dynamic = 'force-dynamic'`
  - **File**: `src/web-form/app/api/tickets/route.ts` (NEW)
  - **Acceptance**: File exports `POST` function and `dynamic = 'force-dynamic'`; FastAPI 201 → proxied 201; FastAPI 422 → proxied 422 (error detail preserved, not swallowed); network failure → 503; `FASTAPI_URL` from `process.env` (server-side only, not prefixed `NEXT_PUBLIC_`)
  - **Depends on**: T019, T049
  - **Test needed**: No
  - **HIGH RISK**: No

### 3D — Support Form Page ⚠️ HIGH RISK

- [ ] T051 [US1] Create `src/web-form/app/support/page.tsx` — Server Component; static metadata export: `title: "Submit a Support Ticket | NexaFlow"`, `description`, `og:title`, `og:description`; renders `<SupportForm />` client component below a heading `"Get Support"` with subheading
  - **File**: `src/web-form/app/support/page.tsx` (NEW)
  - **Acceptance**: `export const metadata`; no `'use client'`; imports `SupportForm` from `"./SupportForm"`; page title in browser tab reads "Submit a Support Ticket | NexaFlow"
  - **Depends on**: T009, T017
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T052 [US1] ⚠️ HIGH RISK — Subtask A: Define Zod schema in `src/web-form/app/support/SupportForm.tsx` (new file): `formSchema = z.object({ name: z.string().min(1, 'Name is required'), email: z.string().email('Enter a valid email'), subject: z.string().min(5, 'Subject must be at least 5 characters'), category: z.enum(['billing', 'technical', 'account', 'general'], { required_error: 'Category is required' }), priority: z.enum(['low', 'medium', 'high', 'urgent'], { required_error: 'Priority is required' }), message: z.string().min(20, 'Message must be at least 20 characters').max(2000, 'Message cannot exceed 2000 characters') })`
  - **File**: `src/web-form/app/support/SupportForm.tsx` (NEW)
  - **Acceptance**: `'use client'` directive at top; schema exported as `formSchema`; `z.string().email()` rejects `"not-an-email"`; `message` with 19 chars fails `.min(20)`; `message` with 2001 chars fails `.max(2000)`; `category` with value `"other"` fails `.enum()`
  - **Depends on**: T008, T009
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T053 [US1] ⚠️ HIGH RISK — Subtask B: Set up `useForm` with `zodResolver` in `SupportForm.tsx`: `const form = useForm<z.infer<typeof formSchema>>({ resolver: zodResolver(formSchema), defaultValues: { name: '', email: '', subject: '', category: undefined, priority: undefined, message: '' } })`
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE)
  - **Acceptance**: `useForm` imported from `react-hook-form`; `zodResolver` imported from `@hookform/resolvers/zod`; `defaultValues` includes all 6 fields; form state `isDirty` starts as false; validation only triggers on submit (not on every keystroke)
  - **Depends on**: T052
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T054 [US1] ⚠️ HIGH RISK — Subtask C: Build form UI in `SupportForm.tsx`: shadcn `<Form>` wraps all content; 6 fields each use `<FormField control={form.control} name="...">` → `<FormItem>` → `<FormLabel>` → `<FormControl>` → appropriate input → `<FormMessage>`; Name: `<Input>`; Email: `<Input type="email">`; Subject: `<Input>`; Category: `<Select>` with 4 options; Priority: `<Select>` with 4 options; Message: `<Textarea rows={5}`; dark theme: `bg-slate-900/50 border-slate-700` on form card
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE)
  - **Acceptance**: All 6 `<FormLabel>` components present; all 6 `<FormMessage>` components present (they show error text automatically via RHF); Category/Priority each have all 4 options; empty submit shows validation errors on all required fields without a network request
  - **Depends on**: T053
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T055 [US1] Add live character counter to Message `<Textarea>`: `const messageLength = form.watch('message').length`; display `{messageLength}/2000` below textarea; apply `text-red-400 font-medium` when `messageLength >= 1800`
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE)
  - **Acceptance**: Counter updates on every keystroke; counter turns red at 1800 chars; counter shows `0/2000` on empty form; counter resets after successful submission
  - **Depends on**: T054
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T056 [US1] ⚠️ HIGH RISK — Subtask D: Implement optimistic submit handler in `SupportForm.tsx`: `form.handleSubmit(async (data) => { setSubmitting(true); const res = await fetch('/api/tickets', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); const json = await res.json(); if (res.ok) { /* success path */ } else { toast.error(json.detail || 'Submission failed'); setSubmitting(false); } })`; on success: show confetti (T057) + toast with ticket ID + `router.push('/ticket/' + ticketId)` after 2 seconds
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE)
  - **Acceptance**: `setSubmitting(true)` called before `fetch`; on 201 response `setSubmitting` stays true (navigating away); on any error `setSubmitting(false)` called before returning; form field values NOT cleared on error (zero data loss); `useRouter` imported from `next/navigation`
  - **Depends on**: T054, T050
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T057 [US1] ⚠️ HIGH RISK — Subtask E: Add canvas-confetti trigger in `SupportForm.tsx`: `import confetti from 'canvas-confetti'`; on success call `confetti({ particleCount: 80, spread: 60, origin: { y: 0.6 }, colors: ['#3B82F6', '#2563EB', '#60A5FA', '#FFFFFF'] })`; guard with `confettiFired` ref to ensure fires exactly once per submission: `const confettiFired = useRef(false)` → set to true after firing → reset on new submission attempt
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE)
  - **Acceptance**: Confetti fires exactly once on success (not on page revisit or refresh); colors include NexaFlow blue `#3B82F6`; duration approx 2 seconds; `confettiFired.current` reset to false when submit button is re-enabled for retry
  - **Depends on**: T056
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T058 [US1] Add disabled submit button state in `SupportForm.tsx`: `<Button type="submit" disabled={submitting}>{submitting ? 'Submitting...' : 'Submit Ticket'}</Button>`; button is `w-full` on mobile
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE)
  - **Acceptance**: Button shows "Submitting..." when `submitting === true`; button `disabled` attribute prevents double-click; button re-enables after error (when `setSubmitting(false)` called)
  - **Depends on**: T056
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T059 [US1] ⚠️ HIGH RISK — Subtask F: Add Framer Motion entrance animations to support form: wrap form card in `<SlideUp delay={0.1}>` and page heading in `<FadeIn delay={0}>` — import animation components from `@/components/animations`
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE), `src/web-form/app/support/page.tsx` (UPDATE)
  - **Acceptance**: Form card slides up 24px into view on page load; heading fades in; animations complete within 600ms; with `prefers-reduced-motion` system setting enabled, form renders instantly (no animation)
  - **Depends on**: T027, T028, T054
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T060 [US1] Add accessibility attributes to `SupportForm.tsx`: all `<FormLabel>` have implicit `htmlFor` via shadcn; add `aria-describedby` to each input pointing to `<FormMessage>` ID; verify Tab order matches visual top-to-bottom field order
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE)
  - **Acceptance**: Each `<Input>`/`<Textarea>`/`<Select>` has `aria-describedby` matching its `<FormMessage>` element id; Tab key moves Name → Email → Subject → Category → Priority → Message → Submit in order; Enter key on submit button submits the form
  - **Depends on**: T054
  - **Test needed**: No
  - **HIGH RISK**: No

**Checkpoint Phase 3**: Navigate to `/support`, fill valid data, submit. Should see: disabled button → confetti → toast with "Ticket #TKT-XXX created!" → redirect to `/ticket/[id]`.

---

## Phase 4: User Story 2 — Customer Tracks Ticket Status (Priority: P2) ⚠️ HIGH RISK

**Goal**: `/ticket/[id]` page polls every 5 seconds, shows skeleton on load, shows typing indicator when open/in_progress, stops polling when resolved/escalated, shows not-found for invalid IDs.

**Independent Test**: Navigate to `/ticket/[id]` with valid ID. Assert: (a) skeleton loader visible during initial fetch; (b) details render with colored status badge; (c) "AI is analyzing your ticket..." visible for open/in_progress; (d) polling fires every 5s (verify via Network tab); (e) visiting `/ticket/invalid-id` shows not-found page, not a crash.

### 4A — Next.js GET Ticket Proxy Route

- [ ] T061 [US2] Create `src/web-form/app/api/tickets/[id]/route.ts` — `GET` handler: `const { id } = await params`; `fetch(\`${process.env.FASTAPI_URL}/support/ticket/${id}\`)`; pass through status + body; on network error → 503
  - **File**: `src/web-form/app/api/tickets/[id]/route.ts` (NEW)
  - **Acceptance**: File exports `GET` function; valid ticket ID → proxied 200 with full ticket dict; unknown ID → proxied 404; network failure → 503; `export const dynamic = 'force-dynamic'`
  - **Depends on**: T019, T049
  - **Test needed**: No
  - **HIGH RISK**: No

### 4B — Ticket Status Page ⚠️ HIGH RISK

- [ ] T062 [US2] Create `src/web-form/app/ticket/[id]/page.tsx` — Server Component; `generateMetadata({ params }: { params: Promise<{ id: string }> })`: await params, fetch ticket by ID, return `title: "Ticket ${id} | NexaFlow Support"`, `description: "Track your support ticket status"`; if ticket not found call `notFound()` from `next/navigation`
  - **File**: `src/web-form/app/ticket/[id]/page.tsx` (NEW)
  - **Acceptance**: `export async function generateMetadata` present; `params` awaited (Next.js 15 pattern); valid ticket ID → correct `<title>` in `<head>`; invalid ticket ID → `notFound()` called → not-found.tsx renders
  - **Depends on**: T061, T021
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T063 [US2] Implement initial server-side data fetch in `src/web-form/app/ticket/[id]/page.tsx`: fetch `\`${process.env.FASTAPI_URL}/support/ticket/${params.id}\``; parse JSON; pass as `initialData` prop to `<TicketStatus initialData={ticket} ticketId={params.id} />`; if 404 call `notFound()`
  - **File**: `src/web-form/app/ticket/[id]/page.tsx` (UPDATE)
  - **Acceptance**: Initial data passed as prop (avoids loading flash on first render); `notFound()` called for 404 before any client hydration; `<TicketStatus>` receives typed `TicketData` prop
  - **Depends on**: T062
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T064 [US2] Create `src/web-form/app/ticket/[id]/TicketStatus.tsx` — Client Component (`'use client'`); `useState<TicketData>(initialData)` for ticket; `useState(false)` for `loading`
  - **File**: `src/web-form/app/ticket/[id]/TicketStatus.tsx` (NEW)
  - **Acceptance**: `'use client'` directive present; `initialData` prop typed as `TicketData`; state initialized from prop (no undefined flash); no `useEffect` yet (added in T065)
  - **Depends on**: T021
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T065 [US2] ⚠️ HIGH RISK — Subtask A: Add `useEffect` polling in `TicketStatus.tsx`: `useEffect(() => { const id = setInterval(fetchTicket, 5000); return () => clearInterval(id); }, [ticket.status])` — `fetchTicket` calls `GET /api/tickets/${ticketId}` and calls `setTicket(json)` on success
  - **File**: `src/web-form/app/ticket/[id]/TicketStatus.tsx` (UPDATE)
  - **Acceptance**: `setInterval` fires every 5000ms; dependency array includes `ticket.status`; Network tab shows GET `/api/tickets/[id]` requests every ~5 seconds; status badge updates when server status changes without full page reload
  - **Depends on**: T064, T061
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T066 [US2] ⚠️ HIGH RISK — Subtask B: Add cleanup on unmount in `TicketStatus.tsx` — `useEffect` cleanup function `return () => clearInterval(intervalId)` must be called even if component unmounts mid-poll
  - **File**: `src/web-form/app/ticket/[id]/TicketStatus.tsx` (UPDATE)
  - **Acceptance**: Navigating away from `/ticket/[id]` stops the interval; browser console shows no "Warning: Can't perform a React state update on an unmounted component" message; interval ID captured in closure and cleared in cleanup function
  - **Depends on**: T065
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T067 [US2] ⚠️ HIGH RISK — Subtask C: Stop polling when status is terminal in `TicketStatus.tsx` — inside `fetchTicket` after `setTicket(json)`: `if (json.status === 'resolved' || json.status === 'escalated') clearInterval(intervalId)` — also guard at interval start: if `ticket.status` is already terminal, don't start interval
  - **File**: `src/web-form/app/ticket/[id]/TicketStatus.tsx` (UPDATE)
  - **Acceptance**: After status becomes "resolved": no further GET `/api/tickets/[id]` requests in Network tab; console logs no interval errors; already-resolved ticket on page load starts no interval at all
  - **Depends on**: T066
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T068 [US2] ⚠️ HIGH RISK — Subtask D: Add typing indicator in `TicketStatus.tsx` — when `ticket.status === 'open' || ticket.status === 'in_progress'` render: `<div className="flex items-center gap-2 text-slate-400">"AI is analyzing your ticket..." <span className="flex gap-1">{[0,1,2].map(i => <span key={i} className="h-1.5 w-1.5 rounded-full bg-blue-400 animate-bounce" style={{ animationDelay: \`${i * 0.2}s\` }} />)}</span></div>`
  - **File**: `src/web-form/app/ticket/[id]/TicketStatus.tsx` (UPDATE)
  - **Acceptance**: Typing indicator visible when status is open or in_progress; 3 dots bounce with staggered animation (0s, 0.2s, 0.4s delay); indicator hidden when status is resolved or escalated; no layout shift when indicator appears/disappears
  - **Depends on**: T067
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T069 [US2] ⚠️ HIGH RISK — Subtask E: Add skeleton loader on initial load in `TicketStatus.tsx` — use `initialData` prop to skip skeleton on SSR (data already loaded); if `initialData` is null/undefined show `<TicketStatusSkeleton />` until first fetch resolves
  - **File**: `src/web-form/app/ticket/[id]/TicketStatus.tsx` (UPDATE)
  - **Acceptance**: When accessing page with valid ID from server-side data → no skeleton (immediate render); if somehow `initialData` is missing → skeleton shows; skeleton has correct dimensions matching real content layout (uses `TicketStatusSkeleton` from T026)
  - **Depends on**: T026, T064
  - **Test needed**: No
  - **HIGH RISK**: Yes

- [ ] T070 [US2] Add full ticket display to `TicketStatus.tsx`: Ticket ID in `font-mono text-lg`; `<StatusBadge status={ticket.status} />`; Category and Priority as `<Badge>` pills; Created time formatted as `"Apr 5, 2026 at 10:30 AM PKT"` using `Intl.DateTimeFormat`; original message in `<pre className="whitespace-pre-wrap font-sans bg-slate-800 p-4 rounded">` box
  - **File**: `src/web-form/app/ticket/[id]/TicketStatus.tsx` (UPDATE)
  - **Acceptance**: All 6 data fields render; timestamp shows PKT timezone; monospace ticket ID; message wraps correctly (no horizontal overflow); `<StatusBadge>` shows correct color per status
  - **Depends on**: T025, T068
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T071 [US2] ⚠️ HIGH RISK — Subtask F: Create `src/web-form/app/ticket/[id]/not-found.tsx` — "Ticket not found" h1 heading, "The ticket you're looking for doesn't exist or has been removed." text, `<Link href="/support">Submit a new ticket →</Link>` button
  - **File**: `src/web-form/app/ticket/[id]/not-found.tsx` (NEW)
  - **Acceptance**: Visiting `/ticket/invalid-id-that-does-not-exist` renders this component (not a crash or blank page); Link navigates to `/support`; no `'use client'` required (Server Component); heading + description visible
  - **Depends on**: T062
  - **Test needed**: No
  - **HIGH RISK**: Yes

**Checkpoint Phase 4**: Navigate to `/ticket/[id]` with valid/invalid IDs. Confirm skeleton → details → polling → typing indicator → not-found all work.

---

## Phase 5: User Story 3 — Support Manager Reviews Dashboard (Priority: P3)

**Goal**: `/dashboard` displays 4 metric cards + recent tickets table + channel breakdown with 30-second auto-refresh.

**Independent Test**: Navigate to `/dashboard`. Assert: (a) 4 metric cards render (Total, Open, Resolved, Escalation Rate); (b) table shows ≤10 recent tickets with status badges; (c) channel breakdown shows Email / WhatsApp / Web Form counts; (d) data refreshes automatically after 30 seconds.

### 5A — Metrics Proxy Route

- [ ] T072 [US3] Create `src/web-form/app/api/metrics/route.ts` — `GET` handler: `fetch(\`${process.env.FASTAPI_URL}/metrics/summary\`)`; pass through status + body; set `Cache-Control: no-store` header; on network error → 503
  - **File**: `src/web-form/app/api/metrics/route.ts` (NEW)
  - **Acceptance**: File exports `GET` function; `Cache-Control: no-store` set via `NextResponse` headers; `export const dynamic = 'force-dynamic'`; FastAPI 200 → proxied 200 with full metrics dict; network failure → 503
  - **Depends on**: T019, T049
  - **Test needed**: No
  - **HIGH RISK**: No

### 5B — Dashboard Page

- [ ] T073 [US3] Create `src/web-form/app/dashboard/page.tsx` — Server Component; static metadata: `title: "Support Dashboard | NexaFlow"`, `description: "Real-time support metrics"`, `og:title`, `og:description`; initial server-side fetch of metrics → pass as `initialMetrics` to `<DashboardContent>`
  - **File**: `src/web-form/app/dashboard/page.tsx` (NEW)
  - **Acceptance**: `export const metadata`; no `'use client'`; `<DashboardContent initialMetrics={metrics} />` rendered; page title correct in browser tab
  - **Depends on**: T072, T021
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T074 [US3] Create `src/web-form/app/dashboard/DashboardContent.tsx` — Client Component (`'use client'`); `useState<MetricsSummary>(initialMetrics)` for metrics; `useEffect` with `setInterval(refreshMetrics, 30000)`; `refreshMetrics` calls `GET /api/metrics`, calls `setMetrics(json)` on success; cleanup `clearInterval` on unmount
  - **File**: `src/web-form/app/dashboard/DashboardContent.tsx` (NEW)
  - **Acceptance**: `'use client'` present; interval fires every 30s; cleanup prevents memory leak; metric cards update without full page reload when interval fires
  - **Depends on**: T073
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T075 [US3] Add 4 metric cards to `DashboardContent.tsx` using shadcn `<Card>`: Total Tickets (Lucide `Ticket` icon), Open Tickets (Lucide `AlertCircle` icon), Resolved Tickets (Lucide `CheckCircle2` icon), Escalation Rate — `\`${metrics.escalation_rate}%\`` (Lucide `ArrowUpRight` icon); `grid grid-cols-2 md:grid-cols-4 gap-4`
  - **File**: `src/web-form/app/dashboard/DashboardContent.tsx` (UPDATE)
  - **Acceptance**: All 4 cards render with correct values from `metrics`; Escalation Rate shows `%` suffix; icons visible; 2-column mobile grid, 4-column desktop grid
  - **Depends on**: T074
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T076 [US3] Add recent tickets table to `DashboardContent.tsx` using shadcn `<Table>`: columns — Ticket ID (`font-mono`), Channel, Category, Priority, Status (`<StatusBadge>`), Time (relative — "2 hours ago" via `Intl.RelativeTimeFormat`); map `metrics.recent_tickets`; on mobile hide Channel and Category columns via `hidden md:table-cell`
  - **File**: `src/web-form/app/dashboard/DashboardContent.tsx` (UPDATE)
  - **Acceptance**: Table renders ≤10 rows; `<StatusBadge>` in Status column; Ticket ID is monospace; mobile shows only Ticket ID + Status + Time (3 columns); no horizontal scroll on 375px viewport
  - **Depends on**: T075, T025
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T077 [US3] Add channel breakdown section to `DashboardContent.tsx`: 3 small `<Card>` pills for Email, WhatsApp, Web Form with counts from `metrics.channels`; channel icons: `<Mail>`, `<MessageSquare>`, `<Globe>` (Lucide); `flex gap-4 flex-wrap`
  - **File**: `src/web-form/app/dashboard/DashboardContent.tsx` (UPDATE)
  - **Acceptance**: 3 channel cards render; counts come from `metrics.channels.email`, `metrics.channels.whatsapp`, `metrics.channels.web_form`; wrap correctly on mobile; no crash if channel count is 0
  - **Depends on**: T076
  - **Test needed**: No
  - **HIGH RISK**: No

**Checkpoint Phase 5**: Navigate to `/dashboard`. Confirm 4 cards + table + channel breakdown render. Wait 30 seconds for auto-refresh.

---

## Phase 6: User Story 4 — Visitor Lands on Homepage (Priority: P4)

**Goal**: `/` landing page with hero section, 3 animated feature cards, "Get Support" CTA.

**Independent Test**: Navigate to `/`. Assert: (a) NexaFlow logo and tagline visible; (b) 3 feature cards present; (c) "Get Support" CTA links to `/support`; (d) Framer Motion entrance animations complete within 600ms.

- [ ] T078 [US4] Create `src/web-form/app/page.tsx` — Server Component; static metadata: `title: "NexaFlow | Intelligent Customer Support"`, `description: "AI-powered 24/7 customer support for NexaFlow SaaS platform"`, `og:type: "website"`, `og:title`, `og:description`
  - **File**: `src/web-form/app/page.tsx` (UPDATE — replace scaffold default)
  - **Acceptance**: `export const metadata`; no `'use client'`; OG tags in rendered HTML `<head>`; browser tab shows "NexaFlow | Intelligent Customer Support"
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T079 [US4] Build hero section in `src/web-form/app/page.tsx`: `<FadeIn>` wrapper around centered `<NexaFlowLogo size="lg" />` (80px variant), `<h1>"Intelligent Customer Success Platform"</h1>`, `<p>` subtext, `<Button asChild><Link href="/support">Get Support</Link></Button>`; `min-h-[60vh] flex flex-col items-center justify-center`; background `bg-[#0F172A]`
  - **File**: `src/web-form/app/page.tsx` (UPDATE)
  - **Acceptance**: Hero renders with large logo; tagline text matches exactly "Intelligent Customer Success Platform"; CTA button links to `/support`; `<FadeIn>` animation plays on load; background is dark navy
  - **Depends on**: T027, T022, T078
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T080 [US4] Build feature cards section in `src/web-form/app/page.tsx`: 3 `<SlideUp delay={0.1 * i}>` wrapped shadcn `<Card>` components — "24/7 AI Support" (Lucide `Clock` icon), "Multi-Channel" (Lucide `Globe` icon), "Smart Routing" (Lucide `Zap` icon); `grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto`; card style: `bg-slate-800/50 border-slate-700`
  - **File**: `src/web-form/app/page.tsx` (UPDATE)
  - **Acceptance**: All 3 cards render with correct labels and icons; `SlideUp` animations staggered by 0.1s; single column on mobile, 3-column on md+; cards use dark slate styling
  - **Depends on**: T028, T080
  - **Test needed**: No
  - **HIGH RISK**: No

**Checkpoint Phase 6**: Navigate to `/`. Confirm hero + feature cards + animations + CTA work.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Metadata completeness, error boundaries, accessibility, mobile responsiveness, Lighthouse audit.

### 7A — generateMetadata on All Pages [P]

- [ ] T081 [P] Verify `/` metadata complete in `src/web-form/app/page.tsx`: `og:title: "NexaFlow | Intelligent Customer Support"`, `og:description`, `og:type: "website"` — already added in T078; confirm no missing OG tags
  - **File**: `src/web-form/app/page.tsx` (VERIFY)
  - **Acceptance**: Browser DevTools shows `og:title`, `og:description`, `og:type` in `<head>`
  - **Depends on**: T078
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T082 [P] Verify `/support` metadata in `src/web-form/app/support/page.tsx`: `og:title: "Submit a Support Ticket | NexaFlow"`, `og:description`, `og:type: "website"` — already added in T051; confirm all tags present
  - **File**: `src/web-form/app/support/page.tsx` (VERIFY)
  - **Acceptance**: `og:title`, `og:description`, `og:type` present in rendered HTML `<head>` for `/support`
  - **Depends on**: T051
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T083 [P] Verify `/ticket/[id]` dynamic metadata in `src/web-form/app/ticket/[id]/page.tsx`: `generateMetadata` returns `title: "Ticket ${id} | NexaFlow Support"`; falls back gracefully to `"Ticket | NexaFlow Support"` if ticket fetch fails; `og:title` and `og:description` also set dynamically
  - **File**: `src/web-form/app/ticket/[id]/page.tsx` (UPDATE if fallback missing)
  - **Acceptance**: Valid ticket ID → title shows actual ID in tab; 404 ticket → fallback title used (not error); OG tags present
  - **Depends on**: T062
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T084 [P] Verify `/dashboard` metadata in `src/web-form/app/dashboard/page.tsx`: `title: "Support Dashboard | NexaFlow"`, `og:title`, `og:description` — already added in T073; confirm all tags
  - **File**: `src/web-form/app/dashboard/page.tsx` (VERIFY)
  - **Acceptance**: Browser tab reads "Support Dashboard | NexaFlow"; OG tags in `<head>`
  - **Depends on**: T073
  - **Test needed**: No
  - **HIGH RISK**: No

### 7B — Error Boundaries + Not-Found Handlers

- [ ] T085 Create `src/web-form/app/error.tsx` — root error boundary: Client Component (`'use client'`); props `{ error: Error, reset: () => void }`; renders "Something went wrong" heading + error message in dev + "Try again" button calling `reset()`
  - **File**: `src/web-form/app/error.tsx` (NEW)
  - **Acceptance**: `'use client'` present (required by Next.js); `reset()` called on button click; re-renders page segment on retry; no raw stack trace shown to user in production build
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T086 Create `src/web-form/app/not-found.tsx` — root 404: "Page not found (404)" heading + "The page you're looking for doesn't exist." + `<Link href="/">Return to homepage</Link>` button
  - **File**: `src/web-form/app/not-found.tsx` (NEW)
  - **Acceptance**: Server Component; Link navigates to `/`; renders for any unknown route not handled by a route segment's own `not-found.tsx`
  - **Depends on**: T007
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T087 Create `src/web-form/app/support/error.tsx` and `src/web-form/app/support/not-found.tsx` — both match root patterns; support error links back to support form; support not-found shows "Support page unavailable" + link to `/`
  - **File**: `src/web-form/app/support/error.tsx` (NEW), `src/web-form/app/support/not-found.tsx` (NEW)
  - **Acceptance**: Both files exist; `error.tsx` has `'use client'`; `not-found.tsx` is Server Component; no duplicate of root patterns needed — just route-specific messaging
  - **Depends on**: T085, T086
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T088 Verify `src/web-form/app/ticket/[id]/not-found.tsx` is complete (created in T071) and create `src/web-form/app/ticket/[id]/error.tsx` — `'use client'`; "Error loading ticket" + reset button + link to `/support`
  - **File**: `src/web-form/app/ticket/[id]/error.tsx` (NEW)
  - **Acceptance**: `'use client'` on error.tsx; `not-found.tsx` from T071 confirmed present; error boundary renders "Error loading ticket" with reset and back-to-support link
  - **Depends on**: T071
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T089 Create `src/web-form/app/dashboard/error.tsx` and `src/web-form/app/dashboard/not-found.tsx` — dashboard error shows "Dashboard unavailable" + reset button; not-found shows "Dashboard not found" + link to `/`
  - **File**: `src/web-form/app/dashboard/error.tsx` (NEW), `src/web-form/app/dashboard/not-found.tsx` (NEW)
  - **Acceptance**: Both files exist; `error.tsx` has `'use client'`; previously loaded metrics data not destroyed on reset attempt (handled by Next.js segment error boundary scope)
  - **Depends on**: T085
  - **Test needed**: No
  - **HIGH RISK**: No

### 7C — Accessibility Audit

- [ ] T090 Audit all 6 form fields in `SupportForm.tsx`: confirm each `<FormField>` → `<FormLabel>` → `<FormControl>` → `<FormMessage>` chain is correct; `<FormMessage>` in shadcn renders with `role="alert"` automatically; add explicit `aria-describedby` to any input missing it
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE if needed)
  - **Acceptance**: Each input has `aria-describedby` referencing its error message element; screen reader reads error when field fails; no `id` collisions between fields
  - **Depends on**: T060
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T091 Test keyboard-only navigation of support form: Tab to each field in order (Name → Email → Subject → Category → Priority → Message → Submit); Enter submits; Escape dismisses toast; no focus trap
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE if fixes needed)
  - **Acceptance**: All fields reachable via Tab; Submit reachable without mouse; Enter on Submit triggers form submission; toast dismissible with Escape; no focus trap — Shift+Tab reverses through fields
  - **Depends on**: T060
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T092 Verify focus rings on all interactive elements: buttons, inputs, select triggers, links must all show `focus-visible:ring-2 focus-visible:ring-[#3B82F6]` or equivalent Tailwind ring class
  - **File**: Multiple — `src/web-form/app/support/SupportForm.tsx`, `src/web-form/components/Navbar.tsx`, `src/web-form/components/ThemeToggle.tsx` (UPDATE if missing)
  - **Acceptance**: Focus ring visible on Tab to each interactive element; ring uses NexaFlow blue or shadcn default ring; no element has `outline-none` without a replacement focus indicator
  - **Depends on**: T091
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T093 Verify `aria-label` on `ThemeToggle` button in `src/web-form/components/ThemeToggle.tsx`: `aria-label="Switch to dark mode"` or `"Switch to light mode"` (context-appropriate, updates with theme)
  - **File**: `src/web-form/components/ThemeToggle.tsx` (UPDATE if missing)
  - **Acceptance**: `aria-label` changes between "Switch to dark mode" and "Switch to light mode" based on current theme; screen reader announces correct action
  - **Depends on**: T024
  - **Test needed**: No
  - **HIGH RISK**: No

### 7D — Mobile Responsive Check

- [ ] T094 Test all 4 pages (`/`, `/support`, `/ticket/[id]`, `/dashboard`) at 375px, 768px, 1280px viewport widths using Chrome DevTools; record any horizontal overflow or broken layouts
  - **File**: N/A (verification step — fix any issues found in subsequent tasks)
  - **Acceptance**: No `overflow-x: auto` or horizontal scrollbar at 375px on any page; all content visible without horizontal scrolling
  - **Depends on**: T080, T060, T070, T077
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T095 Fix support form layout for mobile in `SupportForm.tsx`: Category and Priority selects in `grid grid-cols-1 sm:grid-cols-2 gap-4` (single column mobile, side-by-side sm+); form card full-width on mobile with `p-4` padding
  - **File**: `src/web-form/app/support/SupportForm.tsx` (UPDATE if needed)
  - **Acceptance**: At 375px Category and Priority stack vertically; at 640px+ they sit side by side; no horizontal overflow; card has comfortable padding on mobile
  - **Depends on**: T094
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T096 Fix dashboard table for mobile in `DashboardContent.tsx`: Channel and Category columns use `hidden md:table-cell` so mobile shows only Ticket ID + Status + Time
  - **File**: `src/web-form/app/dashboard/DashboardContent.tsx` (UPDATE if not already done in T076)
  - **Acceptance**: At 375px table shows 3 columns (ID, Status, Time); at 768px+ all 6 columns visible; no horizontal scroll
  - **Depends on**: T094
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T097 Verify all touch targets ≥ 44×44px: submit button, category/priority selects, nav links, ThemeToggle button; add `min-h-[44px]` or `py-3` if any target is smaller
  - **File**: `src/web-form/app/support/SupportForm.tsx`, `src/web-form/components/Navbar.tsx`, `src/web-form/components/ThemeToggle.tsx` (UPDATE if needed)
  - **Acceptance**: Chrome DevTools "Tap target size" audit shows no violations; submit button is at least 44px tall; ThemeToggle button is at least 44×44px
  - **Depends on**: T094
  - **Test needed**: No
  - **HIGH RISK**: No

### 7E — Lighthouse Documentation

- [ ] T098 Run Lighthouse on all 4 pages in Chrome DevTools (Incognito mode, mobile preset): record Performance, Accessibility, Best Practices, SEO scores; target ≥90 on all 4 categories for all 4 pages
  - **File**: N/A (scores to be recorded in T099)
  - **Acceptance**: Lighthouse runs to completion without timeout; scores recorded; any category below 90 triggers a fix task
  - **Depends on**: T097
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T099 Apply Lighthouse fixes if any score is below 90: common fixes — add `next/image` if any `<img>` tags used; ensure all pages have meta description (T082-T084 should cover this); fix any missing labels caught by accessibility audit
  - **File**: Any page with score < 90 (UPDATE as needed)
  - **Acceptance**: After fixes, all 4 pages achieve ≥90 on Performance, Accessibility, Best Practices, SEO
  - **Depends on**: T098
  - **Test needed**: No
  - **HIGH RISK**: No

- [ ] T100 Document final Lighthouse scores in `src/web-form/README.md`: one table with 4 pages × 4 Lighthouse categories; include last-run date (2026-04-05)
  - **File**: `src/web-form/README.md` (NEW)
  - **Acceptance**: Markdown table with columns: Page, Performance, Accessibility, Best Practices, SEO; all scores ≥90; date noted
  - **Depends on**: T099
  - **Test needed**: No
  - **HIGH RISK**: No

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (T001–T004): No dependencies — start immediately
- **Phase 2** (T005–T036): T005–T006 (Python queries) depend on T002; T007–T035 (Next.js) depend on nothing — run in parallel with Phase 1; **T036 (gate) blocks all Phases 3–7**
- **Phase 3** (T037–T060): Depends on T036 gate passing; all Phase 2 tasks complete
- **Phase 4** (T061–T071): Depends on Phase 3 complete (uses ticket status data from US1 submissions)
- **Phase 5** (T072–T077): Depends on Phase 1 complete (metrics queries); can start in parallel with Phase 4
- **Phase 6** (T078–T080): Can start after Phase 2 complete (scaffold + components ready); runs in parallel with Phases 4–5
- **Phase 7** (T081–T100): Depends on all previous phases complete

### Parallel Opportunities

| Group | Tasks | Can run in parallel |
|-------|-------|---------------------|
| Python queries + Next.js scaffold | T005–T006 + T007–T035 | Yes — different stacks |
| Shared components (after T009) | T021–T028 | Yes — different files |
| Proxy routes (after T049) | T050, T061, T072 | Yes — different files |
| Metadata verification | T081–T084 | Yes — different pages |
| Error boundaries | T085–T089 | Yes — different route segments |

### HIGH RISK Task Summary

| Task | Component | Acceptance Criteria |
|------|-----------|---------------------|
| T007 (B2-T1) | Next.js scaffold | `src/web-form/app/layout.tsx` exists; `npm run dev` on port 3001 no errors |
| T010 (B2-T1 verify) | Dev server verify | HTTP 200 on localhost:3001; no console errors |
| T036 | Python regression gate | `pytest` shows exactly `142 passed, 0 failed` |
| T038–T044 (B1-T3) | WebFormHandler pipeline | Any DB step fails → return None; Kafka fail does NOT raise; ticket ID only returned on full success |
| T052 (B5-T2-A) | Zod schema | 6 fields; invalid email, short message, unknown category all raise ValidationError |
| T053 (B5-T2-B) | RHF useForm | `zodResolver` wired; defaultValues set; validation on submit only |
| T054 (B5-T2-C) | Form UI | Empty submit shows errors on all 6 fields; no network request made |
| T056 (B5-T2-D) | Submit handler | `setSubmitting(false)` on error; field values preserved; confetti on success |
| T057 (B5-T2-E) | Confetti | Fires exactly once per submission; NexaFlow blue colors |
| T059 (B5-T2-F) | Framer Motion | Animations complete in 600ms; `prefers-reduced-motion` skips animation |
| T065 (B5-T3-A) | Polling setup | Network tab shows requests every ~5 seconds |
| T066 (B5-T3-B) | Cleanup | No memory leak warnings on unmount; clearInterval in useEffect cleanup |
| T067 (B5-T3-C) | Stop polling | No further requests after status=resolved/escalated |
| T068 (B5-T3-D) | Typing indicator | Visible for open/in_progress; hidden for resolved/escalated |
| T069 (B5-T3-E) | Skeleton | No skeleton flash when initialData available from SSR |
| T071 (B5-T3-F) | not-found | Invalid ticket ID shows not-found UI; no crash |

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 (T001–T004)
2. Complete Phase 2 (T005–T036) — Python parallel with Next.js
3. **Pass T036 gate** — 142 tests green
4. Complete Phase 3 (T037–T060) — form submission end-to-end
5. **STOP and VALIDATE**: Submit a ticket via the form; confirm DB record + Kafka publish + confetti + redirect
6. Demo US1 if ready

### Incremental Delivery

1. Phase 1 + Phase 2 → Foundation ready
2. Phase 3 → US1 (form submission) → Demo: submit a ticket
3. Phase 4 → US2 (ticket status + polling) → Demo: track your ticket
4. Phase 5 → US3 (dashboard) → Demo: ops metrics view
5. Phase 6 → US4 (landing page) → Demo: full user journey from landing to resolution
6. Phase 7 → Polish → Lighthouse ≥90, full accessibility, mobile check

---

## Notes

- `[P]` = different files, no dependencies — safe to implement in parallel
- `[US1]–[US4]` label maps task to user story for traceability
- **T036 is a hard gate** — never skip; if it fails, fix regression before touching frontend
- HIGH RISK tasks require extra attention and manual verification of acceptance criteria
- Commit after each logical group; do NOT push until `/sp.implement` is complete
- `FASTAPI_URL` is a server-side env var only — never prefix with `NEXT_PUBLIC_`
- `received_at` in all Kafka messages MUST use `datetime.now(ZoneInfo("Asia/Karachi"))` — never infer date
