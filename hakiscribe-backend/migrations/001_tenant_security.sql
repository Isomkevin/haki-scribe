-- HakiScribe production tenancy foundation for Supabase Postgres.
-- Apply through the Supabase SQL editor or the Supabase CLI before enabling
-- HAKISCRIBE_PRODUCTION_AUTH=true. Do not apply demo data to these tables.

create extension if not exists pgcrypto;

create type public.haki_member_role as enum ('owner', 'admin', 'lawyer', 'clerk');
create type public.haki_membership_status as enum ('active', 'invited', 'suspended');

create table public.haki_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.haki_organisations (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(trim(name)) between 2 and 160),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.haki_memberships (
  organisation_id uuid not null references public.haki_organisations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.haki_member_role not null default 'lawyer',
  status public.haki_membership_status not null default 'active',
  created_at timestamptz not null default now(),
  primary key (organisation_id, user_id)
);

create table public.haki_workspaces (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.haki_organisations(id) on delete cascade,
  name text not null check (char_length(trim(name)) between 1 and 160),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  unique (organisation_id, name)
);

create table public.haki_matters (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid not null references public.haki_organisations(id) on delete cascade,
  workspace_id uuid not null references public.haki_workspaces(id) on delete cascade,
  client_name text not null,
  matter_name text not null,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table public.haki_matter_memberships (
  matter_id uuid not null references public.haki_matters(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.haki_member_role not null default 'lawyer',
  created_at timestamptz not null default now(),
  primary key (matter_id, user_id)
);

create table public.haki_sessions (
  id uuid primary key,
  organisation_id uuid not null references public.haki_organisations(id) on delete restrict,
  workspace_id uuid not null references public.haki_workspaces(id) on delete restrict,
  matter_id uuid references public.haki_matters(id) on delete set null,
  created_by uuid not null references auth.users(id),
  title text not null,
  source text not null check (source in ('mic', 'omi')),
  status text not null,
  language_hint text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Transcript segments, flags, actions, results, and chats are scoped through
-- their session; this keeps the organisation boundary impossible to omit.
create table public.haki_session_records (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.haki_sessions(id) on delete cascade,
  record_type text not null check (record_type in ('segment','flag','action','result','chat','contact')),
  payload jsonb not null,
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now()
);

create table public.haki_audit_events (
  id uuid primary key default gen_random_uuid(),
  organisation_id uuid references public.haki_organisations(id) on delete set null,
  actor_id uuid references auth.users(id) on delete set null,
  event_type text not null,
  target_type text,
  target_id uuid,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index haki_sessions_org_idx on public.haki_sessions (organisation_id, created_at desc);
create index haki_session_records_session_idx on public.haki_session_records (session_id, created_at);
create index haki_audit_org_idx on public.haki_audit_events (organisation_id, created_at desc);

create or replace function public.haki_active_member(org uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.haki_memberships m
    where m.organisation_id = org and m.user_id = auth.uid() and m.status = 'active'
  );
$$;

create or replace function public.haki_workspace_administrator(org uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.haki_memberships m
    where m.organisation_id = org
      and m.user_id = auth.uid()
      and m.status = 'active'
      and m.role in ('owner', 'admin')
  );
$$;

create or replace function public.haki_can_access_session(target_session uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.haki_sessions s
    where s.id = target_session
      and public.haki_active_member(s.organisation_id)
      and (s.matter_id is null or exists (
        select 1 from public.haki_matter_memberships mm
        where mm.matter_id = s.matter_id and mm.user_id = auth.uid()
      ))
  );
$$;

alter table public.haki_profiles enable row level security;
alter table public.haki_organisations enable row level security;
alter table public.haki_memberships enable row level security;
alter table public.haki_workspaces enable row level security;
alter table public.haki_matters enable row level security;
alter table public.haki_matter_memberships enable row level security;
alter table public.haki_sessions enable row level security;
alter table public.haki_session_records enable row level security;
alter table public.haki_audit_events enable row level security;

create policy "profile self" on public.haki_profiles for all using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "organisation member read" on public.haki_organisations for select using (public.haki_active_member(id));
create policy "membership member read" on public.haki_memberships for select using (public.haki_active_member(organisation_id));
create policy "workspace member read" on public.haki_workspaces for select using (public.haki_active_member(organisation_id));
create policy "workspace administrator write" on public.haki_workspaces for insert with check (public.haki_workspace_administrator(organisation_id));
create policy "workspace administrator update" on public.haki_workspaces for update using (public.haki_workspace_administrator(organisation_id)) with check (public.haki_workspace_administrator(organisation_id));
create policy "workspace administrator delete" on public.haki_workspaces for delete using (public.haki_workspace_administrator(organisation_id));
create policy "matter member" on public.haki_matters for select using (public.haki_active_member(organisation_id) and exists (select 1 from public.haki_matter_memberships mm where mm.matter_id = id and mm.user_id = auth.uid()));
create policy "session access" on public.haki_sessions for all using (public.haki_can_access_session(id)) with check (public.haki_active_member(organisation_id) and created_by = auth.uid());
create policy "session record read" on public.haki_session_records for select using (public.haki_can_access_session(session_id));
create policy "session record append" on public.haki_session_records for insert with check (public.haki_can_access_session(session_id) and created_by = auth.uid());
create policy "audit member read" on public.haki_audit_events for select using (organisation_id is not null and public.haki_active_member(organisation_id));

-- Service-role background workers may bypass RLS only after they have verified
-- producer identity and tenant membership in application code. Never use the
-- service role for ordinary browser requests.
