# Production database migrations

`001_tenant_security.sql` establishes the production tenancy boundary for a Supabase Postgres project. It is not used by demo mode and must be applied before enabling `HAKISCRIBE_PRODUCTION_AUTH=true`.

## Apply

1. Back up the target database.
2. Run the SQL in the Supabase SQL Editor or through the Supabase CLI against the production project.
3. Create the first organisation and owner membership using an audited, server-side onboarding flow.
4. Run cross-tenant tests before migrating any real matter data.

Do not point the current shared JSON snapshot store at real client data. The next application migration replaces route-level storage calls with these tenant-scoped tables.
