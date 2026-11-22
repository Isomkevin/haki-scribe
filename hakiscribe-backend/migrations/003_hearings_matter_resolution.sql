-- Virtual court hearings + matter resolution (apply after 002).
-- Demo mode mirrors these via in-memory services; production uses RLS when
-- HAKISCRIBE_PRODUCTION_AUTH is enabled.
--
-- ROLLBACK:
--   drop policy if exists "hearings member" on public.haki_hearings;
--   drop policy if exists "hearing_matches member" on public.haki_hearing_match_candidates;
--   drop policy if exists "hearing_confirmations member" on public.haki_hearing_confirmations;
--   drop table if exists public.haki_hearing_confirmations;
--   drop table if exists public.haki_hearing_match_candidates;
--   drop table if exists public.haki_hearings;

create table if not exists public.haki_hearings (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid references public.haki_organisations(id) on delete cascade,
  source text not null check (source in ('google_calendar', 'teams_graph', 'zoom', 'manual_upload')),
  external_id text,
  title text not null,
  description text,
  starts_at timestamptz,
  ends_at timestamptz,
  court_name text,
  case_reference text,
  meeting_url text,
  platform_metadata jsonb not null default '{}'::jsonb,
  status text not null default 'scheduled'
    check (status in (
      'scheduled',
      'pending_confirm',
      'matched',
      'capturing',
      'ingested',
      'transcribed',
      'reviewed',
      'filed',
      'rejected'
    )),
  matter_id uuid references public.haki_matters(id) on delete set null,
  session_id uuid references public.haki_sessions(id) on delete set null,
  match_confidence double precision,
  recording_object_key text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.haki_hearing_match_candidates (
  id uuid primary key default gen_random_uuid(),
  hearing_id uuid not null references public.haki_hearings(id) on delete cascade,
  matter_id uuid not null references public.haki_matters(id) on delete cascade,
  score double precision not null,
  rationale text,
  created_at timestamptz not null default now()
);

create table if not exists public.haki_hearing_confirmations (
  id uuid primary key default gen_random_uuid(),
  hearing_id uuid not null references public.haki_hearings(id) on delete cascade,
  matter_id uuid references public.haki_matters(id) on delete set null,
  decision text not null check (decision in ('confirm', 'reject')),
  actor_label text,
  created_at timestamptz not null default now()
);

create index if not exists haki_hearings_org_idx on public.haki_hearings (organisation_id, starts_at desc);
create index if not exists haki_hearings_status_idx on public.haki_hearings (status);
create index if not exists haki_hearing_matches_hearing_idx on public.haki_hearing_match_candidates (hearing_id, score desc);

alter table public.haki_hearings enable row level security;
alter table public.haki_hearing_match_candidates enable row level security;
alter table public.haki_hearing_confirmations enable row level security;

create policy "hearings member"
  on public.haki_hearings for all
  using (organisation_id is null or public.haki_active_member(organisation_id))
  with check (organisation_id is null or public.haki_active_member(organisation_id));

create policy "hearing_matches member"
  on public.haki_hearing_match_candidates for all
  using (
    exists (
      select 1 from public.haki_hearings h
      where h.id = hearing_id
        and (h.organisation_id is null or public.haki_active_member(h.organisation_id))
    )
  )
  with check (
    exists (
      select 1 from public.haki_hearings h
      where h.id = hearing_id
        and (h.organisation_id is null or public.haki_active_member(h.organisation_id))
    )
  );

create policy "hearing_confirmations member"
  on public.haki_hearing_confirmations for all
  using (
    exists (
      select 1 from public.haki_hearings h
      where h.id = hearing_id
        and (h.organisation_id is null or public.haki_active_member(h.organisation_id))
    )
  )
  with check (
    exists (
      select 1 from public.haki_hearings h
      where h.id = hearing_id
        and (h.organisation_id is null or public.haki_active_member(h.organisation_id))
    )
  );
