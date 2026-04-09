# Research: Phase 7A — NextAuth.js v5 Auth + RBAC

**Date**: 2026-04-09  
**Branch**: `011-auth`  
**Sources**: Context7 (live docs), Next.js 16 release notes

---

## R-001: Next.js 16 proxy.ts Rename

**Decision**: Use `proxy.ts` at project root (alongside `app/`), NOT `middleware.ts`.

**Rationale**: Context7 live documentation confirmed: "As of Next.js 16, `middleware.ts` has been renamed to `proxy.ts` and now runs on the **Node.js runtime** instead of the edge runtime." This is a breaking change from Next.js 15. The project has Next.js 16.2.2 installed.

**Impact**:
- Edge runtime restrictions no longer apply: `bcryptjs`, Neon client, and full Node.js APIs are available in proxy.ts
- `req.auth` (from NextAuth v5) works in proxy.ts without any Edge workarounds
- File must be named `proxy.ts` — Next.js 16 ignores `middleware.ts` silently

**Alternatives rejected**: Keep `middleware.ts` — rejected because Next.js 16 does not process it; routes would appear protected during development on older tooling but fail silently in production.

---

## R-002: NextAuth v5 Configuration Pattern

**Decision**: Split configuration: `auth.config.ts` (providers only) → imported by `auth.ts` (full config).

**Pattern** (Context7 verified):

```typescript
// auth.config.ts — providers-only, no Node.js-specific imports
import type { NextAuthConfig } from "next-auth"
import Credentials from "next-auth/providers/credentials"

export const authConfig: NextAuthConfig = {
  pages: { signIn: "/login" },
  providers: [
    Credentials({
      credentials: { email: {}, password: {} },
      // authorize is added in auth.ts (requires bcryptjs + DB)
    })
  ]
}

// auth.ts — full config, Node.js runtime
import NextAuth from "next-auth"
import Credentials from "next-auth/providers/credentials"
import bcrypt from "bcryptjs"
import { authConfig } from "./auth.config"
import { getUserByEmail } from "@/lib/db"

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  providers: [
    Credentials({
      credentials: { email: {}, password: {} },
      async authorize(credentials) {
        const user = await getUserByEmail(credentials.email as string)
        if (!user) return null
        const valid = await bcrypt.compare(credentials.password as string, user.hashed_password)
        if (!valid) return null
        return { id: user.id, email: user.email, name: user.name, role: user.role }
      }
    })
  ],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, user }) {
      if (user) { token.id = user.id; token.role = (user as any).role }
      return token
    },
    async session({ session, token }) {
      session.user.id = token.id as string
      session.user.role = token.role as string
      return session
    }
  }
})
```

**Key v4→v5 changes**:
- Config file: `pages/api/auth/[...nextauth].ts` → `auth.ts` at root
- Export: default handler → named exports `{ handlers, auth, signIn, signOut }`
- Server session: `getServerSession(authOptions)` → `auth()` (zero args)
- Middleware: `withAuth` from `next-auth/middleware` → `auth` from `@/auth`
- Route handler: `app/api/auth/[...nextauth]/route.ts` exports `{ GET, POST } = handlers`

---

## R-003: Neon Serverless Driver for Next.js

**Decision**: Use `@neondatabase/serverless` (Neon's official JavaScript driver).

**Rationale**: 
- Neon-optimized, no native bindings — works in serverless contexts
- Same Neon instance already used by the FastAPI backend
- No ORM required for 2 queries (getUserByEmail, createUser)
- HTTP transport option available if WebSocket is restricted

**Usage pattern**:

```typescript
// lib/db.ts
import { neon } from "@neondatabase/serverless"
const sql = neon(process.env.DATABASE_URL!)

export async function getUserByEmail(email: string) {
  const [user] = await sql`
    SELECT id, name, email, hashed_password, role FROM users WHERE email = ${email}
  `
  return user ?? null
}

export async function createUser(name: string, email: string, hashedPassword: string, role: string) {
  const [user] = await sql`
    INSERT INTO users (name, email, hashed_password, role)
    VALUES (${name}, ${email}, ${hashedPassword}, ${role})
    RETURNING id, name, email, role, created_at
  `
  return user
}
```

**Alternatives rejected**: 
- `pg`: Heavier, requires connection pool management — overkill for 2 queries
- `prisma`: Too heavy for auth-only use, adds schema file maintenance burden
- FastAPI proxy: Adds extra network hop; FastAPI should not be the auth authority for Next.js

---

## R-004: bcryptjs Password Hashing

**Decision**: `bcryptjs` (JavaScript implementation), cost factor 12.

**API** (Context7 verified):
```typescript
import bcrypt from "bcryptjs"

// Hash (at user creation/seed time):
const hashed = await bcrypt.hash(password, 12)  // ~250ms at cost 12

// Compare (at login time in authorize()):
const isValid = await bcrypt.compare(plaintext, hashed)  // returns boolean
```

**Cost factor**: 12 chosen for balance between security (~250ms) and user experience. Cost 10 is minimum acceptable (too fast = easier brute force).

**Alternatives rejected**: `bcrypt` (native bindings, deployment complexity); `argon2` (ideal but heavier dependency); `crypto.pbkdf2` (requires more code for same security).

---

## R-005: JWT Token Role Propagation

**Decision**: Store `role` and `id` in JWT via callbacks; type-augment `next-auth.d.ts`.

**Type augmentation** (required for TypeScript):
```typescript
// types/next-auth.d.ts
import { DefaultSession, DefaultUser } from "next-auth"
import { DefaultJWT } from "next-auth/jwt"

declare module "next-auth" {
  interface Session {
    user: { role: string; id: string } & DefaultSession["user"]
  }
  interface User extends DefaultUser {
    role: string
  }
}

declare module "next-auth/jwt" {
  interface JWT extends DefaultJWT {
    role: string
    id: string
  }
}
```

**Note**: `user.role` in `authorize()` return value flows into `jwt` callback only on first sign-in (`if (user)` guard). Subsequent token refreshes use the persisted `token.role`.

---

## R-006: Route Protection Pattern

**Decision**: Export `auth` as default from `proxy.ts` with custom redirect logic and matcher.

**Pattern**:
```typescript
// proxy.ts (NOT middleware.ts — Next.js 16)
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
  // Logged in + correct role → pass through
})

export const config = {
  matcher: ["/dashboard/:path*", "/admin/:path*"]
}
```

**Matcher design**: Targets only protected paths. Public paths (`/`, `/support`, `/ticket/*`, `/api/*`, `/login`) are NOT in matcher — no auth check overhead on public routes.

---

## R-007: Login Page signIn Pattern

**Decision**: Client Component form submits via Server Action calling `signIn("credentials", ...)`.

**Pattern**:
```typescript
// Server Action in login/page.tsx (or separate actions.ts)
"use server"
import { signIn } from "@/auth"
import { AuthError } from "next-auth"
import { redirect } from "next/navigation"

export async function loginAction(formData: FormData) {
  try {
    const result = await signIn("credentials", {
      email: formData.get("email"),
      password: formData.get("password"),
      redirect: false  // handle redirect manually for role-based routing
    })
    // On success, check role and redirect appropriately
    // Role is available from auth() after signIn
  } catch (error) {
    if (error instanceof AuthError) {
      return { error: "Invalid email or password" }
    }
    throw error
  }
}
```

**Post-signIn redirect**: After successful `signIn()`, call `auth()` to get session, read `session.user.role`, then `redirect("/admin/dashboard")` or `redirect("/dashboard")`.

---

## R-008: Seed Script Pattern

**Decision**: Standalone TypeScript script using `tsx` runner; idempotent via existence check.

**Run**: `npx tsx scripts/seed.ts` from `src/web-form/`

**Pattern**:
```typescript
import bcrypt from "bcryptjs"
import { neon } from "@neondatabase/serverless"

const sql = neon(process.env.DATABASE_URL!)

async function seed() {
  const email = "admin@nexaflow.com"
  const [existing] = await sql`SELECT id FROM users WHERE email = ${email}`
  if (existing) {
    console.log("Admin user already exists — skipping")
    return
  }
  const hashed = await bcrypt.hash("Admin123!", 12)
  await sql`
    INSERT INTO users (name, email, hashed_password, role)
    VALUES ('NexaFlow Admin', ${email}, ${hashed}, 'admin')
  `
  console.log("Admin user created: admin@nexaflow.com")
}

seed().catch(console.error)
```
