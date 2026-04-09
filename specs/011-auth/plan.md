# Implementation Plan: NextAuth.js v5 Auth + RBAC

**Branch**: `011-auth` | **Date**: 2026-04-09 | **Spec**: [spec.md](./spec.md)

---

## Summary

Add internal authentication and role-based access control to the NexaFlow support portal. Internal staff (admins and agents) log in at `/login` using email/password credentials. Sessions are JWT-based (no database session table). Route protection via `proxy.ts` blocks unauthenticated access to `/dashboard` and `/admin/*`. Admin users can create new accounts from `/admin/dashboard`. The default admin seed (`admin@nexaflow.com`) is provisioned via an idempotent `seed.ts` script. Public routes (`/`, `/support`, `/ticket/*`) remain unprotected.

---

## Technical Context

**Language/Version**: TypeScript / Next.js 16.2.2 (App Router)  
**Primary Dependencies**: next-auth@beta (v5), bcryptjs, @neondatabase/serverless, zod (already installed), react-hook-form (already installed)  
**Storage**: Neon PostgreSQL 16 (existing connection via `DATABASE_URL` env var)  
**Testing**: Manual smoke tests + TypeScript compile check  
**Target Platform**: Node.js (Next.js 16 routes run on Node.js runtime, not Edge)  
**Project Type**: Web application (Next.js 16 frontend + FastAPI backend)  
**Performance Goals**: Login round-trip < 2s; JWT verify on each protected route < 50ms  
**Constraints**: proxy.ts (not middleware.ts — Next.js 16 rename); JWT strategy only (no DB sessions); AUTH_SECRET shared with FastAPI  
**Scale/Scope**: ~10–50 internal users; no pagination needed for user table in this phase  

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Smallest viable change | ✅ PASS | Adding auth layer without touching existing ticket/agent code |
| No DB sessions | ✅ PASS | JWT-only strategy aligns with constitution's stateless design |
| Secrets in env vars | ✅ PASS | AUTH_SECRET in `.env.local`, never committed |
| No plaintext passwords | ✅ PASS | bcryptjs hash stored; plaintext never persisted |
| Constitution §VI tech stack | ⚠ NOTE | Constitution lists "Next.js 15" but 16.2.2 is installed. This phase uses 16.2.2 as found. ADR suggestion below. |
| No unrelated refactoring | ✅ PASS | Existing dashboard/support pages untouched except adding auth guard |
| Migration numbered correctly | ✅ PASS | 004_add_users_table.sql follows 001/002 + add_ticket_priority |

📋 **Architectural decision detected**: Next.js version in production is 16.2.2 (constitution says 15). The proxy.ts rename and Node.js runtime change are significant. Document? Run `/sp.adr next-js-16-upgrade`

---

## Project Structure

### Documentation (this feature)

```text
specs/011-auth/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── POST_api_admin_users.md
│   └── GET_POST_api_auth_nextauth.md
└── tasks.md             # Phase 2 output (sp.tasks)
```

### Source Code

```text
# Database
production/database/migrations/
└── 004_add_users_table.sql        # NEW: users table + role enum

production/database/
└── queries.py                     # UPDATED: add get_user_by_email(), create_user()

# Next.js web-form
src/web-form/
├── auth.ts                        # NEW: NextAuth config (handlers, auth, signIn, signOut)
├── auth.config.ts                 # NEW: providers-only config (Edge-safe if needed)
├── proxy.ts                       # NEW: route protection (NOT middleware.ts — Next.js 16)
├── types/
│   └── next-auth.d.ts             # NEW: type augmentation for role + id on JWT/Session
├── scripts/
│   └── seed.ts                    # NEW: idempotent admin seed script
├── lib/
│   └── db.ts                      # NEW: Neon serverless DB client for Next.js
├── app/
│   ├── api/
│   │   ├── auth/
│   │   │   └── [...nextauth]/
│   │   │       └── route.ts       # NEW: NextAuth handler (GET + POST)
│   │   └── admin/
│   │       └── users/
│   │           └── route.ts       # NEW: POST create user (admin only)
│   ├── login/
│   │   └── page.tsx               # NEW: login page (shadcn form, Zod, dark theme)
│   └── admin/
│       └── dashboard/
│           └── page.tsx           # NEW: admin dashboard (tickets + create user)
├── components/
│   └── Navbar.tsx                 # UPDATED: auth-aware nav links
└── app/
    └── dashboard/
        └── page.tsx               # UPDATED: add auth guard
```

---

## Phase 0: Research

*All research decisions are resolved below. No NEEDS CLARIFICATION markers remain.*

See [`research.md`](./research.md) for full findings.

### R-001: Next.js 16 proxy.ts vs middleware.ts

**Decision**: Use `proxy.ts` at `src/web-form/proxy.ts`.  
**Rationale**: Context7 confirmed: "As of Next.js 16, `middleware.ts` has been renamed to `proxy.ts` and now runs on the Node.js runtime instead of the edge runtime." This eliminates all Edge compatibility concerns for `bcryptjs` and the Neon DB client.  
**Alternatives considered**: Keep middleware.ts — rejected because Next.js 16 ignores it silently, leading to unprotected routes with no error.

### R-002: NextAuth v5 Configuration Split (auth.ts vs auth.config.ts)

**Decision**: Use a split configuration: `auth.config.ts` contains only providers (Edge-safe); `auth.ts` imports from `auth.config.ts` and adds DB-dependent callbacks.  
**Rationale**: This is the recommended v5 pattern for projects that may need Edge-compatible auth checks. Since proxy.ts now runs on Node.js in Next.js 16, the split is not strictly required but follows best practices and future-proofs the design.  
**Context7 pattern**:
```typescript
// auth.config.ts — providers only (no bcrypt, no DB import)
export const authConfig = { providers: [Credentials({...})] }

// auth.ts — full config (imports authConfig + adds callbacks)
export const { handlers, auth, signIn, signOut } = NextAuth({ ...authConfig, callbacks: {...} })
```

### R-003: Database Client for Next.js

**Decision**: Use `@neondatabase/serverless` (Neon's official serverless driver).  
**Rationale**: Neon is already the production database. The serverless driver is optimized for serverless/edge environments, has zero native dependencies, and works in Next.js App Router server components. No ORM needed for 2 queries.  
**Package**: `@neondatabase/serverless`  
**Alternatives considered**: `pg` (heavier, works but overkill for 2 queries); `prisma` (too heavy for auth-only use case); raw fetch to FastAPI (introduces FastAPI dependency and extra latency).

### R-004: Password Hashing — bcryptjs

**Decision**: Use `bcryptjs` with cost factor 12 for hashing, `bcrypt.compare()` async for verification.  
**Rationale**: Context7 confirmed bcryptjs async API: `await bcrypt.hash(password, 12)` and `await bcrypt.compare(plaintext, hash)`. Cost factor 12 is secure (~250ms on modern hardware) without being user-noticeable.  
**Pattern**:
```typescript
// Hash (seed/create user):
const hash = await bcrypt.hash(password, 12)

// Verify (login):
const isValid = await bcrypt.compare(credentials.password, user.hashed_password)
```

### R-005: JWT Token + Role Propagation

**Decision**: Store `role` and `id` in JWT via `jwt` callback; expose to client via `session` callback.  
**Rationale**: Context7 pattern confirmed:
```typescript
callbacks: {
  async jwt({ token, user }) {
    if (user) { token.role = user.role; token.id = user.id }
    return token
  },
  async session({ session, token }) {
    session.user.role = token.role as string
    session.user.id = token.id as string
    return session
  }
}
```
**Type augmentation** required in `types/next-auth.d.ts` to add `role` and `id` to `Session`, `User`, and `JWT` types.

### R-006: Route Protection Pattern (proxy.ts)

**Decision**: Export `auth` as default middleware from proxy.ts with matcher targeting `/dashboard` and `/admin/:path*`. Custom redirect logic handles role-based admin access.  
**Pattern**:
```typescript
// proxy.ts
import { auth } from "@/auth"
import { NextResponse } from "next/server"

export default auth((req) => {
  const isLoggedIn = !!req.auth
  const path = req.nextUrl.pathname

  if (!isLoggedIn) {
    return NextResponse.redirect(new URL("/login", req.url))
  }
  if (path.startsWith("/admin") && req.auth?.user?.role !== "admin") {
    return NextResponse.redirect(new URL("/dashboard", req.url))
  }
})

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*"]
}
```

### R-007: Login Page — signIn() Server Action

**Decision**: Use NextAuth v5 `signIn()` server action (not client-side `signIn()` from next-auth/react).  
**Rationale**: Avoids client-side exposure of credentials. The login form submits via a Server Action which calls `signIn("credentials", { email, password, redirect: false })` and handles the result.  
**Error handling**: `signIn` returns an error object on failure; display "Invalid email or password" inline.

### R-008: Neon Migration Numbering

**Decision**: Use `004_add_users_table.sql` (follows 001, 002, add_ticket_priority which is effectively 003).  
**Rationale**: Maintains sequential numbering for future migrations. The unnumbered `add_ticket_priority.sql` is treated as 003.

---

## Phase 1: Design & Contracts

See [`data-model.md`](./data-model.md) and [`contracts/`](./contracts/) for full artifacts.

### Data Model Summary

**New table: `users`**

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, DEFAULT gen_random_uuid() |
| `name` | VARCHAR(255) | NOT NULL |
| `email` | VARCHAR(255) | UNIQUE NOT NULL |
| `hashed_password` | TEXT | NOT NULL |
| `role` | VARCHAR(50) | NOT NULL, CHECK IN ('admin','agent') |
| `created_at` | TIMESTAMPTZ | NOT NULL DEFAULT NOW() |

**Role enum**: `'admin'` | `'agent'` — stored as VARCHAR(50) with CHECK constraint (no PostgreSQL ENUM type to simplify migration rollback).

**Python queries.py additions**:
- `get_user_by_email(email: str) -> dict | None` — SELECT by email for NextAuth authorize
- `create_user(name, email, hashed_password, role) -> dict` — INSERT, returns created user
- Both use asyncpg connection pool already established in the codebase.

**Note**: queries.py functions are FastAPI-side (Python). The Next.js side uses `@neondatabase/serverless` directly in `lib/db.ts` for its own queries. These are two separate DB clients connecting to the same Neon instance.

### API Contracts

#### POST /api/admin/users
- **Auth**: Required — admin role only (verified via `auth()` session check)
- **Request body**: `{ name: string, email: string, password: string, role: "admin" | "agent" }`
- **Validation**: Zod schema — name non-empty, email valid, password ≥8 chars, role enum
- **Success 201**: `{ id: string, name: string, email: string, role: string, created_at: string }`
- **Error 400**: `{ error: "Validation failed", details: [...] }`
- **Error 409**: `{ error: "Email already exists" }`
- **Error 401**: `{ error: "Unauthorized" }` (not logged in)
- **Error 403**: `{ error: "Forbidden" }` (logged in but not admin)
- **HIGH RISK**: This endpoint creates privileged accounts. Must double-check role from session on server — do not trust client-sent role without session verification.

#### GET + POST /api/auth/[...nextauth]
- **Standard NextAuth v5 handler** — delegates to NextAuth `handlers`
- No custom logic beyond what NextAuth provides
- POST handles credentials sign-in; GET handles sign-out redirect + session check

---

## Implementation Blocks

### Block 1 — Database Migration *(LOW RISK)*

**Files**:
1. `production/database/migrations/004_add_users_table.sql` — CREATE TABLE users with role CHECK constraint; CREATE INDEX on email
2. `production/database/queries.py` — add `get_user_by_email()` and `create_user()` async functions

**Acceptance**:
- `psql` execution of migration succeeds with no errors
- `get_user_by_email("admin@nexaflow.com")` returns expected row after seed
- Migration is idempotent (`CREATE TABLE IF NOT EXISTS`)

---

### Block 2 — NextAuth.js Setup *(HIGH RISK)*

**Risk**: Version compatibility between next-auth@beta, Next.js 16, and TypeScript. The v5 API differs significantly from v4. Package may require specific peer dependency resolution.

**Files**:
1. Install packages: `next-auth@beta bcryptjs @types/bcryptjs @neondatabase/serverless`
2. `src/web-form/lib/db.ts` — Neon serverless client using `DATABASE_URL` env var
3. `src/web-form/auth.config.ts` — providers config: Credentials with email/password fields
4. `src/web-form/auth.ts` — full NextAuth config: imports auth.config.ts, adds jwt/session callbacks, sets `pages: { signIn: "/login" }`, `session: { strategy: "jwt" }`
5. `src/web-form/types/next-auth.d.ts` — module augmentation for `role: string` and `id: string` on Session.user, User, and JWT
6. Add `AUTH_SECRET` to `.env.local` (generate with `openssl rand -base64 32`)

**Acceptance**:
- `npx tsc --noEmit` passes with no type errors on auth.ts
- `auth()` returns null when no session; returns `{ user: { role, id, email } }` when session active

---

### Block 3 — Route Protection via proxy.ts *(HIGH RISK)*

**Risk**: Next.js 16 proxy.ts is a renamed file. If auth.ts has import issues detectable at Edge (even though proxy now runs on Node.js), the middleware silently fails and routes are unprotected. Must verify with manual test.

**Files**:
1. `src/web-form/proxy.ts` — auth-wrapped proxy with matcher for `/dashboard/:path*` and `/admin/:path*`

**Logic**:
- No session → redirect to `/login`  
- Session with `role !== "admin"` on `/admin/*` → redirect to `/dashboard`
- Session present on `/dashboard` → pass through

**Acceptance**:
- GET `/dashboard` with no cookie → 302 to `/login`
- GET `/admin/dashboard` with agent cookie → 302 to `/dashboard`
- GET `/admin/dashboard` with admin cookie → 200

---

### Block 4 — Login Page *(LOW RISK)*

**Files**:
1. `src/web-form/app/login/page.tsx` — login page (Server Component wrapper)
2. `src/web-form/app/login/LoginForm.tsx` — Client Component with react-hook-form + Zod + shadcn

**Design**:
- Background: `bg-[#0F172A]` (matches site theme)
- Card: `bg-slate-800/50 border-slate-700`, centered, max-w-sm
- Fields: Email input + Password input (shadcn Input)
- Submit: Blue button (`bg-[#3B82F6] hover:bg-[#2563EB]`)
- Error: Inline red text below form on failed login
- No "Sign up" or "Forgot password" links
- On success: redirect admin → `/admin/dashboard`, agent → `/dashboard`

**Acceptance**:
- Empty submit → Zod validation errors shown inline
- Wrong credentials → "Invalid email or password" shown
- Valid admin credentials → redirected to `/admin/dashboard`
- Valid agent credentials → redirected to `/dashboard`

---

### Block 5 — Admin Dashboard *(MEDIUM RISK)*

**Risk**: The admin dashboard makes a server-side call to FastAPI for tickets + a direct Neon call for user creation. Two distinct data sources. Must handle gracefully if either is down.

**Files**:
1. `src/web-form/app/admin/dashboard/page.tsx` — Server Component; fetches all tickets from FastAPI; checks session is admin
2. `src/web-form/app/admin/dashboard/AdminDashboardContent.tsx` — Client Component; tickets table + create user form
3. `src/web-form/app/api/admin/users/route.ts` — POST handler; verifies admin session, validates input, hashes password, inserts to Neon

**Acceptance**:
- Unauthenticated access → handled by proxy (redirect to `/login`)
- Agent accessing `/admin/dashboard` → handled by proxy (redirect to `/dashboard`)
- Admin sees full tickets table (same data as `/dashboard`)
- Create user form: successful creation shows success toast; duplicate email shows error
- Created user can log in immediately

---

### Block 6 — Update /dashboard (Auth Guard) *(LOW RISK)*

**Files**:
1. `src/web-form/app/dashboard/page.tsx` — add `auth()` call; redirect to `/login` if no session (belt-and-suspenders beyond proxy)
2. `src/web-form/app/dashboard/DashboardContent.tsx` — add user name + role badge in header

**Acceptance**:
- Direct access without auth → redirect (proxy handles this; page.tsx adds belt-and-suspenders)
- Authenticated agent sees same ticket metrics as before (no regression)
- User name and role badge visible in dashboard header

---

### Block 7 — Navbar Updates *(LOW RISK)*

**Files**:
1. `src/web-form/components/Navbar.tsx` — make Server Component async; call `auth()` to get session; conditionally render links

**Logic**:
- No session → show "Login" button linking to `/login`
- Admin session → show: Home, Admin Dashboard, Get Support, Logout button
- Agent session → show: Home, Dashboard, Get Support, Logout button
- Logout: `<form action={async () => { "use server"; await signOut() }}>`

**Acceptance**:
- No flash of unauthenticated nav state (Server Component renders correct state on first paint)
- Logout clears session and redirects to `/login`
- Role links correct for both admin and agent

---

### Block 8 — Seed Script *(LOW RISK)*

**Files**:
1. `src/web-form/scripts/seed.ts` — standalone TypeScript script using `@neondatabase/serverless`; checks if `admin@nexaflow.com` exists; creates only if absent

**Run command**: `npx tsx src/web-form/scripts/seed.ts`

**Acceptance**:
- First run: creates admin user; logs "Admin user created"
- Second run: skips creation; logs "Admin user already exists"
- Created admin can log in at `/login` with `admin@nexaflow.com / Admin123!`

---

## Risk Register

| Risk | Severity | Block | Mitigation |
|------|----------|-------|------------|
| next-auth@beta breaking changes | HIGH | B2 | Pin to specific beta version; test `auth()` call immediately after install |
| proxy.ts silent failure (wrong filename) | HIGH | B3 | Manual smoke test: unauthenticated GET `/dashboard` must 302 |
| bcryptjs compare async — hash format mismatch | MEDIUM | B2/B8 | Ensure seed uses same bcrypt cost factor as authorize; test login immediately after seed |
| Neon connection pooling in serverless context | MEDIUM | B3/B5/B8 | Use `@neondatabase/serverless` neonConfig for WebSocket pooling; avoid creating new Pool per request |
| AUTH_SECRET not shared with FastAPI | MEDIUM | B2 | Add `AUTH_SECRET` to both `.env.local` (Next.js) and FastAPI env; document in quickstart.md |
| Admin role bypass via client POST | HIGH | B5 | `/api/admin/users` MUST verify `session.user.role === "admin"` server-side, not via client header |

---

## Environment Variables

```bash
# src/web-form/.env.local (gitignored)
AUTH_SECRET=<generate with: openssl rand -base64 32>
DATABASE_URL=<existing Neon connection string>
FASTAPI_URL=https://psqasim-crm-digital-fte-api.hf.space

# FastAPI .env (same AUTH_SECRET value for JWT verification)
AUTH_SECRET=<same value as above>
```

---

## Implementation Order

Execute blocks in this order (each block depends on the previous):

```
Block 1 (DB migration) 
  → Block 2 (NextAuth setup + lib/db.ts)
  → Block 8 (Seed script — validates DB + bcrypt work)
  → Block 3 (proxy.ts — validates auth() works)
  → Block 4 (Login page)
  → Block 5 (Admin dashboard + /api/admin/users)
  → Block 6 (Update /dashboard)
  → Block 7 (Navbar)
```

**Rationale**: Seed script (Block 8) is moved before UI (Blocks 3–7) to give a working credential for manual testing of all subsequent blocks.
