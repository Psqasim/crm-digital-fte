# Data Model: Phase 7A — NextAuth.js v5 Auth + RBAC

**Date**: 2026-04-09  
**Branch**: `011-auth`

---

## New Table: `users`

### Schema

```sql
-- 004_add_users_table.sql
CREATE TABLE IF NOT EXISTS users (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name             VARCHAR(255) NOT NULL,
    email            VARCHAR(255) UNIQUE NOT NULL,
    hashed_password  TEXT         NOT NULL,
    role             VARCHAR(50)  NOT NULL DEFAULT 'agent'
                                  CHECK (role IN ('admin', 'agent')),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users (email);
```

### Field Definitions

| Field | Type | Constraints | Notes |
|-------|------|-------------|-------|
| `id` | UUID | PK, gen_random_uuid() | Matches pattern of all other tables in schema |
| `name` | VARCHAR(255) | NOT NULL | Display name; shown in navbar + dashboard header |
| `email` | VARCHAR(255) | UNIQUE NOT NULL | Primary login identifier; lowercased at application layer |
| `hashed_password` | TEXT | NOT NULL | bcryptjs hash (60-char string at cost 12); never plaintext |
| `role` | VARCHAR(50) | NOT NULL, CHECK enum | `'admin'` or `'agent'`; CHECK prevents invalid values |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() | Audit trail; UTC-stored |

### Role Enum Values

| Value | Access |
|-------|--------|
| `admin` | `/admin/dashboard`, `/dashboard`, user management |
| `agent` | `/dashboard` only |

**Design decision**: VARCHAR + CHECK constraint instead of PostgreSQL ENUM type. Rationale: CHECK constraints are easier to migrate (adding a new role is `ALTER TABLE users ADD CONSTRAINT` vs `ALTER TYPE` which requires more steps and may conflict with existing data).

---

## Python queries.py — New Functions

Add to `production/database/queries.py`:

```python
async def get_user_by_email(email: str) -> dict | None:
    """Look up a user by email for NextAuth credential verification."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, name, email, hashed_password, role FROM users WHERE email = $1",
            email.lower()
        )
        return dict(row) if row else None


async def create_user(name: str, email: str, hashed_password: str, role: str) -> dict:
    """Create a new internal user. Raises UniqueViolationError on duplicate email."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO users (name, email, hashed_password, role)
            VALUES ($1, $2, $3, $4)
            RETURNING id, name, email, role, created_at
            """,
            name, email.lower(), hashed_password, role
        )
        return dict(row)
```

**Note**: These functions are for potential FastAPI endpoints in future phases. For Phase 7A, the Next.js side uses `@neondatabase/serverless` directly (see `lib/db.ts`). The Python functions are added for completeness and future FastAPI user management endpoints.

---

## Next.js lib/db.ts — New Functions

```typescript
// src/web-form/lib/db.ts
import { neon } from "@neondatabase/serverless"

const sql = neon(process.env.DATABASE_URL!)

export interface DbUser {
  id: string
  name: string
  email: string
  hashed_password: string
  role: "admin" | "agent"
  created_at: string
}

export async function getUserByEmail(email: string): Promise<DbUser | null> {
  const rows = await sql`
    SELECT id, name, email, hashed_password, role
    FROM users
    WHERE email = ${email.toLowerCase()}
    LIMIT 1
  `
  return (rows[0] as DbUser) ?? null
}

export async function createUser(
  name: string,
  email: string,
  hashedPassword: string,
  role: "admin" | "agent"
): Promise<Omit<DbUser, "hashed_password">> {
  const rows = await sql`
    INSERT INTO users (name, email, hashed_password, role)
    VALUES (${name}, ${email.toLowerCase()}, ${hashedPassword}, ${role})
    RETURNING id, name, email, role, created_at
  `
  return rows[0] as Omit<DbUser, "hashed_password">
}
```

---

## Relationships

```
users (new)
  ↑
  │  (no FK — auth users are independent of ticket customers)
  │
tickets (existing) — assigned_to field could reference users.id in future
customers (existing) — separate entity (end customers, not internal staff)
```

**Design note**: Internal staff (`users` table) are intentionally decoupled from end customers (`customers` table). A `customers` record is an external NexaFlow subscriber. A `users` record is an internal NexaFlow employee. They share the same database but have no FK relationship in this phase.

---

## Session Token Shape (JWT)

The JWT stored in the session cookie contains:

```typescript
// Decoded JWT payload (not transmitted to client directly)
{
  sub: "uuid-of-user",          // standard JWT subject
  id: "uuid-of-user",           // explicit copy for ease of access
  email: "user@nexaflow.com",
  name: "NexaFlow Admin",
  role: "admin",                // "admin" | "agent"
  iat: 1712700000,              // issued at
  exp: 1715292000,              // expires (30 days default)
  jti: "random-uuid"            // JWT ID
}
```

**Session object shape** (accessible via `auth()` or `useSession()`):

```typescript
{
  user: {
    id: string,
    email: string,
    name: string,
    role: "admin" | "agent",
    image: string | null    // not used, included by NextAuth default
  },
  expires: string           // ISO date string
}
```
