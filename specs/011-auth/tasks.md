# Tasks: NextAuth.js v5 Auth + RBAC

**Feature**: `011-auth` | **Branch**: `011-auth` | **Date**: 2026-04-09  
**Input**: `specs/011-auth/plan.md` (8 blocks) + `spec.md` (5 user stories)  
**Prerequisites**: plan.md ✅ | spec.md ✅ | data-model.md ✅ | contracts/ ✅  
**Current tests**: 166 passing — must remain green throughout  
**Implementation order** (from plan.md): B1 → B2 → B8 → B3 → B4 → B5 → B6 → B7

---

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no blocking dependencies)
- **[US#]**: User story this task belongs to (Phase 3+ only)
- **⚠️ HIGH RISK**: Annotated in description — special care required
- Sub-bullets per task: **File** | **Acceptance** | **Depends** | **Test** | **Risk**

---

## Phase 1: Setup

**Purpose**: Verify environment, generate secrets, confirm structure before any code is written

- [X] T001 Verify src/web-form/ installed packages and confirm next-auth is NOT yet installed
  - **File**: `src/web-form/package.json` (read-only verify)
  - **Acceptance**: Output of `cat src/web-form/package.json` confirms next-auth absent; bcryptjs absent; @neondatabase/serverless absent
  - **Depends**: nothing
  - **Test**: no
  - **Risk**: LOW

- [X] T002 Generate AUTH_SECRET and add to src/web-form/.env.local and src/web-form/.env.example
  - **File**: `src/web-form/.env.local` (create/update) | `src/web-form/.env.example` (create/update)
  - **Acceptance**: `.env.local` contains `AUTH_SECRET=<32-byte base64 string>`; `.env.example` contains `AUTH_SECRET=` placeholder; neither file is git-tracked (verify `.gitignore` covers `.env.local`)
  - **Depends**: T001
  - **Test**: no
  - **Risk**: LOW
  - **Note**: Generate with `openssl rand -base64 32`; also ensure `DATABASE_URL` and `FASTAPI_URL=https://psqasim-crm-digital-fte-api.hf.space` are present

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Database migration + NextAuth core setup + seed script. ALL must complete before any user story work.

**⚠️ CRITICAL**: No user story work can begin until Phase 2 is complete. B2 is HIGH RISK — 4 subtasks each require `npm run build` validation.

### B1: Database Migration (LOW RISK)

- [X] T003 [P] Create production/database/migrations/004_add_users_table.sql
  - **File**: `production/database/migrations/004_add_users_table.sql` (CREATE)
  - **Acceptance**: File contains `CREATE TABLE IF NOT EXISTS users` with columns: `id UUID PK DEFAULT gen_random_uuid()`, `name VARCHAR(255) NOT NULL`, `email VARCHAR(255) UNIQUE NOT NULL`, `hashed_password TEXT NOT NULL`, `role VARCHAR(50) NOT NULL DEFAULT 'agent' CHECK (role IN ('admin','agent'))`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`; plus `CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email)`; migration is idempotent (IF NOT EXISTS guards)
  - **Depends**: T002
  - **Test**: no (manual: `psql $DATABASE_URL -f 004_add_users_table.sql` must exit 0)
  - **Risk**: LOW

- [X] T004 [P] Add get_user_by_email() and create_user() async functions to production/database/queries.py
  - **File**: `production/database/queries.py` (UPDATE — append 2 new async functions)
  - **Acceptance**: `get_user_by_email(email: str) -> dict | None` — SELECT id, name, email, hashed_password, role FROM users WHERE email=$1 (lowercased); `create_user(name, email, hashed_password, role) -> dict` — INSERT RETURNING id, name, email, role, created_at; both use existing asyncpg `pool.acquire()` pattern already in file
  - **Depends**: T002 (can run parallel with T003)
  - **Test**: no
  - **Risk**: LOW

### B2: NextAuth.js Setup (⚠️ HIGH RISK — 6 subtasks)

**Risk**: next-auth@beta v5 API differs from v4; peer dep conflicts with Next.js 16 possible; TypeScript types may not resolve. Run `npm run build` after T005, T009, T010.

- [X] T005 Install next-auth@beta bcryptjs @types/bcryptjs @neondatabase/serverless in src/web-form/ — ⚠️ HIGH RISK
  - **File**: `src/web-form/package.json` + `src/web-form/package-lock.json` (UPDATE via npm install)
  - **Command**: `cd src/web-form && npm install next-auth@beta bcryptjs @types/bcryptjs @neondatabase/serverless`
  - **Acceptance**: `npm install` exits 0 with no unresolved peer dependency warnings; `package.json` shows `"next-auth": "^5.x.x-beta.*"`; `npm run build` still passes (166 tests still green)
  - **Depends**: T003, T004
  - **Test**: yes — `npm run build` must pass after install
  - **Risk**: HIGH — if peer dep conflicts arise, pin to specific beta version (e.g. `next-auth@5.0.0-beta.25`)

- [X] T006 Create src/web-form/lib/db.ts with Neon serverless client and DB query functions
  - **File**: `src/web-form/lib/db.ts` (CREATE)
  - **Acceptance**: Exports: `DbUser` interface (id, name, email, hashed_password, role, created_at); `getUserByEmail(email: string): Promise<DbUser | null>` — uses tagged template sql\`SELECT...\`; `createUser(name, email, hashedPassword, role): Promise<Omit<DbUser, 'hashed_password'>>` — INSERT RETURNING; uses `neon(process.env.DATABASE_URL!)` from `@neondatabase/serverless`; email lowercased in both functions; `npx tsc --noEmit` passes
  - **Depends**: T005
  - **Test**: no
  - **Risk**: LOW

- [X] T007 Create src/web-form/auth.config.ts with Credentials provider — ⚠️ HIGH RISK (Edge-safe)
  - **File**: `src/web-form/auth.config.ts` (CREATE)
  - **Acceptance**: Exports `authConfig` (type `NextAuthConfig`); contains only `providers: [Credentials({ ... })]`; Credentials provider has `name`, `credentials` (email + password fields), and `authorize` async function that: (1) calls `getUserByEmail(credentials.email)`, (2) calls `bcrypt.compare(credentials.password, user.hashed_password)`, (3) returns `{ id: user.id, email: user.email, name: user.name, role: user.role }` on success or `null` on failure; NO bcrypt import at module level (import inside authorize or use dynamic import to stay Edge-compatible); `npx tsc --noEmit` passes
  - **Depends**: T006
  - **Test**: yes — `npm run build` must pass
  - **Risk**: HIGH — bcrypt import in Edge context must be verified; if Edge errors occur, add `import 'server-only'` guard

- [X] T008 Create src/web-form/auth.ts with full NextAuth config — ⚠️ HIGH RISK
  - **File**: `src/web-form/auth.ts` (CREATE)
  - **Acceptance**: Imports `authConfig` from `./auth.config`; calls `NextAuth({ ...authConfig, session: { strategy: 'jwt' }, pages: { signIn: '/login' }, callbacks: { async jwt({ token, user }) { if (user) { token.role = user.role; token.id = user.id } return token }, async session({ session, token }) { session.user.role = token.role as string; session.user.id = token.id as string; return session } } })`; exports named: `handlers`, `auth`, `signIn`, `signOut`; `npx tsc --noEmit` passes; `auth()` returns null when called without a session
  - **Depends**: T007
  - **Test**: yes — `npm run build` must pass
  - **Risk**: HIGH — v5 export API differs from v4; verify exports match NextAuth v5 docs pattern

- [X] T009 Create src/web-form/types/next-auth.d.ts with Session/JWT type augmentation — ⚠️ HIGH RISK
  - **File**: `src/web-form/types/next-auth.d.ts` (CREATE)
  - **Acceptance**: Augments `next-auth` module to add `role: string` and `id: string` to `Session["user"]`; augments `next-auth/jwt` to add `role: string` and `id: string` to `JWT`; augments `next-auth` `User` interface to add `role: string`; no TypeScript errors (`npx tsc --noEmit` clean); file is in `src/web-form/types/` directory and picked up by `tsconfig.json`
  - **Depends**: T008
  - **Test**: yes — `npx tsc --noEmit` must pass with zero type errors on auth.ts imports
  - **Risk**: HIGH — if tsconfig doesn't include `types/` directory, add `"typeRoots"` or `"include"` entry to `src/web-form/tsconfig.json`

- [X] T010 Create src/web-form/app/api/auth/[...nextauth]/route.ts with NextAuth GET+POST handler
  - **File**: `src/web-form/app/api/auth/[...nextauth]/route.ts` (CREATE — also create directory)
  - **Acceptance**: Imports `{ handlers }` from `@/auth`; exports `const { GET, POST } = handlers`; no custom logic; `npm run build` passes
  - **Depends**: T009
  - **Test**: no
  - **Risk**: LOW

### B8: Seed Script (validates DB + bcrypt — must run before proxy.ts testing)

- [X] T011 Create src/web-form/scripts/seed.ts — idempotent admin seed script
  - **File**: `src/web-form/scripts/seed.ts` (CREATE — also create `scripts/` directory if absent)
  - **Acceptance**: Uses `neon(process.env.DATABASE_URL!)` from `@neondatabase/serverless`; checks if `admin@nexaflow.com` exists in users table; if absent: hashes `Admin123!` with `bcrypt.hash(password, 12)` and INSERTs `(name='NexaFlow Admin', email='admin@nexaflow.com', role='admin')`; logs `"✅ Admin user created"` on creation; logs `"ℹ️ Admin user already exists — skipping"` on second run; run with `npx tsx src/web-form/scripts/seed.ts`; second run produces no DB changes
  - **Depends**: T010 (needs DATABASE_URL and bcryptjs installed)
  - **Test**: no (manual: run twice, confirm idempotent)
  - **Risk**: LOW

**Checkpoint**: Foundation complete — auth.ts, lib/db.ts, migration, and seed are ready. Manual test: run `npx tsx src/web-form/scripts/seed.ts` and confirm admin user created.

---

## Phase 3: User Story 1 — Internal Staff Login (Priority: P1) 🎯 MVP

**Goal**: Internal staff can navigate to `/login`, enter credentials, and be redirected to their role-appropriate dashboard.

**Independent Test**: Visit `/login` → enter `admin@nexaflow.com / Admin123!` → confirm redirect to `/admin/dashboard`. Visit `/login` → enter wrong password → confirm inline error shown.

### Implementation for US1

- [X] T012 [US1] Create src/web-form/app/login/page.tsx — Server Component wrapper
  - **File**: `src/web-form/app/login/page.tsx` (CREATE — create `app/login/` directory)
  - **Acceptance**: Server Component; calls `auth()` — if session exists redirects to `/admin/dashboard` (admin) or `/dashboard` (agent) using `redirect()`; if no session renders `<LoginForm />`; page title "NexaFlow Login"; background `bg-[#0F172A]`; no "Create Account" or "Forgot Password" links anywhere on the page
  - **Depends**: T010 (auth.ts available), T011 (seed complete — admin credentials exist)
  - **Test**: no
  - **Risk**: LOW

- [X] T013 [US1] Create src/web-form/app/login/LoginForm.tsx — Client Component with form + validation
  - **File**: `src/web-form/app/login/LoginForm.tsx` (CREATE)
  - **Acceptance**: `'use client'` directive; uses `react-hook-form` with `zodResolver`; Zod schema validates: email (required, valid email format), password (required, min 1 char for display purposes — server validates credentials); form submits via Server Action calling `signIn('credentials', { email, password, redirect: false })`; on `error` from signIn: displays inline red text "Invalid email or password" below submit button; on success: `router.push('/admin/dashboard')` for admin or `router.push('/dashboard')` for agent (read role from session via `useSession()` or refetch); shadcn `Input` components; submit button `bg-[#3B82F6] hover:bg-[#2563EB]`; card `bg-slate-800/50 border-slate-700 max-w-sm mx-auto mt-20`
  - **Depends**: T012
  - **Test**: no
  - **Risk**: LOW

**Checkpoint**: US1 complete. Test: `/login` with valid admin creds → redirected to `/admin/dashboard` (which may 404 — that's OK at this stage). Wrong creds → inline error shown.

---

## Phase 4: User Story 2 — Route Protection & Redirect (Priority: P2)

**Goal**: Unauthenticated visitors accessing `/dashboard` or `/admin/*` are redirected to `/login`. Agents accessing `/admin/*` are redirected to `/dashboard`.

**Independent Test**: Open browser in incognito → navigate to `/dashboard` → confirm 302 redirect to `/login`. Navigate to `/admin/dashboard` as agent → confirm redirect to `/dashboard`.

### Implementation for US2

- [X] T014 [US2] Create src/web-form/proxy.ts — ⚠️ HIGH RISK (NOT middleware.ts — Next.js 16 rename)
  - **File**: `src/web-form/proxy.ts` (CREATE — filename is `proxy.ts`, NOT `middleware.ts`)
  - **Acceptance**:
    - File is named exactly `proxy.ts` (verify: `ls src/web-form/proxy.ts` must succeed; `ls src/web-form/middleware.ts` must fail)
    - Imports `{ auth }` from `@/auth` and `{ NextResponse }` from `next/server`
    - Default export: `auth((req) => { ... })` — auth-wrapped function
    - Logic inside: `const isLoggedIn = !!req.auth`; `const path = req.nextUrl.pathname`; if `!isLoggedIn` → `NextResponse.redirect(new URL('/login', req.url))`; if `path.startsWith('/admin')` AND `req.auth?.user?.role !== 'admin'` → `NextResponse.redirect(new URL('/dashboard', req.url))`; otherwise fall through (no return = allow)
    - Exports `config = { matcher: ['/dashboard/:path*', '/admin/:path*'] }`
    - **Manual smoke tests** (run after seed):
      1. GET `/dashboard` with no session cookie → HTTP 302 Location: `/login` ✅
      2. GET `/admin/dashboard` with admin session cookie → HTTP 200 (or 404 if page not yet built — redirect must NOT fire) ✅
      3. GET `/admin/dashboard` with agent session cookie → HTTP 302 Location: `/dashboard` ✅
      4. GET `/` with no session cookie → HTTP 200 (no redirect) ✅
  - **Depends**: T013 (login flow available for manual testing), T011 (seed — credentials for cookie)
  - **Test**: yes (manual smoke tests above — run with curl or browser DevTools network tab)
  - **Risk**: HIGH — if proxy.ts is not recognized by Next.js 16, ALL protected routes will be open with no errors shown; verify by checking that unauthenticated GET `/dashboard` returns 302 NOT 200

**Checkpoint**: US2 complete. All 4 manual smoke tests must pass before continuing.

---

## Phase 5: User Story 3 — Admin User Management (Priority: P3)

**Goal**: Authenticated admin sees all tickets + can create new user accounts from `/admin/dashboard`. Two separate data sources: tickets from FastAPI, user creation via Neon directly.

**Independent Test**: Log in as admin → navigate to `/admin/dashboard` → verify tickets table renders → fill create-user form → submit → confirm success toast → log in as new user → confirm `/dashboard` accessible.

### Implementation for US3

- [X] T015 [P] [US3] Create src/web-form/app/admin/dashboard/page.tsx — Server Component with auth check + FastAPI tickets fetch
  - **File**: `src/web-form/app/admin/dashboard/page.tsx` (CREATE — create `app/admin/dashboard/` directory)
  - **Acceptance**: Server Component; calls `auth()` — if no session or `session.user.role !== 'admin'` calls `redirect('/login')` (belt-and-suspenders beyond proxy); fetches tickets from FastAPI: `fetch(\`${process.env.FASTAPI_URL}/api/tickets\`, { cache: 'no-store' })` — SAME pattern as existing `/dashboard/page.tsx`; passes `tickets` array and `session.user` to `<AdminDashboardContent>`; handles fetch error gracefully (empty array + console.error); page title "Admin Dashboard — NexaFlow"
  - **Depends**: T014 (proxy.ts in place)
  - **Test**: no
  - **Risk**: MEDIUM — uses FastAPI for tickets (existing pattern); if FastAPI is down, show empty state not error page

- [X] T016 [P] [US3] Create src/web-form/app/admin/dashboard/AdminDashboardContent.tsx — Client Component with tickets table + create user form
  - **File**: `src/web-form/app/admin/dashboard/AdminDashboardContent.tsx` (CREATE)
  - **Acceptance**: `'use client'` directive; receives `tickets: Ticket[]` and `user: { name, role }` as props; renders: (1) tickets table with columns: Ticket ID, Channel, Category, Priority, Status, Timestamp — same display as existing dashboard; (2) "Create User" form with fields: Full Name (text), Email (email), Password (password), Role (select: admin | agent); form uses `react-hook-form` + Zod validation (name ≥2 chars, valid email, password ≥8 chars, role required); on submit: POST to `/api/admin/users` with JSON body; on 201: show success toast "User created successfully"; on 409: show inline error "Email already exists"; on 400: show inline validation errors; on 401/403: show "Permission denied" (should not happen given proxy + server guard)
  - **Depends**: T015 (can be written in parallel — different file)
  - **Test**: no
  - **Risk**: MEDIUM — two distinct data sources must not be mixed; tickets come from props (FastAPI via Server Component); user creation POSTs to Next.js API route (not FastAPI)

- [X] T017 [US3] Create src/web-form/app/api/admin/users/route.ts — POST handler (admin-only user creation)
  - **File**: `src/web-form/app/api/admin/users/route.ts` (CREATE — create `app/api/admin/users/` directory)
  - **Acceptance**: `export async function POST(req: Request)` (no GET); step-by-step:
    1. `const session = await auth()` — if null → 401 `{ error: 'Unauthorized' }`
    2. if `session.user.role !== 'admin'` → 403 `{ error: 'Forbidden — admin role required' }`
    3. `const body = await req.json()` + `createUserSchema.safeParse(body)` where schema: `{ name: z.string().min(2).max(255), email: z.string().email(), password: z.string().min(8), role: z.enum(['admin','agent']) }`; if invalid → 400 `{ error: 'Validation failed', details: [...] }`
    4. `const hashedPassword = await bcrypt.hash(result.data.password, 12)`
    5. `const user = await createUser(result.data.name, result.data.email, hashedPassword, result.data.role)` — imports from `@/lib/db`; on success → 201 `{ id, name, email, role, created_at }`
    6. catch: if error message contains 'unique' or 'duplicate' → 409 `{ error: 'A user with this email address already exists' }`; else → 500 `{ error: 'Failed to create user' }`
    - **Security**: role is NEVER read from request body for authorization — only session.user.role is trusted; password plaintext never logged
  - **Depends**: T016
  - **Test**: no (manual: POST to `/api/admin/users` with valid body → 201; with duplicate email → 409; with agent session → 403)
  - **Risk**: MEDIUM — server-side role check is critical security gate; double-verify session.user.role check executes BEFORE any DB operation

**Checkpoint**: US3 complete. Created user can log in at `/login` and access `/dashboard`.

---

## Phase 6: User Story 4 — Agent Dashboard Auth Guard (Priority: P4)

**Goal**: `/dashboard` requires authentication. Session expiry triggers redirect to `/login`. User name + role badge visible in header.

**Independent Test**: Log in as agent → verify `/dashboard` loads with metrics → click Logout → verify redirected to `/login` → verify direct URL access to `/dashboard` redirects back to `/login`.

### Implementation for US4

- [X] T018 [P] [US4] Update src/web-form/app/dashboard/page.tsx — add auth() call and belt-and-suspenders redirect
  - **File**: `src/web-form/app/dashboard/page.tsx` (UPDATE)
  - **Acceptance**: Adds `const session = await auth()` at top of page function; if `!session` → `redirect('/login')`; passes `session.user` to dashboard content component; existing ticket data fetch from FastAPI is UNCHANGED; no other modifications to the file; `npm run build` passes; existing ticket metrics display is regression-free
  - **Depends**: T017
  - **Test**: no
  - **Risk**: LOW

- [X] T019 [P] [US4] Update src/web-form/app/dashboard/DashboardContent.tsx — add user name + role badge in header
  - **File**: `src/web-form/app/dashboard/DashboardContent.tsx` (UPDATE — locate existing file)
  - **Acceptance**: Accepts `user: { name: string, role: string }` prop (add to existing props interface); renders user name and role badge in dashboard header — e.g. "Welcome, {user.name}" + `<span className="bg-blue-600 text-xs px-2 py-1 rounded">{user.role}</span>`; all existing dashboard content (ticket metrics, recent tickets table) is UNCHANGED and regression-free
  - **Depends**: T018 (can be written in parallel — different file)
  - **Test**: no
  - **Risk**: LOW

**Checkpoint**: US4 complete. Agent sees their name + role in dashboard header. Session expiry redirects to `/login`.

---

## Phase 7: User Story 5 — Navbar Auth State (Priority: P5)

**Goal**: Navbar adapts to authentication state — shows Login when unauthenticated, role-based links + Logout when authenticated. Server Component render prevents flash of incorrect state.

**Independent Test**: Visit any page while logged out → verify navbar shows "Login" button only. Log in as admin → verify "Admin Dashboard" link visible. Log in as agent → verify "Dashboard" link visible (not "Admin Dashboard"). Click Logout → session cleared → navbar shows "Login".

### Implementation for US5

- [X] T020 [US5] Update src/web-form/components/Navbar.tsx — make async Server Component with auth-aware links
  - **File**: `src/web-form/components/Navbar.tsx` (UPDATE)
  - **Acceptance**: Convert to async Server Component (`export default async function Navbar()`); add `const session = await auth()` at top; conditional rendering:
    - No session: render "Login" button → `<Link href="/login">Login</Link>` only (no dashboard/admin links)
    - Admin session: render links — Home (`/`), Admin Dashboard (`/admin/dashboard`), Get Support (`/support`), Logout button
    - Agent session: render links — Home (`/`), Dashboard (`/dashboard`), Get Support (`/support`), Logout button
    - Logout implementation: `<form action={async () => { 'use server'; await signOut({ redirectTo: '/login' }) }}><button type="submit">Logout</button></form>`
    - No `'use client'` directive (Server Component)
    - No flash of unauthenticated state (Server Component renders correct nav on first paint)
    - `npm run build` passes
  - **Depends**: T019
  - **Test**: no
  - **Risk**: LOW — if Navbar was previously a Client Component, removing `'use client'` may require extracting any client-side interactive pieces to a child component

**Checkpoint**: US5 complete. All 5 user stories implemented. Run full end-to-end flow.

---

## Phase 8: Polish & Validation

**Purpose**: Build verification, smoke tests, and final commit

- [X] T021 Run npm run build in src/web-form/ and resolve any TypeScript or build errors
  - **File**: `src/web-form/` (build check — no file changes unless errors found)
  - **Acceptance**: `cd src/web-form && npm run build` exits 0 with no TypeScript errors and no missing module errors; if errors exist: fix them in the relevant file before proceeding
  - **Depends**: T020
  - **Test**: yes — this IS the test
  - **Risk**: LOW

- [X] T022 Run quickstart.md smoke tests end-to-end (seed → login → route protection → admin dashboard → logout)
  - **File**: `specs/011-auth/quickstart.md` (reference only)
  - **Acceptance**: All scenarios in quickstart.md pass manually: (1) seed script idempotent; (2) admin login → `/admin/dashboard` reachable; (3) agent login → `/dashboard` reachable; (4) unauthenticated `/dashboard` → 302 `/login`; (5) agent `/admin/dashboard` → 302 `/dashboard`; (6) admin creates new agent → new agent can log in; (7) Logout clears session; (8) public routes `/`, `/support`, `/ticket/*` load without auth
  - **Depends**: T021
  - **Test**: yes (manual smoke)
  - **Risk**: LOW

- [X] T023 Commit all changes on branch 011-auth (do NOT push)
  - **File**: all created/modified files in `src/web-form/`, `production/database/`, `specs/011-auth/`
  - **Acceptance**: `git status` shows no uncommitted changes after commit; commit message follows conventional commit format: `feat(auth): Phase 7A — NextAuth.js v5 auth + RBAC`; branch remains `011-auth`; NOT pushed to remote
  - **Depends**: T022
  - **Test**: no
  - **Risk**: LOW

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup: T001–T002)
  └── Phase 2 Foundational (T003–T011) — BLOCKS all user stories
        ├── B1 DB Migration: T003 [P] + T004 [P] — parallel
        ├── B2 NextAuth: T005 → T006 → T007 → T008 → T009 → T010 — sequential (each depends on previous)
        └── B8 Seed: T011 (after T010)
              └── Phase 3 US1 Login (T012–T013)
                    └── Phase 4 US2 Route Protection (T014) ← ⚠️ HIGH RISK
                          └── Phase 5 US3 Admin Dashboard (T015[P] + T016[P] → T017)
                                └── Phase 6 US4 Agent Dashboard (T018[P] + T019[P])
                                      └── Phase 7 US5 Navbar (T020)
                                            └── Phase 8 Polish (T021 → T022 → T023)
```

### HIGH RISK Subtasks

| Task | Block | Risk | Mitigation |
|------|-------|------|------------|
| T005 | B2 | next-auth@beta peer dep conflicts | Pin to specific beta version on conflict; run `npm run build` to verify |
| T007 | B2 | auth.config.ts Edge safety | Keep `bcrypt` import inside `authorize()` function body; never at module top |
| T008 | B2 | auth.ts v5 export API mismatch | Use `export const { handlers, auth, signIn, signOut } = NextAuth(...)` pattern |
| T009 | B2 | TypeScript type augmentation | Ensure `tsconfig.json` `include` covers `types/` directory |
| T014 | B3 | proxy.ts silent failure | File must be `proxy.ts` NOT `middleware.ts`; run all 4 smoke tests before continuing |

### Parallel Opportunities

```bash
# Phase 2 — B1 tasks (parallel):
T003: Create 004_add_users_table.sql
T004: Add queries.py functions

# Phase 5 — US3 admin dashboard (parallel):
T015: Create admin/dashboard/page.tsx
T016: Create AdminDashboardContent.tsx

# Phase 6 — US4 agent dashboard (parallel):
T018: Update dashboard/page.tsx
T019: Update DashboardContent.tsx
```

### User Story Dependencies

| Story | Priority | Block | Depends On |
|-------|----------|-------|------------|
| US1 Login | P1 | B4 | Phase 2 Foundational (B1+B2+B8) |
| US2 Route Protection | P2 | B3 HIGH RISK | US1 (T013 — login page for redirect target) |
| US3 Admin Dashboard | P3 | B5 | US2 (T014 — proxy guards admin routes) |
| US4 Agent Dashboard | P4 | B6 | US3 (T017 — auth guard pattern established) |
| US5 Navbar | P5 | B7 | US4 (T019 — all auth patterns stable) |

---

## Implementation Strategy

### MVP First (US1 + US2 only — minimum viable auth)

1. Complete Phase 1 (Setup)
2. Complete Phase 2 (Foundational — B1 + B2 + B8)
3. Complete Phase 3 US1 (Login page)
4. Complete Phase 4 US2 (proxy.ts — route protection) — **SMOKE TEST ALL 4 CASES**
5. **STOP and VALIDATE**: admin can log in, unauthenticated access redirects, agent blocked from admin
6. Only then proceed to US3–US5

### Full Delivery Order

1. Setup → Foundational → US1 → US2 → US3 → US4 → US5 → Polish
2. Each phase is a shippable increment
3. After US2: basic auth is fully functional (login + route guard)
4. After US3: admin user management works
5. After US4: agent dashboard is auth-gated
6. After US5: navbar reflects auth state

---

---

## Phase 9: UI/UX Polish (Post-implementation additions — 2026-04-10)

**Purpose**: Professional CRM-grade UI — login without Navbar/Footer, route group restructure, auth-aware footer

- [X] T024 Restructure app/ into (auth) and (main) route groups — login has no Navbar/Footer
  - **File**: `src/web-form/app/(auth)/layout.tsx` (CREATE) | `src/web-form/app/(main)/layout.tsx` (CREATE) | `src/web-form/app/layout.tsx` (UPDATE — remove Navbar/Footer)
  - **Acceptance**: `/login` renders with NO Navbar or Footer; all other routes (`/`, `/dashboard`, `/admin/dashboard`, `/support`) retain Navbar + Footer; `npm run build` 0 errors; all 5 smoke tests pass
  - **Depends**: T020
  - **Test**: yes — `curl -sI /login` returns 200 with no nav markup; `/dashboard` still has nav
  - **Risk**: LOW

- [X] T025 Redesign login page — professional split-screen CRM UI
  - **File**: `src/web-form/app/(auth)/login/page.tsx` (UPDATE) | `src/web-form/app/(auth)/login/LoginForm.tsx` (UPDATE)
  - **Acceptance**: Left panel: NexaFlow brand, tagline, 3 feature bullets with icons; Right panel: email + password fields with icons, password show/hide toggle, loading spinner, error banner; No "Create Account" or "Forgot Password" links; Responsive (left panel hidden on mobile); `npm run build` 0 errors
  - **Depends**: T024
  - **Test**: no (manual — visual)
  - **Risk**: LOW

- [X] T026 Update Footer to auth-aware Server Component — role-based nav links
  - **File**: `src/web-form/components/Footer.tsx` (UPDATE)
  - **Acceptance**: Footer is async Server Component calling `auth()`; shows Admin link only when `role === 'admin'`; shows Dashboard link only when `role === 'agent'`; hardcoded `/dashboard` link removed; GitHub + Home + Get Support links always visible
  - **Depends**: T024
  - **Test**: no (manual — visual)
  - **Risk**: LOW

---

## Summary

| Metric | Count |
|--------|-------|
| Total tasks | 26 |
| Phase 1 Setup | 2 |
| Phase 2 Foundational (B1+B2+B8) | 9 |
| Phase 3 US1 Login (B4) | 2 |
| Phase 4 US2 Route Protection (B3) | 1 |
| Phase 5 US3 Admin Dashboard (B5) | 3 |
| Phase 6 US4 Agent Dashboard (B6) | 2 |
| Phase 7 US5 Navbar (B7) | 1 |
| Phase 8 Polish | 3 |
| Phase 9 UI/UX Polish | 3 |
| **HIGH RISK tasks** | **5** (T005, T007, T008, T009, T014) |
| Parallel opportunities | 3 groups (T003+T004, T015+T016, T018+T019) |
