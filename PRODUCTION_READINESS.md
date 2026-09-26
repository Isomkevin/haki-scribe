# HakiScribe Production Readiness Plan

## Current assessment

HakiScribe is **not ready to hold real client or court data** in its present demo configuration. The product workflow is strong, but the current identity and storage model is intentionally demo-grade:

- accounts are configured server-side rather than managed as persistent user identities;
- authentication state is stored in browser local storage;
- there is no password reset, email verification, lockout policy, MFA, device/session management, or audit trail;
- all signed-in users share one workspace and case library;
- existing data records do not yet carry an enforceable firm or user ownership boundary.

Production readiness requires a migration, not incremental UI changes. Every session, transcript, generated artifact, matter, contact, connector credential, file, background task, and cache entry must have an authenticated and enforced ownership scope.

## Target tenancy model

Use three layers of ownership:

| Layer | Meaning | Examples |
| --- | --- | --- |
| User | A natural person with a verified account | Advocate, clerk, partner, administrator |
| Firm / organisation | The paying legal practice and primary security boundary | A law firm, legal-aid organisation, court registry |
| Workspace / matter access | A scoped collaboration boundary within a firm | Litigation team, client/matter team, restricted matter |

### Roles

Start with four firm roles:

- **Owner** — billing, firm security policy, user administration, data export/deletion approval.
- **Administrator** — invites, memberships, workspace administration; no implicit access to restricted matter content.
- **Lawyer** — create and work on matters and sessions they have been granted.
- **Staff / clerk** — limited capture, review, and drafting permissions defined by a matter/workspace grant.

Do not use frontend visibility as authorization. The server must derive firm and membership from the authenticated identity, then authorise every operation.

## Recommended technical architecture

1. Move from local JSON/demo storage to managed Postgres before onboarding any real firm.
2. Add `organisations`, `users`, `memberships`, `workspaces`, and `matter_memberships`.
3. Add `organisation_id`, creator identity, and appropriate workspace/matter scope to every tenant-owned table.
4. Enforce Postgres Row Level Security for normal application access, with policies based on the authenticated user's active membership.
5. Use a non-superuser database role for normal requests; background jobs must re-establish verified tenant scope before reading or writing.
6. Include tenant scope in object-storage keys, signed URL checks, cache keys, queues, rate limits, logs, and analytics.
7. Use a managed identity provider rather than designing password, email verification, MFA, reset, token rotation, and recovery from scratch. A suitable provider must support OIDC, WebAuthn/passkeys, TOTP, recovery codes, email verification, password reset, session revocation, and audit events.

OWASP recommends deriving tenant context from a server-verified identity and enforcing it at every tenant-owned access path; Row Level Security can provide defence in depth. [OWASP Multi-Tenant Security guidance](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html)

## Authentication and account lifecycle

### Required before production

- Email verification before firm access.
- Password hashing handled by the identity provider; never store plaintext or reversible passwords.
- Password reset through a single-use, short-lived, purpose-limited token; use the same response whether an email exists or not to prevent account enumeration.
- Rate limits and abuse detection for login, reset, verification, invitation, and MFA challenges.
- Session rotation on login, password reset, MFA enrollment/reset, and privilege changes.
- Secure, `HttpOnly`, `Secure`, `SameSite` cookies for browser sessions instead of local-storage bearer tokens.
- Session/device listing and remote sign-out.
- Audit events for login, failed login, reset request/completion, MFA change, invitation, role change, export, deletion, and connector authorization.

### MFA / 2FA

Require MFA for owners and administrators at launch; make it mandatory for all users handling privileged data after rollout.

Preferred order of factors:

1. Passkeys / WebAuthn.
2. Authenticator-app TOTP.
3. One-time recovery codes, shown once and stored only as hashes.

Do not rely on security questions. SMS should be a fallback only, not the primary factor. MFA-factor reset must require a hardened recovery flow and generate an audit event. OWASP specifically calls out secure MFA reset and session management as essential controls. [OWASP MFA guidance](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html), [session guidance](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)

## Data protection controls

- Encrypt data in transit and at rest; use managed key management and document key rotation.
- Apply a configurable retention policy for transcripts, recordings, generated drafts, and backups.
- Provide firm-authorised export and deletion workflows with an immutable audit record.
- Minimise model-provider data: send only the approved non-redacted transcript segment required for the chosen task.
- Maintain processor agreements, a data inventory, an incident-response process, and a lawful-basis/consent record appropriate to the deployment jurisdiction.
- Never write transcript text, credentials, reset tokens, or raw provider payloads to application logs.

## Delivery phases

### Phase 0 — Production design and safety gate

- Select identity provider and transactional email provider.
- Define firm/matter roles, retention periods, consent process, and incident owner.
- Freeze onboarding of real legal data until Phase 2 is complete.
- Create a migration and rollback plan from demo storage.

### Phase 1 — Identity foundation

- Implement managed sign-up/sign-in, verification, password reset, secure cookie sessions, logout-all-devices, and account deletion request.
- Remove demo credentials and browser-local token persistence from production builds.
- Add audit logging and rate limiting.

### Phase 2 — Firm tenancy and isolation

- Create organisation, membership, invitation, role, workspace, and matter-membership models.
- Migrate every existing record to a tenant-owned schema.
- Implement server-side ownership checks and Postgres RLS policies.
- Require `X-Haki-Organisation` only as a requested context; validate it
  server-side against the authenticated user's active membership before any
  tenant-scoped route reads or writes data.
- Add automated negative tests proving one firm cannot read, modify, export, stream, or enumerate another firm's data.

### Phase 3 — MFA and administrative controls

- Roll out passkeys/TOTP, recovery codes, enforced MFA policy, device/session administration, and step-up authentication for sensitive actions.
- Add firm onboarding, user invitations, offboarding, role review, and connector ownership controls.

### Phase 4 — Operational readiness

- Configure production backups, restore drills, monitoring, alerting, vulnerability/dependency scanning, and incident response.
- Perform independent security review and tenant-isolation penetration testing.
- Pilot with one firm using synthetic or explicitly consented low-risk data before broad release.

## Production release gates

HakiScribe may accept real legal-client data only when all items below are true:

- [ ] Postgres-backed storage and backups are live.
- [ ] Every tenant-owned record has an enforced organisation scope.
- [ ] Cross-firm access regression tests pass for REST, WebSocket, background jobs, files, cache, exports, and connectors.
- [ ] Managed identity, verified email, reset, session revocation, and MFA are enabled.
- [ ] No production access token is stored in browser local storage.
- [ ] Consent, retention, deletion/export, audit logging, and incident response are operational.
- [ ] OAuth/provider credentials are tenant-scoped or explicitly firm-scoped.
- [ ] A security review and restore drill have been completed.
- [ ] The demo account and seeded demo data are disabled in production.

## Implemented foundation (not a release approval)

The repository now includes a deliberately separate production path while the
existing demo remains usable:

- `hakiscribe-backend/migrations/001_tenant_security.sql` creates the firm,
  membership, workspace, matter, session, immutable session-record, and audit
  tables, plus Row Level Security policies.
- Production identity is verified against Supabase Auth in
  `app/services/production_auth.py`; it rejects unverified-email accounts.
- The organisation and workspace headers are only requested context. Their
  membership and ownership are checked by the backend in
  `app/services/tenant_context.py` before a production route can use them.
- `POST /organisations`, `/production/workspaces`, and `/production` bootstrap
  a firm, its workspace, and a tenant-backed session. Session records live at
  `/production/{session_id}/records` and are protected from cross-firm and
  restricted-matter access. Workspace creation is restricted to an owner or
  administrator; session records are append-only at the database policy layer.
- The production Auth BFF (`/auth/production/*`) uses Secure, HttpOnly access
  and refresh cookies, a double-submit CSRF token for writes, password reset
  initiation, password update, session refresh/logout, and the Supabase TOTP
  enrollment/challenge/verification sequence. It deliberately has no route
  that returns an access token to browser JavaScript.
- An owner or administrator must have an `aal2` (MFA-verified) token before
  administering workspaces. Initial firm creation is intentionally allowed at
  `aal1` so a new user can create the firm before completing MFA enrolment.
- `HAKISCRIBE_PRODUCTION_AUTH=false` preserves the existing demo workflow.
  When it is set to `true`, production routes require a Supabase bearer token;
  browser CORS is deny-by-default until `HAKISCRIBE_ALLOWED_ORIGINS` is set.

This foundation does **not** yet move the legacy UI, WebSocket streams,
background detection jobs, object storage, exports, connectors, or old records
onto those controls. Do not enable real legal-data onboarding until each route
and data path has been migrated and the release gates above are evidenced.

## Safe enablement sequence

1. Create a separate Supabase production project. Apply
   `hakiscribe-backend/migrations/001_tenant_security.sql` there via the
   Supabase CLI or SQL editor, then verify the tables and RLS policies.
2. Configure Supabase Auth: verified-email sign-up, reset-email redirect URLs,
   password policy, TOTP MFA, recovery-code policy, and appropriate rate
   limits. Put only the anon/publishable key in the frontend; keep the service
   role key in the backend secret store.
3. Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, and exact
   `HAKISCRIBE_ALLOWED_ORIGINS` on the backend. Set
   `HAKISCRIBE_PASSWORD_RESET_URL` to the exact public reset page and add it
   under Supabase Auth redirect URLs. Set
   `HAKISCRIBE_PRODUCTION_AUTH=true` only in that production environment.
4. Run cross-firm negative tests before deployment: a member of Firm A must be
   unable to list, retrieve, append a record to, or alter a Firm B session;
   the same must hold for restricted matters inside a firm.
5. Migrate the frontend endpoint-by-endpoint from the demo API to the
   production API, then remove the demo routes and seed credentials from the
   production deployment.

## Decisions required from HakiChain

1. Identity provider: choose a managed provider or approve building/operating identity infrastructure.
2. Tenant model: confirm whether firms can have restricted internal matter workspaces and whether court/registry organisations need a separate model.
3. Hosting and database: approve managed Postgres and object storage suitable for privileged data.
4. MFA policy: decide whether MFA is required from the first production user or phased by role.
5. Retention and jurisdiction: approve legal-data retention, deletion, breach, and processor requirements with counsel.

## References

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Forgot Password Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
- [OWASP Multi-Tenant Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multi_Tenant_Security_Cheat_Sheet.html)
