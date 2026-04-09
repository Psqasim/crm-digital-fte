# Feature Specification: NextAuth.js v5 Auth + RBAC

**Feature Branch**: `011-auth`  
**Created**: 2026-04-09  
**Status**: Draft  
**Phase**: 7A

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Internal Staff Login (Priority: P1)

An internal NexaFlow team member (admin or agent) navigates to `/login`, enters their email and password, and is redirected to their role-appropriate dashboard. The login page is not publicly advertised — no signup link is shown.

**Why this priority**: Authentication is the foundation gate. Without it, no role-based access, dashboard protection, or user management is possible.

**Independent Test**: Can be fully tested by visiting `/login`, entering valid credentials (`admin@nexaflow.com / Admin123!`), and confirming redirection to `/admin/dashboard`.

**Acceptance Scenarios**:

1. **Given** a visitor is on `/login`, **When** they enter valid admin credentials, **Then** they are redirected to `/admin/dashboard` and the navbar shows role-based links + Logout.
2. **Given** a visitor is on `/login`, **When** they enter valid agent credentials, **Then** they are redirected to `/dashboard` and the navbar shows agent links + Logout.
3. **Given** a visitor is on `/login`, **When** they enter incorrect credentials, **Then** an inline error message is displayed and no redirect occurs.
4. **Given** a user is already logged in, **When** they navigate to `/login`, **Then** they are redirected to their dashboard (no re-login loop).

---

### User Story 2 — Route Protection & Redirect (Priority: P2)

An unauthenticated visitor attempts to access a protected internal route (`/dashboard` or `/admin/*`). They are automatically redirected to `/login` without seeing any protected content. Public routes (`/`, `/support`, `/ticket/*`) remain accessible to anyone.

**Why this priority**: Security boundary — no internal data should be visible without authentication.

**Independent Test**: Can be fully tested by directly visiting `/dashboard` while not logged in and confirming a redirect to `/login` occurs.

**Acceptance Scenarios**:

1. **Given** an unauthenticated user, **When** they navigate to `/dashboard`, **Then** they are redirected to `/login` immediately.
2. **Given** an unauthenticated user, **When** they navigate to `/admin/dashboard`, **Then** they are redirected to `/login` immediately.
3. **Given** an authenticated agent, **When** they navigate to `/admin/dashboard`, **Then** they are redirected to `/dashboard` (role mismatch blocked).
4. **Given** any user (authenticated or not), **When** they visit `/`, `/support`, or `/ticket/*`, **Then** the page renders normally without any auth requirement.

---

### User Story 3 — Admin: User Management (Priority: P3)

An authenticated admin visits `/admin/dashboard`. They see all support tickets and a "Create User" form allowing them to provision new agent or admin accounts. No self-service signup exists — only admins can create accounts.

**Why this priority**: Enables team onboarding without exposing public registration.

**Independent Test**: Can be fully tested by logging in as admin, navigating to `/admin/dashboard`, creating a new agent account, then logging in as that agent and verifying `/dashboard` access.

**Acceptance Scenarios**:

1. **Given** an admin on `/admin/dashboard`, **When** they fill in name, email, password, and role then submit, **Then** a new user account is created and confirmation is shown.
2. **Given** an admin on `/admin/dashboard`, **When** they submit a create-user form with an email that already exists, **Then** an error is shown and no duplicate is created.
3. **Given** an admin on `/admin/dashboard`, **When** they view the tickets table, **Then** all tickets from all channels are displayed with status and priority.

---

### User Story 4 — Agent: Assigned Ticket Dashboard (Priority: P4)

An authenticated agent visits `/dashboard`. They see a filtered view of tickets (metrics and recent tickets relevant to their work). The dashboard includes an auth guard — if the session expires mid-session, the user is redirected to `/login`.

**Why this priority**: Agents need a personalized, access-controlled view distinct from public-facing pages.

**Independent Test**: Can be fully tested by logging in as an agent and confirming the dashboard loads with ticket data, and that the Logout button ends the session.

**Acceptance Scenarios**:

1. **Given** an authenticated agent, **When** they visit `/dashboard`, **Then** the page loads with ticket metrics and the navbar shows "Dashboard" link + Logout.
2. **Given** an authenticated agent with an expired session, **When** they navigate to any protected route, **Then** they are redirected to `/login`.
3. **Given** an authenticated agent on `/dashboard`, **When** they click Logout, **Then** the session is cleared and they are redirected to `/login`.

---

### User Story 5 — Navbar Auth State (Priority: P5)

The global navbar adapts based on authentication state. Unauthenticated visitors see a "Login" button. Authenticated users see role-appropriate navigation links and a "Logout" button. The "Dashboard" link is hidden from unauthenticated visitors.

**Why this priority**: Navigation clarity prevents confusion and prevents users from discovering protected links they cannot access.

**Independent Test**: Can be fully tested by checking navbar in logged-out state (shows Login), then logging in and confirming role-based links appear.

**Acceptance Scenarios**:

1. **Given** an unauthenticated user on any page, **When** the page loads, **Then** the navbar shows a "Login" button and no dashboard or admin links.
2. **Given** an authenticated admin, **When** viewing any page, **Then** the navbar shows links: Home, Admin Dashboard, Get Support, and Logout.
3. **Given** an authenticated agent, **When** viewing any page, **Then** the navbar shows links: Home, Dashboard, Get Support, and Logout.

---

### Edge Cases

- What happens when the admin tries to delete the only admin account? The system must reject the deletion/deactivation (out of scope for this phase — addressed in future user management spec).
- What happens when the JWT secret changes? All existing sessions are invalidated immediately — users are redirected to `/login`.
- What happens when a seed script is run twice? The script must be idempotent — existing admin account is not duplicated; a `upsert` or existence check is used.
- What happens when a user accesses `/login` with a valid token cookie? They are redirected to their role-appropriate dashboard without re-entering credentials.
- What happens when the database is unavailable during login? A user-friendly error message is shown — "Service temporarily unavailable. Please try again shortly."

---

## Requirements *(mandatory)*

### Functional Requirements

**Authentication**

- **FR-001**: System MUST authenticate internal users via email and password credentials only — no public OAuth, no public signup.
- **FR-002**: System MUST validate credentials against a `users` table in the existing Neon PostgreSQL database.
- **FR-003**: System MUST store passwords as cryptographic hashes — plaintext passwords must never be persisted or logged.
- **FR-004**: System MUST issue a signed token containing user identity and role upon successful authentication.
- **FR-005**: System MUST share its token signing secret with the FastAPI backend, enabling cross-service token verification.
- **FR-006**: System MUST support session strategy via token-only (no server-side session storage in the database).

**Route Protection**

- **FR-007**: System MUST redirect any unauthenticated request to `/dashboard` or `/admin/*` to `/login`.
- **FR-008**: System MUST redirect authenticated agents who attempt to access `/admin/*` to `/dashboard`.
- **FR-009**: System MUST allow unauthenticated access to `/`, `/support`, `/ticket/*`, and `/login` without redirection.
- **FR-010**: System MUST re-validate the session on each protected page load — expired tokens must trigger a redirect to `/login`.

**Login Page**

- **FR-011**: System MUST provide a `/login` page with email and password fields, validated client-side before submission.
- **FR-012**: The login page MUST display inline validation errors (empty fields, invalid email format, wrong credentials).
- **FR-013**: The login page MUST NOT include a "Create Account" or "Sign Up" link — account creation is admin-only.
- **FR-014**: The login page MUST match the existing dark theme (`#0F172A` background, slate palette, blue accent).

**Admin Dashboard**

- **FR-015**: System MUST provide an `/admin/dashboard` page accessible only to users with `admin` role.
- **FR-016**: The admin dashboard MUST display all support tickets with columns: Ticket ID, Channel, Category, Priority, Status, Timestamp.
- **FR-017**: The admin dashboard MUST include a "Create User" form with fields: Full Name, Email, Password, Role (admin | agent).
- **FR-018**: The "Create User" form MUST validate inputs client-side (required fields, email format, password minimum length of 8 characters).
- **FR-019**: System MUST prevent duplicate email addresses when creating users — duplicate attempts return an error.

**Agent Dashboard**

- **FR-020**: The existing `/dashboard` page MUST be updated to require authentication.
- **FR-021**: The `/dashboard` page MUST remain functionally equivalent for authenticated agents — ticket metrics and recent ticket table are preserved.

**Navbar**

- **FR-022**: The Navbar MUST display a "Login" button linking to `/login` when the user is not authenticated.
- **FR-023**: The Navbar MUST display role-appropriate navigation links and a "Logout" button when the user is authenticated.
- **FR-024**: Admin navbar links: Home, Admin Dashboard (`/admin/dashboard`), Get Support, Logout.
- **FR-025**: Agent navbar links: Home, Dashboard (`/dashboard`), Get Support, Logout.

**User Account Seeding**

- **FR-026**: A seed script MUST create a default admin account: email `admin@nexaflow.com`, password `Admin123!`, role `admin`, name `NexaFlow Admin`.
- **FR-027**: The seed script MUST be idempotent — running it multiple times must not create duplicate accounts.

### Key Entities

- **User**: An internal NexaFlow staff member with fields: unique identifier, full name, email address (unique), hashed password, role (admin or agent), account creation timestamp.
- **Session Token**: A short-lived cryptographically signed token containing user identity (ID, email, name) and role claim. No server-side session record is stored. Shared secret with FastAPI backend enables cross-service verification.
- **Role**: An enumeration with exactly two values — `admin` (full access including user management) and `agent` (dashboard access only).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Internal staff can complete the login flow (navigate to `/login` → enter credentials → reach dashboard) in under 10 seconds on a standard connection.
- **SC-002**: 100% of unauthenticated requests to `/dashboard` or `/admin/*` result in a redirect to `/login` — zero protected content is served without a valid session.
- **SC-003**: An authenticated admin can create a new user account from `/admin/dashboard` in under 2 minutes without leaving the page.
- **SC-004**: The seed script completes setup of the default admin account in under 5 seconds and is safe to re-run without side effects.
- **SC-005**: Public routes (`/`, `/support`, `/ticket/*`) load without any authentication requirement — zero regressions for public-facing users.
- **SC-006**: The Navbar correctly reflects authentication state on 100% of page loads — no flash of incorrect nav state.
- **SC-007**: An agent logging out is fully de-authenticated within 1 interaction (single click on Logout), with no ability to access protected routes without re-authenticating.

---

## Assumptions

- Next.js 16.2.2 is installed (confirmed). In Next.js 16+, route protection is handled via `proxy.ts` (formerly `middleware.ts`) running on the Node.js runtime.
- NextAuth.js v5 (`next-auth@5.x`) is not yet installed — it will be added in the implementation phase.
- The Neon PostgreSQL database already has the connection string available in environment variables. The `users` table does not yet exist and will be created via migration.
- `bcrypt` or equivalent cryptographic hashing is used for passwords — the exact library choice is an implementation detail.
- The JWT secret is a new environment variable (`AUTH_SECRET`) stored in `.env.local` and shared with the FastAPI backend via `NEXTAUTH_SECRET` / `AUTH_SECRET` environment variables.
- Existing dashboard (`/dashboard`) currently has no auth guard — this feature adds one without breaking the metrics/tickets display.
- shadcn/ui components and Zod are already installed in `src/web-form/`.
- No email verification flow is required for this phase — admin-created accounts are immediately active.
- Session token expiry defaults to NextAuth.js defaults (30 days) — configurable in a future phase if needed.

---

## Out of Scope

- OAuth / social login providers (Google, GitHub, etc.)
- Public user self-registration
- Password reset / forgot password flow
- Two-factor authentication (2FA)
- Audit logging of login events
- User deactivation / deletion
- Pagination or search in the admin tickets table (future enhancement)
- Email notifications on account creation
