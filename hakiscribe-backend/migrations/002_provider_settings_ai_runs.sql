-- HakiScribe provider_settings + ai_runs for Nebius / Nemotron observability.
-- Apply after 001_tenant_security.sql. Do not store raw API keys here.
--
-- ROLLBACK:
--   drop policy if exists "provider_settings member" on public.provider_settings;
--   drop policy if exists "ai_runs member read" on public.ai_runs;
--   drop policy if exists "ai_runs member insert" on public.ai_runs;
--   drop table if exists public.ai_runs;
--   drop table if exists public.provider_settings;

create table if not exists public.provider_settings (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.haki_organisations(id) on delete cascade,
  provider text not null,
  base_url text,
  ultra_model text,
  super_model text,
  nano_model text,
  enabled boolean not null default true,
  default_for_tasks jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now(),
  unique (organisation_id, provider)
);

create table if not exists public.ai_runs (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid references public.haki_organisations(id) on delete set null,
  session_id uuid references public.haki_sessions(id) on delete set null,
  task text not null,
  provider text not null,
  model_id text not null,
  latency_ms integer,
  status text not null default 'ok',
  privileged_lines_excluded integer not null default 0,
  created_at timestamptz not null default now()
  -- Intentionally no transcript / prompt / response columns.
);

create index if not exists ai_runs_org_idx on public.ai_runs (organisation_id, created_at desc);
create index if not exists ai_runs_session_idx on public.ai_runs (session_id, created_at desc);
create index if not exists provider_settings_org_idx on public.provider_settings (organisation_id);

alter table public.provider_settings enable row level security;
alter table public.ai_runs enable row level security;

create policy "provider_settings member"
  on public.provider_settings for all
  using (public.haki_active_member(organisation_id))
  with check (public.haki_active_member(organisation_id));

create policy "ai_runs member read"
  on public.ai_runs for select
  using (
    organisation_id is not null and public.haki_active_member(organisation_id)
  );

create policy "ai_runs member insert"
  on public.ai_runs for insert
  with check (
    organisation_id is null
    or public.haki_active_member(organisation_id)
  );
