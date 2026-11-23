-- Durable hearing /process jobs + organisation-scoped contacts (apply after 003).
--
-- haki_hearing_jobs: one row per /process request. Workers claim a row with a
-- conditional UPDATE (status + attempts in the WHERE clause) and renew
-- lease_expires_at while they run; an expired lease means the worker died and
-- any other worker may claim the job again (app.services.hearing_jobs).
--
-- haki_contacts: the production counterpart of the demo /contacts store.
--
-- ROLLBACK:
--   drop policy if exists "contacts member" on public.haki_contacts;
--   drop policy if exists "hearing_jobs member read" on public.haki_hearing_jobs;
--   drop table if exists public.haki_contacts;
--   drop table if exists public.haki_hearing_jobs;

create table if not exists public.haki_hearing_jobs (
  id uuid primary key default gen_random_uuid(),
  hearing_id uuid not null references public.haki_hearings(id) on delete cascade,
  organisation_id uuid not null references public.haki_organisations(id) on delete cascade,
  workspace_id uuid not null references public.haki_workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id),
  params jsonb not null default '{}'::jsonb,
  status text not null default 'queued' check (status in ('queued', 'running', 'done', 'error')),
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 3 check (max_attempts >= 1),
  worker_id text,
  lease_expires_at timestamptz,
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- At most one queued/running job per hearing, even with concurrent requests.
create unique index if not exists haki_hearing_jobs_one_active
  on public.haki_hearing_jobs (hearing_id)
  where status in ('queued', 'running');
create index if not exists haki_hearing_jobs_runnable_idx
  on public.haki_hearing_jobs (status, created_at)
  where status in ('queued', 'running');
create index if not exists haki_hearing_jobs_org_idx
  on public.haki_hearing_jobs (organisation_id, created_at desc);

create table if not exists public.haki_contacts (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.haki_organisations(id) on delete cascade,
  matter_id uuid references public.haki_matters(id) on delete set null,
  name text not null check (char_length(trim(name)) between 1 and 200),
  updates jsonb not null default '{}'::jsonb,
  session_ids uuid[] not null default '{}',
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists haki_contacts_org_idx on public.haki_contacts (organisation_id, created_at desc);
create index if not exists haki_contacts_matter_idx on public.haki_contacts (matter_id);

alter table public.haki_hearing_jobs enable row level security;
alter table public.haki_contacts enable row level security;

-- Members may read their organisation's job history; only the backend's
-- service role (which bypasses RLS) writes jobs.
create policy "hearing_jobs member read"
  on public.haki_hearing_jobs for select
  using (public.haki_active_member(organisation_id));

create policy "contacts member"
  on public.haki_contacts for all
  using (public.haki_active_member(organisation_id))
  with check (public.haki_active_member(organisation_id));
