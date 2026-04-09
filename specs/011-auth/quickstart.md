# Quickstart: Phase 7A — NextAuth.js v5 Auth + RBAC

**Date**: 2026-04-09  
**Branch**: `011-auth`

---

## Prerequisites

- Node.js 18+ installed
- Neon PostgreSQL connection string available (`DATABASE_URL`)
- Existing `src/web-form/` Next.js project running
- On branch `011-auth`

---

## Step 1: Run Database Migration

Apply the `users` table to Neon:

```bash
# From project root
psql "$DATABASE_URL" -f production/database/migrations/004_add_users_table.sql
```

Verify:
```bash
psql "$DATABASE_URL" -c "\d users"
# Should show: id, name, email, hashed_password, role, created_at
```

---

## Step 2: Install Packages

```bash
cd src/web-form
npm install next-auth@beta bcryptjs @neondatabase/serverless
npm install -D @types/bcryptjs
```

---

## Step 3: Set Environment Variables

Create `src/web-form/.env.local`:

```bash
# Generate AUTH_SECRET:
openssl rand -base64 32

# Add to .env.local:
AUTH_SECRET=<output from above>
DATABASE_URL=<your Neon connection string>
FASTAPI_URL=https://psqasim-crm-digital-fte-api.hf.space
```

> **CRITICAL**: Copy the same `AUTH_SECRET` value to the FastAPI `.env` so it can verify JWTs issued by Next.js.

---

## Step 4: Run Seed Script

Create the default admin account:

```bash
cd src/web-form
npx tsx scripts/seed.ts
# Expected output: "Admin user created: admin@nexaflow.com"
# Re-run is safe: "Admin user already exists — skipping"
```

---

## Step 5: Start Dev Server

```bash
cd src/web-form
npm run dev
```

---

## Step 6: Smoke Test

| Test | Expected |
|------|----------|
| GET `http://localhost:3000/dashboard` | Redirect to `/login` |
| GET `http://localhost:3000/admin/dashboard` | Redirect to `/login` |
| GET `http://localhost:3000/` | 200 (public, no redirect) |
| GET `http://localhost:3000/support` | 200 (public, no redirect) |
| Login as `admin@nexaflow.com / Admin123!` | Redirect to `/admin/dashboard` |
| Login as agent (created via admin dashboard) | Redirect to `/dashboard` |
| Agent tries GET `/admin/dashboard` | Redirect to `/dashboard` |
| Click Logout | Session cleared, redirect to `/login` |

---

## FastAPI AUTH_SECRET Integration

For the FastAPI backend to verify NextAuth JWTs:

```python
# In FastAPI auth middleware (future phase)
import jwt
from fastapi import HTTPException, Header

def verify_nextauth_token(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, settings.AUTH_SECRET, algorithms=["HS256"])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
```

The shared `AUTH_SECRET` env var enables cross-service JWT verification without a dedicated auth service.

---

## Create a New Agent Account

1. Log in as admin at `/login`
2. Navigate to `/admin/dashboard`
3. Fill in the "Create User" form: Name, Email, Password (min 8 chars), Role: Agent
4. Submit — agent can log in immediately at `/login`
