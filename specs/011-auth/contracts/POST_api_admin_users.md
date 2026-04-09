# API Contract: POST /api/admin/users

**Route**: `POST /api/admin/users`  
**Auth**: Required — `admin` role only  
**Purpose**: Create a new internal user (agent or admin account)

---

## Request

### Headers

| Header | Value | Required |
|--------|-------|----------|
| `Content-Type` | `application/json` | Yes |
| Cookie | NextAuth session cookie | Yes (auto-sent by browser) |

### Body

```json
{
  "name": "Jane Smith",
  "email": "jane@nexaflow.com",
  "password": "SecurePass123!",
  "role": "agent"
}
```

### Validation Rules

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | string | Required, min 2 chars, max 255 chars |
| `email` | string | Required, valid email format |
| `password` | string | Required, min 8 chars |
| `role` | string | Required, one of: `"admin"` \| `"agent"` |

---

## Responses

### 201 Created

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Jane Smith",
  "email": "jane@nexaflow.com",
  "role": "agent",
  "created_at": "2026-04-09T12:00:00.000Z"
}
```

### 400 Bad Request (Validation failure)

```json
{
  "error": "Validation failed",
  "details": [
    { "field": "email", "message": "Invalid email address" },
    { "field": "password", "message": "Password must be at least 8 characters" }
  ]
}
```

### 401 Unauthorized (No session)

```json
{ "error": "Unauthorized" }
```

### 403 Forbidden (Session exists but role is not admin)

```json
{ "error": "Forbidden — admin role required" }
```

### 409 Conflict (Duplicate email)

```json
{ "error": "A user with this email address already exists" }
```

### 500 Internal Server Error

```json
{ "error": "Failed to create user" }
```

---

## Security Notes

1. **Server-side role check**: The handler calls `auth()` and verifies `session.user.role === "admin"` — never trusts a client-supplied role claim.
2. **Password hashing**: The plaintext `password` from the request body is hashed with `bcrypt.hash(password, 12)` before storage. Plaintext is never written to the database or logs.
3. **Email normalization**: Email is lowercased before INSERT to prevent duplicate-with-different-case exploits.
4. **No hashed_password in response**: The response body never includes `hashed_password`.

---

## Server-Side Handler Pseudocode

```typescript
export async function POST(req: Request) {
  // 1. Verify session
  const session = await auth()
  if (!session) return Response.json({ error: "Unauthorized" }, { status: 401 })
  if (session.user.role !== "admin") return Response.json({ error: "Forbidden" }, { status: 403 })

  // 2. Parse + validate body
  const body = await req.json()
  const result = createUserSchema.safeParse(body)
  if (!result.success) return Response.json({ error: "Validation failed", details: ... }, { status: 400 })

  // 3. Hash password
  const hashedPassword = await bcrypt.hash(result.data.password, 12)

  // 4. Insert to DB (handle unique constraint violation → 409)
  try {
    const user = await createUser(result.data.name, result.data.email, hashedPassword, result.data.role)
    return Response.json(user, { status: 201 })
  } catch (err) {
    if (isDuplicateEmailError(err)) return Response.json({ error: "..." }, { status: 409 })
    return Response.json({ error: "Failed to create user" }, { status: 500 })
  }
}
```
