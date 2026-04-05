# Feature Specification: Phase 4C-iii — NexaFlow Web Support Form

**Feature Branch**: `006-production-agent`
**Created**: 2026-04-05
**Status**: Draft
**Phase**: 4C-iii (Web Support Form — Next.js Frontend)

> **Predecessor:** Phases 4C-i (Gmail handler) and 4C-ii (WhatsApp handler) are complete. The
> production agent handles email and WhatsApp channels and publishes to `fte.tickets.incoming`.
> This phase adds the third and final intake channel: a browser-based support form that customers
> use to submit tickets and track resolution status. It is the **highest single scoring rubric item
> (10 points)** and the primary portfolio deliverable for LinkedIn.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Customer Submits a Support Ticket via Web Form (Priority: P1)

A NexaFlow customer visits the support form page, fills in their contact details, describes their
issue, selects a category and priority, and submits. They receive an immediate confirmation — a
ticket ID and a success toast — and are directed to a status tracking page.

**Why this priority**: This is the scored deliverable. Without a working form submission flow the
entire phase fails. Every other page depends on tickets created through this flow.

**Independent Test**: Navigate to `/support`. Fill all fields with valid data. Click Submit. Assert:
(a) submit button enters a "Submitting..." disabled state immediately on click, (b) within 3 seconds
a success toast appears containing a ticket ID in the format "Ticket #TKT-XXX created!", (c) clicking
the ticket ID in the toast navigates to `/ticket/[id]`, (d) the ticket status page loads with correct
details.

**Acceptance Scenarios**:

1. **Given** a customer on `/support` with all fields filled correctly, **When** they click Submit,
   **Then** the form immediately enters a disabled "Submitting..." state and a POST request is made
   to the ticket ingestion endpoint.

2. **Given** the POST succeeds with a ticket ID, **When** the response is received, **Then** a toast
   notification displays "Ticket #TKT-XXX created!" with the ticket ID as a clickable link, and a
   brief confetti animation plays.

3. **Given** the toast with ticket ID is shown, **When** the customer clicks the ticket ID link,
   **Then** they are navigated to `/ticket/[id]`.

4. **Given** the POST fails (network error or 5xx), **When** the error occurs, **Then** a toast
   shows the error message, all form field values are preserved (zero data loss), and the submit
   button re-enables so the customer can retry.

---

### User Story 2 — Customer Tracks Ticket Status in Real Time (Priority: P2)

A customer who has submitted a ticket visits `/ticket/[id]` to monitor progress. The page
displays their ticket details and automatically polls for status updates while the AI agent
processes it.

**Why this priority**: Without status visibility, customers re-submit or call support — defeating
the purpose of the system. Real-time feedback is essential for trust and reduced re-contact.

**Independent Test**: Navigate to `/ticket/[id]` with a valid ticket ID. Assert: (a) a skeleton
loader appears during the initial fetch, (b) ticket details render with the correct status badge
color, (c) when status is Open or In Progress an animated "AI is analyzing your ticket..."
indicator is visible, (d) the page polls every 5 seconds and updates the badge without a full
page reload, (e) visiting `/ticket/invalid-id` renders the not-found page with a link back to
`/support`.

**Acceptance Scenarios**:

1. **Given** a customer navigating to `/ticket/[id]`, **When** the page loads, **Then** a skeleton
   loader is shown while data is fetched, then replaced with: ticket ID, status badge, category,
   priority, submission timestamp, and original message body.

2. **Given** a ticket with status "Open" or "In Progress", **When** the status page is displayed,
   **Then** an animated "AI is analyzing your ticket..." typing indicator is visible.

3. **Given** a ticket whose status changes on the server, **When** the 5-second poll fires,
   **Then** the status badge updates to the new value and color without a full page reload.

4. **Given** a ticket ID that does not exist in the system, **When** the page is requested,
   **Then** the not-found view renders with a message and a link back to `/support`.

---

### User Story 3 — Support Manager Reviews Metrics on Dashboard (Priority: P3)

A NexaFlow support manager visits `/dashboard` to review current ticket volume, resolution rate,
and channel distribution without querying the database directly.

**Why this priority**: Operational visibility demonstrates end-to-end system integration and
showcases the multi-channel architecture to evaluators. It is not scored independently but
contributes to overall completeness.

**Independent Test**: Navigate to `/dashboard`. Assert: (a) four metric cards render (Total,
Open, Resolved, Escalation Rate), (b) a table shows the 10 most recent tickets with status
badges, (c) channel breakdown shows counts for Email / WhatsApp / Web Form, (d) all data
refreshes automatically after 30 seconds.

**Acceptance Scenarios**:

1. **Given** a manager on `/dashboard`, **When** the page loads, **Then** four cards display:
   Total Tickets, Open Tickets, Resolved Tickets, and Escalation Rate (percentage).

2. **Given** a manager on `/dashboard`, **When** the page renders, **Then** a table of the 10
   most recent tickets is shown with columns: Ticket ID, Channel, Status (color-coded), Priority,
   and relative submission time.

3. **Given** 30 seconds have elapsed since the last load, **When** the auto-refresh fires,
   **Then** all four metric cards and the recent tickets table update to reflect the latest data.

---

### User Story 4 — Visitor Lands on Homepage and Finds Support (Priority: P4)

A prospective or existing NexaFlow customer arrives at the root URL. They see a professional
brand-consistent landing page that communicates the AI support value proposition and provides
a clear path to submit a ticket.

**Why this priority**: The landing page sets the first impression and provides navigational
context. It demonstrates portfolio quality and reflects NexaFlow brand standards.

**Independent Test**: Navigate to `/`. Assert: (a) NexaFlow logo and tagline are visible, (b)
three feature cards are present, (c) "Get Support" CTA navigates to `/support`, (d) Framer
Motion entrance animations complete within 600ms.

**Acceptance Scenarios**:

1. **Given** a visitor arriving at `/`, **When** the page loads, **Then** the hero section
   fades in with the NexaFlow logo, tagline "Intelligent Customer Success Platform", and a
   "Get Support" CTA button.

2. **Given** the hero has loaded, **When** the entrance animation plays, **Then** three feature
   cards slide upward into view: "24/7 AI Support", "Multi-Channel", and "Smart Routing".

3. **Given** a visitor who clicks "Get Support", **When** the navigation occurs, **Then** they
   are taken to `/support`.

---

### Edge Cases

- What happens when a customer submits with an invalid email format? → Inline validation error
  appears on the email field before any network request is made; form is not submitted.
- What happens when the subject is fewer than 5 characters? → Inline error shown on the subject
  field; submission blocked.
- What happens when the message is fewer than 20 characters or more than 2000 characters? →
  Inline error with character count indicator; submission blocked.
- What happens when category or priority are not selected? → Inline required-field error shown;
  submission blocked.
- What happens when the ticket status endpoint is unreachable? → The `error.tsx` boundary
  renders with a "Try again" action that re-attempts the fetch.
- What happens when the dashboard metrics endpoint is unavailable? → `error.tsx` boundary
  renders; previously loaded data is not destroyed during the retry attempt.
- What happens on a 375px-wide mobile screen? → All pages render in single-column layout with
  no horizontal scrolling; form touch targets are at least 44×44px.
- What happens when the user has a system-level dark mode preference? → The dark theme is
  applied by default on first visit; the preference can be overridden via the theme toggle and
  the choice is persisted across sessions.

---

## Requirements *(mandatory)*

### Functional Requirements

**FR-001**: The system MUST provide a landing page at the root URL (`/`) that presents the
NexaFlow brand, a support value proposition, and a clear call-to-action navigating to the
support form.

**FR-002**: The landing page MUST display three feature cards with labels "24/7 AI Support",
"Multi-Channel", and "Smart Routing" to communicate system capabilities.

**FR-003**: The landing page MUST include animated entrance effects (hero fade-in, feature
cards slide-up) that complete within 600ms and respect the user's `prefers-reduced-motion`
setting.

**FR-004**: The system MUST provide a support form at `/support` with the following fields:
Full Name (text, required), Email Address (text, required, valid email format), Subject (text,
required, minimum 5 characters), Category (select, required; options: Billing / Technical /
Account / General), Priority (select, required; options: Low / Medium / High / Urgent),
Message (textarea, required, minimum 20 characters, maximum 2000 characters).

**FR-005**: The system MUST validate all six form fields client-side and display a field-level
inline error message for each violation before permitting submission.

**FR-006**: The system MUST display a live character count for the Message field that turns
red when the character limit is approached (≥1800) or exceeded.

**FR-007**: The system MUST disable the submit button and show a "Submitting..." label
immediately when the customer clicks Submit, preventing double-submission.

**FR-008**: On successful submission, the system MUST display a toast notification containing
the assigned ticket ID in the format "Ticket #TKT-XXX created!" where the ticket ID is
clickable and navigates to the ticket status page.

**FR-009**: On successful submission, the system MUST trigger a brief confetti animation as
positive reinforcement.

**FR-010**: On failed submission, the system MUST display a toast with the error message, and
MUST retain all field values so the customer can correct and resubmit without re-entering data.

**FR-011**: The system MUST provide a ticket status page at `/ticket/[id]` that displays:
ticket ID, status badge (color-coded: Open=blue, In Progress=yellow, Resolved=green,
Escalated=red), category, priority, submission timestamp, and original message body.

**FR-012**: The ticket status page MUST display a skeleton loader while the initial data fetch
is in progress.

**FR-013**: The ticket status page MUST poll the ticket status endpoint every 5 seconds and
update the displayed status without a full page reload.

**FR-014**: The ticket status page MUST display an animated "AI is analyzing your ticket..."
typing indicator when the ticket status is Open or In Progress.

**FR-015**: The ticket status page MUST render a dedicated not-found view with a link back to
`/support` when the ticket ID does not exist in the system.

**FR-016**: The system MUST provide a dashboard page at `/dashboard` displaying: a metrics
section with four stat cards (Total Tickets, Open Tickets, Resolved Tickets, Escalation Rate),
a recent tickets table (10 most recent, with status badges), and a channel breakdown showing
counts per channel (Email / WhatsApp / Web Form).

**FR-017**: The dashboard MUST auto-refresh all metrics and the recent tickets table every 30
seconds without a manual user action.

**FR-018**: Every page MUST include a persistent navigation bar with the NexaFlow logo and a
"Get Support" link navigating to `/support`.

**FR-019**: The system MUST support both a dark theme (default) and a light theme, switchable
via a visible toggle in the navigation bar, with the user's preference persisted across sessions.

**FR-020**: Every page MUST expose page-level metadata: a descriptive title, a meta
description, and Open Graph tags (og:title, og:description, og:type). Dynamic pages (e.g.,
`/ticket/[id]`) MUST generate metadata from their data content.

**FR-021**: Every route segment MUST include a dedicated error boundary (renders on unexpected
errors with a retry action) and a not-found handler (renders on missing resources with a
navigation link).

**FR-022**: All form fields MUST have associated labels, `aria-describedby` pointers to
validation messages, and be fully operable via keyboard (Tab/Shift-Tab for navigation, Enter
to submit, Escape to dismiss toast notifications).

**FR-023**: All pages MUST be mobile-first responsive, usable on screens 375px wide and above,
with no horizontal overflow and touch targets of at least 44×44px.

**FR-024**: The web form client MUST communicate with the FastAPI backend exclusively through
Next.js API route handlers (thin proxies). Direct browser-to-FastAPI requests are not permitted.

**FR-025**: The FastAPI backend MUST expose the following three endpoints for the web form
channel:
- `POST /api/web-form/tickets` — accept a validated form submission, persist the ticket, publish
  to `fte.tickets.incoming` Kafka topic, and return `{ ticket_id, status }`.
- `GET /api/web-form/tickets/{id}` — return the full ticket record or a 404 response.
- `GET /api/web-form/metrics` — return a metrics snapshot with total, open, resolved, escalation
  rate, and per-channel counts.

---

### Key Entities

- **Ticket**: A support request with fields: ID (TKT-XXX format), status (Open / In Progress /
  Resolved / Escalated), channel (web), category (Billing / Technical / Account / General),
  priority (Low / Medium / High / Urgent), customer name, customer email, subject, message body,
  and submission timestamp. Created by the FastAPI backend on form submission.

- **Form Submission**: Customer-provided input prior to ticket creation — contains name, email,
  subject, category, priority, message. Validated client-side before the proxy POST is made.
  Maps 1-to-1 to the `Ticket` entity upon success.

- **Metrics Snapshot**: An aggregated read-only view containing: total ticket count, open count,
  resolved count, escalation rate (%), and per-channel counts (email / whatsapp / web). Generated
  by the backend on each metrics request.

- **Theme Preference**: A user-level setting (dark / light) stored client-side, defaulting to
  dark. Does not require authentication; scoped to the browser session/storage.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

**SC-001**: A customer can navigate from the landing page to a submitted, confirmed ticket in
under 2 minutes on a standard broadband connection.

**SC-002**: All client-side form validation errors are surfaced before any network request is
made, with zero false positives for valid inputs.

**SC-003**: The ticket status page reflects a server-side status change within 10 seconds of
the change occurring (5-second poll interval + render time).

**SC-004**: All four pages achieve a Lighthouse score of 90 or above across Performance,
Accessibility, Best Practices, and SEO.

**SC-005**: The support form is fully operable via keyboard alone (Tab/Shift-Tab field
navigation, Enter to submit, Escape to dismiss toasts) with no mouse required.

**SC-006**: All pages render correctly and are fully usable on a 375px-wide viewport (iPhone SE
baseline) with no horizontal scrolling.

**SC-007**: Every page's title, description, and OG tags are correctly populated, confirmed by a
social-media preview tool or browser inspector.

**SC-008**: A failed form submission retains 100% of customer-entered field values — zero data
loss on error.

---

## Out of Scope

- User authentication or login for ticket submission or status tracking.
- Editing or deleting a submitted ticket.
- File or image attachment uploads.
- Email notification to the customer after submission (handled by the agent's `send_response`
  tool in a separate phase).
- Integration with external CRMs (Salesforce, HubSpot) — the PostgreSQL database is the CRM.
- Pagination of the recent tickets table beyond the 10 most recent rows.
- Admin authentication for the dashboard.

---

## Dependencies & Assumptions

### Dependencies

- **FastAPI backend** (`production/api/`): Three new endpoints are required (FR-025). These must
  be built in the implementation phase before the Next.js proxy routes can be validated end-to-end.
- **Kafka** (`fte.tickets.incoming`): Web form submissions MUST publish to the same unified topic
  as Gmail and WhatsApp so the agent processes all channels uniformly.
- **PostgreSQL** (`production/database/`): Ticket persistence and metrics aggregation queries.
- **Existing channel handlers** (Phases 4C-i, 4C-ii): Already complete; the web form handler
  follows the same publish-to-Kafka pattern.

### Assumptions

- The Next.js application resides at `src/web-form/` with its own `package.json` and
  `node_modules`, independent from the Python backend directory.
- The FastAPI base URL is supplied via the `NEXT_PUBLIC_API_URL` environment variable and is
  never hardcoded in source.
- Dark mode is the default; the theme toggle persists the preference via browser storage across
  sessions.
- The confetti animation is a one-time visual effect per submission; it is not triggered on
  page revisits or refreshes.
- The ticket ID format "TKT-XXX" (where XXX is a numeric or alphanumeric sequence) is
  generated server-side by the FastAPI backend — not by the frontend.
- No authentication is required for ticket submission, status tracking, or dashboard access in
  this phase.
- The dashboard is an internal demonstration tool; no access controls are implemented.
- Animations respect the browser's `prefers-reduced-motion` media query: motion is suppressed
  or minimised for users who have opted out of animations.

---

## Context7 Research Notes

> Confirmed before spec was written. Findings:

1. **Next.js 15 `generateMetadata`** — Async function signature: `generateMetadata({ params,
   searchParams }: Props): Promise<Metadata>`. `params` is a `Promise<{ id: string }>` in
   dynamic routes. `Metadata` type accepts `title`, `description`, `openGraph` (with nested
   `images[]`). Must be exported from `page.tsx` alongside the default page component.

2. **shadcn/ui Form + React Hook Form + Zod** — Pattern: define `z.object()` schema → pass to
   `zodResolver` → `useForm({ resolver: zodResolver(schema), defaultValues: {...} })`. Field
   errors surface via `form.formState.errors`. shadcn `<Form>`, `<FormField>`, `<FormItem>`,
   `<FormLabel>`, `<FormMessage>` components wrap RHF's `Controller` for accessible validation
   messages.

3. **Framer Motion entrance animations** — `motion.div` accepts `initial`, `animate`, `exit`,
   and `transition` props. Fade-in: `initial={{ opacity: 0 }} animate={{ opacity: 1 }}`.
   Slide-up: `initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}`. `AnimatePresence`
   wraps conditionally rendered elements for exit animations.

4. **Next.js API proxy to backend** — Two approaches: (a) `rewrites()` in `next.config.ts` for
   transparent URL rewriting; (b) explicit API route handler at `app/api/[route]/route.ts` that
   `fetch()`es `process.env.NEXT_PUBLIC_API_URL + path` and returns the proxied response. The
   explicit handler (b) is preferred here because it allows request/response transformation and
   error normalisation before the client receives the data.
