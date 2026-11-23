# Production database migrations

`001_tenant_security.sql` establishes the production tenancy boundary for a Supabase Postgres project. It is not used by demo mode and must be applied before enabling `HAKISCRIBE_PRODUCTION_AUTH=true`.

`002_provider_settings_ai_runs.sql` adds Nebius/Nemotron `provider_settings` (no API keys) and metadata-only `ai_runs` with RLS. Demo mode mirrors these via in-process ledgers (`app.services.provider_settings`, `app.services.ai_runs`).

`003_hearings_matter_resolution.sql` adds virtual-court `haki_hearings`, match candidates, and confirmation audit tables. Demo mode mirrors these via `app.services.hearings`.

`004_hearing_jobs_contacts.sql` adds `haki_hearing_jobs` (durable `/process` queue: lease + heartbeat, at most one active job per hearing via a partial unique index) and org-scoped `haki_contacts` used by `/production/contacts`. Demo mode mirrors these via `app.services.hearings._jobs` and the snapshot contacts store.

## Apply

1. Back up the target database.
2. Run `001_tenant_security.sql`, then `002_provider_settings_ai_runs.sql`, then `003_hearings_matter_resolution.sql`, then `004_hearing_jobs_contacts.sql`, in the Supabase SQL Editor or through the Supabase CLI against the production project.
3. Create the first organisation and owner membership using an audited, server-side onboarding flow.
4. Run cross-tenant tests before migrating any real matter data.

Do not point the current shared JSON snapshot store at real client data. The next application migration replaces route-level storage calls with these tenant-scoped tables.
