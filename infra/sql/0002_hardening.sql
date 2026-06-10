-- market-monitor schema v2: anti-spam caps, LLM gating, replay requests, realtime
-- Apply AFTER 0001_init.sql.

-- ── new config knobs ──────────────────────────────────────────────────────
alter table public.monitor_configs
  add column if not exists max_alerts_per_cycle int not null default 8,
  add column if not exists max_alerts_per_event_per_day int not null default 5,
  add column if not exists llm_min_band text not null default 'medium'
    check (llm_min_band in ('low', 'medium', 'high'));

-- ── manual replay queue (dashboard inserts, worker consumes) ──────────────
create table if not exists public.replay_requests (
  id uuid primary key default gen_random_uuid(),
  alert_id uuid not null references public.alerts(id) on delete cascade,
  requested_by uuid references public.users(id),
  status text not null default 'pending'
    check (status in ('pending', 'done', 'failed')),
  result_alert_id uuid references public.alerts(id),
  error text,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);
create index if not exists replay_requests_pending_idx
  on public.replay_requests (status) where status = 'pending';

alter table public.replay_requests enable row level security;
create policy replay_requests_read on public.replay_requests
  for select to authenticated
  using (exists (select 1 from public.users u where u.id = auth.uid()));

-- ── realtime: push new alerts to the dashboard ────────────────────────────
do $$
begin
  alter publication supabase_realtime add table public.alerts;
exception when duplicate_object then null;
end $$;
