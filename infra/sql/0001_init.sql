-- market-monitor schema v1
-- Apply with: supabase db push  (or psql against your Supabase database)

create extension if not exists pgcrypto;

-- ── users (mirrors auth.users) ────────────────────────────────────────────
create table public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  display_name text,
  role text not null default 'admin' check (role in ('admin', 'viewer')),
  created_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.users (id, email) values (new.id, new.email)
  on conflict (id) do nothing;
  return new;
end $$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- ── configuration ─────────────────────────────────────────────────────────
create table public.monitor_configs (
  id int primary key check (id = 1),
  football_enabled boolean not null default true,
  world_cup_enabled boolean not null default false,
  world_cup_only_mode boolean not null default false,
  global_pause boolean not null default false,
  dry_run boolean not null default true,
  llm_enabled boolean not null default false,
  daily_credit_cap int not null default 16,
  monthly_credit_cap int not null default 450,
  odds_api_region text not null default 'eu',
  worker_poll_floor_seconds int not null default 300,
  alert_suppression_minutes int not null default 90,
  updated_by uuid references public.users(id),
  updated_at timestamptz not null default now()
);

create table public.monitor_segments (
  segment_key text primary key,
  display_label text not null,
  sport_keys text[] not null,
  bookmaker_keys text[] not null,
  sharp_bookmaker_keys text[] not null default '{pinnacle}',
  market_keys text[] not null default '{h2h,spreads,totals}',
  polling_profile jsonb not null
    default '{"gt48h": 0, "h48_24": 480, "h24_6": 180, "h6_1": 60, "lt1h": 30}',
  min_alert_score int not null default 55,
  thresholds jsonb not null default '{
    "price_move":   {"abs_dp_min": 0.03, "z_min": 3.0},
    "divergence":   {"divergence_min": 0.04},
    "drift":        {"drift_polls_min": 3, "drift_cum_min": 0.04},
    "sharp_leader": {"sharp_dp_min": 0.025, "follower_count_min": 2},
    "persistence":  {"persistence_ratio_min": 0.7},
    "reversal":     {"reversal_ratio": 0.6, "reversal_window_polls": 2},
    "rarity":       {"rarity_pctile_min": 97, "rarity_min_samples": 300}
  }',
  telegram_chat_id text,
  enabled boolean not null default true,
  updated_by uuid references public.users(id),
  updated_at timestamptz not null default now()
);

-- ── reference data ────────────────────────────────────────────────────────
create table public.competitions (
  id uuid primary key default gen_random_uuid(),
  sport_key text not null unique,
  title text not null,
  segment_key text not null references public.monitor_segments(segment_key),
  created_at timestamptz not null default now()
);

create table public.bookmakers (
  bookmaker_key text primary key,
  title text not null,
  is_sharp boolean not null default false
);

create table public.markets (
  market_key text primary key,
  description text not null
);

-- ── market data ───────────────────────────────────────────────────────────
create table public.events (
  id uuid primary key default gen_random_uuid(),
  provider_event_id text not null,
  sport_key text not null,
  segment_key text not null references public.monitor_segments(segment_key),
  home_team text not null,
  away_team text not null,
  commence_time timestamptz not null,
  status text not null default 'upcoming'
    check (status in ('upcoming', 'live', 'finished', 'cancelled')),
  created_at timestamptz not null default now(),
  unique (provider_event_id, sport_key)
);
create index events_segment_commence_idx on public.events (segment_key, commence_time);

create table public.selections (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  market_key text not null references public.markets(market_key),
  name text not null,
  line numeric,
  created_at timestamptz not null default now()
);
create unique index selections_natural_key
  on public.selections (event_id, market_key, name, coalesce(line, 0));

create table public.odds_snapshots (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  selection_id uuid not null references public.selections(id) on delete cascade,
  bookmaker_key text not null references public.bookmakers(bookmaker_key),
  market_key text not null references public.markets(market_key),
  price_decimal numeric(8,3) not null,
  implied_prob numeric(6,5) not null,
  book_last_update timestamptz,
  poll_cycle_id uuid not null,
  polled_at timestamptz not null default now(),
  unique (selection_id, bookmaker_key, poll_cycle_id)
);
create index odds_snapshots_series_idx
  on public.odds_snapshots (selection_id, bookmaker_key, polled_at desc);

create table public.feature_windows (
  id uuid primary key default gen_random_uuid(),
  selection_id uuid not null references public.selections(id) on delete cascade,
  bookmaker_key text references public.bookmakers(bookmaker_key), -- null = consensus
  window text not null check (window in ('poll', '1h', '6h', '24h')),
  dp numeric,
  z numeric,
  pctile numeric,
  computed_at timestamptz not null default now(),
  unique nulls not distinct (selection_id, bookmaker_key, window)
);

-- ── alerts ────────────────────────────────────────────────────────────────
create table public.alerts (
  id uuid primary key default gen_random_uuid(),
  segment_key text not null references public.monitor_segments(segment_key),
  event_id uuid not null references public.events(id),
  market_key text not null references public.markets(market_key),
  selection_id uuid not null references public.selections(id),
  alert_type text not null check (alert_type in
    ('SHARP_MOVE','STEAM_MOVE','PRICE_SPIKE','BOOK_DIVERGENCE','RARE_MOVE','REVERSAL')),
  alert_score int not null check (alert_score between 0 and 100),
  confidence_band text not null check (confidence_band in ('low','medium','high')),
  reason_summary text not null,
  status text not null default 'new'
    check (status in ('new','acknowledged','dismissed','replayed')),
  dedupe_key text not null unique,
  created_at timestamptz not null default now()
);
create index alerts_segment_created_idx on public.alerts (segment_key, created_at desc);

create table public.alert_evidence (
  alert_id uuid primary key references public.alerts(id) on delete cascade,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

create table public.alert_feedback (
  id uuid primary key default gen_random_uuid(),
  alert_id uuid not null references public.alerts(id) on delete cascade,
  user_id uuid not null references public.users(id),
  verdict text not null check (verdict in ('useful','noise','late','wrong')),
  note text,
  created_at timestamptz not null default now(),
  unique (alert_id, user_id)
);

create table public.llm_analyses (
  alert_id uuid primary key references public.alerts(id) on delete cascade,
  classification text check (classification in
    ('possible_sharp_move','possible_market_correction',
     'possible_news_driven_move','possible_noise','needs_human_review')),
  summary text,
  confidence text check (confidence in ('low','medium','high')),
  model text,
  tokens_in int,
  tokens_out int,
  raw jsonb,
  status text not null default 'ok' check (status in ('ok','failed','skipped')),
  created_at timestamptz not null default now()
);

create table public.telegram_deliveries (
  id uuid primary key default gen_random_uuid(),
  alert_id uuid not null references public.alerts(id) on delete cascade,
  chat_id text not null,
  message_id bigint,
  status text not null check (status in ('sent','failed','dry_run','suppressed')),
  error text,
  attempts int not null default 0,
  created_at timestamptz not null default now(),
  unique (alert_id, chat_id)
);

-- ── operations ────────────────────────────────────────────────────────────
create table public.worker_runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  cycle_type text not null default 'poll'
    check (cycle_type in ('poll','event_refresh','idle')),
  segments text[] not null default '{}',
  credits_used int not null default 0,
  snapshots_written int not null default 0,
  alerts_created int not null default 0,
  status text not null default 'ok' check (status in ('ok','error','partial','running')),
  error text
);
create index worker_runs_started_idx on public.worker_runs (started_at desc);

create table public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid references public.users(id), -- null = worker
  action text not null,
  entity text not null,
  entity_id text,
  before jsonb,
  after jsonb,
  created_at timestamptz not null default now()
);

-- ── RLS ───────────────────────────────────────────────────────────────────
-- Worker uses the service-role key (bypasses RLS). Browser users are admins.
do $$
declare t text;
begin
  foreach t in array array[
    'users','monitor_configs','monitor_segments','competitions','events',
    'bookmakers','markets','selections','odds_snapshots','feature_windows',
    'alerts','alert_evidence','alert_feedback','llm_analyses',
    'telegram_deliveries','worker_runs','audit_logs']
  loop
    execute format('alter table public.%I enable row level security', t);
    execute format(
      'create policy %I on public.%I for select to authenticated using (
         exists (select 1 from public.users u where u.id = auth.uid()))', t || '_read', t);
  end loop;
end $$;

-- Admins may submit feedback and update alert status directly.
create policy alert_feedback_insert on public.alert_feedback
  for insert to authenticated
  with check (user_id = auth.uid() and exists
    (select 1 from public.users u where u.id = auth.uid() and u.role = 'admin'));

create policy alerts_update_status on public.alerts
  for update to authenticated
  using (exists (select 1 from public.users u where u.id = auth.uid() and u.role = 'admin'))
  with check (true);

-- Config mutations are NOT allowed via RLS: they go through Next.js API routes
-- using the service-role key so every change lands in audit_logs.

-- ── seeds ─────────────────────────────────────────────────────────────────
insert into public.monitor_segments (segment_key, display_label, sport_keys, bookmaker_keys, min_alert_score) values
  ('general_football', 'GENERAL FOOTBALL', '{soccer_epl}',
   '{pinnacle,bet365,unibet,williamhill,marathonbet,betsson}', 55),
  ('world_cup', 'WORLD CUP', '{soccer_fifa_world_cup}',
   '{pinnacle,bet365,unibet,williamhill,marathonbet,betsson}', 50);

-- World Cup focus: boot in WC-only mode. General football stays configured but
-- suppressed until world_cup_only_mode is switched off from the dashboard.
insert into public.monitor_configs (id, world_cup_enabled, world_cup_only_mode)
values (1, true, true);

insert into public.markets (market_key, description) values
  ('h2h', 'Match winner (1X2 / moneyline)'),
  ('spreads', 'Handicap / spread'),
  ('totals', 'Total goals over/under');

insert into public.bookmakers (bookmaker_key, title, is_sharp) values
  ('pinnacle', 'Pinnacle', true),
  ('bet365', 'bet365', false),
  ('unibet', 'Unibet', false),
  ('williamhill', 'William Hill', false),
  ('marathonbet', 'Marathon Bet', false),
  ('betsson', 'Betsson', false);

insert into public.competitions (sport_key, title, segment_key) values
  ('soccer_epl', 'English Premier League', 'general_football'),
  ('soccer_fifa_world_cup', 'FIFA World Cup', 'world_cup');
