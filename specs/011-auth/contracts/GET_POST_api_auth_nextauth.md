# API Contract: /api/auth/[...nextauth]

**Route**: `GET|POST /api/auth/[...nextauth]`  
**Handler**: NextAuth v5 catch-all handler  
**Purpose**: Standard NextAuth.js authentication endpoints (sign-in, sign-out, session, CSRF token)

---

## Route File

```typescript
// src/web-form/app/api/auth/[...nextauth]/route.ts
import { handlers } from "@/auth"
export const { GET, POST } = handlers
```

No custom logic — delegates entirely to the NextAuth v5 `handlers` export.

---

## Endpoints Handled by NextAuth

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/auth/session` | Returns current session (JSON) |
| `GET` | `/api/auth/csrf` | Returns CSRF token for forms |
| `GET` | `/api/auth/providers` | Lists available providers |
| `POST` | `/api/auth/signin/credentials` | Authenticates with email/password |
| `GET` | `/api/auth/signout` | Initiates sign-out |
| `POST` | `/api/auth/signout` | Completes sign-out, clears cookie |

---

## Session Endpoint: GET /api/auth/session

### Response (authenticated)

```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "NexaFlow Admin",
    "email": "admin@nexaflow.com",
    "role": "admin",
    "image": null
  },
  "expires": "2026-05-09T12:00:00.000Z"
}
```

### Response (unauthenticated)

```json
{}
```

---

## Sign-In Endpoint: POST /api/auth/signin/credentials

### Request Body

```json
{
  "email": "admin@nexaflow.com",
  "password": "Admin123!",
  "csrfToken": "<token from /api/auth/csrf>",
  "callbackUrl": "/admin/dashboard",
  "json": "true"
}
```

### Responses

| Status | Meaning |
|--------|---------|
| 200 | Sign-in successful; session cookie set |
| 401 | Invalid credentials (authorize() returned null) |

---

## Notes

- **CSRF protection**: NextAuth v5 handles CSRF tokens automatically. The login Server Action uses `signIn()` which includes CSRF internally.
- **Cookie**: NextAuth sets a `__Secure-authjs.session-token` (production) or `authjs.session-token` (development) HTTP-only cookie.
- **JWT**: Session is stored entirely in the cookie as a signed JWT. No database session record.
- **No custom implementation**: This route file has no business logic — it's a pure delegate to `handlers`.
