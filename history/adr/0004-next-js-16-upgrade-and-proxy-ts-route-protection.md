# ADR-0004: Next.js 16 Runtime — proxy.ts Route Protection and Node.js Default Runtime

- **Status:** Accepted
- **Date:** 2026-04-09
- **Feature:** 011-auth (Phase 7A — NextAuth.js v5 Auth + RBAC)
- **Context:** During Phase 7A planning, we confirmed that Next.js 16.2.2 is installed in `src/web-form/` (not Next.js 15 as recorded in constitution §VI). Next.js 16 introduced two breaking changes that directly impact the auth implementation: (1) `middleware.ts` is renamed to `proxy.ts` and (2) the default runtime for that file changed from Edge to Node.js. These changes affect how route protection is implemented and whether Edge-runtime compatibility workarounds (common in NextAuth v5 documentation for v14/v15) are required. The decision cluster covers: the version to use in production, the file name convention, the runtime choice, and whether to split NextAuth config for Edge compatibility.

## Decision

**Use Next.js 16.2.2 as-is, with `proxy.ts` and Node.js runtime.**

- **Runtime File**: `proxy.ts` at `src/web-form/proxy.ts` (renamed from `middleware.ts` in Next.js 16)
- **Runtime**: Node.js (Next.js 16 default for proxy.ts — no Edge runtime)
- **NextAuth config split**: `auth.config.ts` (providers-only, nominally Edge-safe) + `auth.ts` (full config with bcryptjs and DB — Node.js runtime)
- **No downgrade**: Stay on 16.2.2; no rollback to 15.x
- **Constitution update**: §VI frontend entry will be updated from "Next.js 15" to "Next.js 16.2.2" in a follow-up amendment
- **Turbopack**: Default in Next.js 16 for `next dev`; no action required (backward compatible with existing config)

## Consequences

### Positive

- **Eliminates Edge runtime restrictions**: `bcryptjs`, `@neondatabase/serverless`, and full Node.js APIs are available directly in `proxy.ts`. No Edge-compatible workarounds (e.g., `jose` instead of `jsonwebtoken`, no `crypto` polyfills) are needed.
- **Simpler NextAuth setup**: The NextAuth v5 "split config" pattern (auth.config.ts for Edge + auth.ts for Node.js) is still used as best practice, but the split is not technically mandatory — proxy.ts runs on Node.js in all environments.
- **Turbopack dev speed**: `next dev` now uses Turbopack by default — faster cold-start HMR during development.
- **Long-term alignment**: Next.js 16 is the current stable release; staying current avoids accumulating upgrade debt.
- **Explicit error surface**: If `proxy.ts` is missing or misconfigured, Next.js 16 will not silently fall back to `middleware.ts` — the failure is observable.

### Negative

- **Breaking rename risk**: Any tooling, documentation, or team member expecting `middleware.ts` will find a missing file. Must document prominently in CLAUDE.md and quickstart.md.
- **Constitution version drift**: The constitution (§VI) records "Next.js 15 App Router" — this creates a documentation inconsistency that must be resolved via a constitution amendment.
- **next-auth@beta + Next.js 16**: NextAuth v5 (`next-auth@beta`) is tested against Next.js 14/15. Next.js 16 compatibility is not explicitly documented in the NextAuth changelog as of this writing; peer dependency resolution may require `--legacy-peer-deps` or a specific beta version pin.
- **Turbopack gotchas**: Turbopack is still marked "stable but evolving" — rare build-time differences from Webpack may surface. Low likelihood, but must verify `next build` (which still uses Webpack) matches `next dev` behavior.
- **Proxy terminology confusion**: Next.js renamed "middleware" to "proxy" in docs/config, but the underlying behavior is similar. Developers familiar with Next.js 14/15 middleware docs must be briefed on the rename.

## Alternatives Considered

### Alternative A: Downgrade to Next.js 15.x
- **Approach**: Pin `"next": "15.x"` in package.json; keep `middleware.ts` naming; use established Next.js 15 + NextAuth v5 patterns.
- **Why rejected**: The codebase already runs on 16.2.2 (no known issues). Downgrading introduces risk of breaking existing features that depend on 16.x behavior. The only gain would be more NextAuth documentation alignment — not worth the regression risk.

### Alternative B: Stay on Next.js 16 but use Edge runtime for proxy.ts
- **Approach**: Add `export const runtime = "edge"` to proxy.ts; use `jose` for JWT verification instead of bcryptjs; split config strictly.
- **Why rejected**: Next.js 16's default is now Node.js for proxy.ts. Forcing Edge runtime adds complexity (no bcryptjs, no native Neon client) with no benefit — the Edge runtime advantage (globally distributed execution) is irrelevant for an internal NexaFlow portal with ~50 users.

### Alternative C: Replace NextAuth v5 with a custom JWT auth solution
- **Approach**: Implement custom sign-in endpoint, JWT generation with `jose`, and session cookie management without a third-party auth library.
- **Why rejected**: NextAuth v5 provides battle-tested CSRF protection, session management, and credential handling. Building equivalent security from scratch introduces risk and maintenance burden disproportionate to the feature scope.

### Alternative D: Keep middleware.ts and add a Next.js config shim
- **Approach**: Some community workarounds configure `next.config.ts` to process `middleware.ts` under the hood.
- **Why rejected**: No official support from Next.js team. Silent failure risk is high — if the shim breaks on upgrade, routes appear protected in dev but are exposed in production with no error.

## References

- Feature Spec: `specs/011-auth/spec.md`
- Implementation Plan: `specs/011-auth/plan.md` (§ R-001, Block B3)
- Research: `specs/011-auth/research.md` (R-001: Next.js 16 proxy.ts Rename, R-006: Route Protection Pattern)
- Related ADRs: None — no prior frontend platform ADRs exist
- Context7 source: "As of Next.js 16, `middleware.ts` has been renamed to `proxy.ts` and now runs on the Node.js runtime instead of the edge runtime."
