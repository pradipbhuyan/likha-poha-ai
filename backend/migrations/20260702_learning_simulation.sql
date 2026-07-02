-- Learning Simulation tables
-- Creates tables for admin-triggered cumulative student learning simulation.
-- All data is synthetic/test. No real users, payments, or emails involved.

-- Tracks each admin-triggered simulation run
create table if not exists learning_simulation_runs (
  id                  uuid primary key default gen_random_uuid(),
  status              text not null default 'pending',  -- pending|running|completed|failed
  cycle_start_day     int  not null,
  cycle_end_day       int  not null,
  created_by_admin_id uuid references auth.users(id),
  dry_run             boolean not null default false,
  create_bugs         boolean not null default true,
  strict_validation   boolean not null default true,
  started_at          timestamptz,
  completed_at        timestamptz,
  total_events        int not null default 0,
  anomalies_count     int not null default 0,
  bugs_created_count  int not null default 0,
  summary_json        jsonb,
  error_message       text,
  created_at          timestamptz not null default now()
);

-- Individual simulation events (one per activity per simulated day)
create table if not exists learning_simulation_events (
  id            uuid primary key default gen_random_uuid(),
  run_id        uuid not null references learning_simulation_runs(id) on delete cascade,
  simulated_day int  not null,
  event_type    text not null, -- lesson|practice|doubt|followup|formula|exemplar|mock_test|dashboard_check|parent_check
  user_id       uuid,
  subject       text,
  chapter       text,
  lesson_id     text,
  metadata_json jsonb,
  created_at    timestamptz not null default now()
);

-- Anomalies detected during simulation runs
create table if not exists learning_simulation_anomalies (
  id               uuid primary key default gen_random_uuid(),
  run_id           uuid not null references learning_simulation_runs(id) on delete cascade,
  severity         text not null default 'medium', -- critical|high|medium|low
  anomaly_type     text not null, -- dashboard_mismatch|access_issue|score_out_of_range|progress_not_cumulative|...
  message          text not null,
  expected_json    jsonb,
  actual_json      jsonb,
  context_json     jsonb,
  product_issue_id uuid,  -- nullable — set when bug is created
  status           text not null default 'open', -- open|bug_created|resolved|ignored
  created_at       timestamptz not null default now()
);

-- Indexes for fast lookups
create index if not exists idx_sim_runs_status on learning_simulation_runs(status);
create index if not exists idx_sim_events_run_id on learning_simulation_events(run_id);
create index if not exists idx_sim_events_day on learning_simulation_events(run_id, simulated_day);
create index if not exists idx_sim_anomalies_run_id on learning_simulation_anomalies(run_id);
create index if not exists idx_sim_anomalies_severity on learning_simulation_anomalies(severity);
