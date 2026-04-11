# Authentication & RBAC Guide

## Overview

NexaFlow uses NextAuth.js v5 (Auth.js) with a JWT strategy — no database sessions.
There is **no public signup**. All staff accounts are created by an admin.

---

## Roles

| Role | Access |
|------|--------|
| `admin` | `/admin/dashboard` — all tickets, metrics, user management |
| `agent` | `/dashboard` — My Tickets (own submitted tickets only) |
| public | `/`, `/support`, `/ticket/[id]` — no login required |

---

## Default Admin Account

| Field | Value |
|-------|-------|
| Email | `admin@nexaflow.com` |
| Password | `Admin123!` |

> Change this immediately after first login via **Profile → Change Password**.

---

## Create a Staff Account

1. Login as admin at `/login`
2. Go to `/admin/dashboard`
3. Fill in the **Add Staff Account** form on the right side
4. Set role to `Admin` or `Agent`
5. Copy the credentials from the confirmation card that appears
6. Share credentials with the staff member
7. They can change their password at `/profile`

---

## Protected Routes

| Route | Auth Required | Role Required |
|-------|--------------|---------------|
| `/dashboard` | Yes | Any |
| `/admin/dashboard` | Yes | `admin` |
| `/profile` | Yes | Any |
| `/ticket/[id]` | No | — |
| `/support` | No | — |
| `/`, `/login` | No | — |

---

## Environment Variables

```env
AUTH_SECRET=<generate with: npx auth secret>
NEXTAUTH_URL=https://your-vercel-url.vercel.app
```

`AUTH_SECRET` must be set in both local `.env` and Vercel environment settings.

---

## Running the Seed Script

If the users table is empty (fresh database), create the default admin:

```bash
cd src/web-form
npx tsx scripts/seed.ts
# Output: ✅ Admin user created: admin@nexaflow.com
```

The seed script is idempotent — safe to run multiple times (skips if admin exists).

---

## Tech Details

- **Strategy:** JWT (stateless — works with HF Spaces, no sticky sessions needed)
- **Password hashing:** `bcryptjs` (10 rounds)
- **Session shape:** `{ user: { id, name, email, role } }`
- **Files:** `src/web-form/auth.ts`, `src/web-form/app/(auth)/login/`
- **ADR:** `history/adr/ADR-0003-nextauth-jwt-rbac.md`
