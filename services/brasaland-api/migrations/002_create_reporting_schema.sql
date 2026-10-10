create schema if not exists reporting;

create table if not exists reporting.weekly_location_performance (
    id uuid primary key default gen_random_uuid(),
    location_id text not null,
    country text not null check (country in ('CO', 'US')),
    week_start date not null,
    total_purchase_cost numeric not null default 0,
    total_waste_cost numeric not null default 0,
    waste_ratio numeric not null default 0,
    stockout_events_count integer not null default 0,
    price_alert_events_count integer not null default 0,
    currency text not null check (currency in ('COP', 'USD')),
    computed_at timestamptz not null default now(),
    unique (location_id, week_start)
);

create table if not exists reporting.pipeline_runs (
    run_id uuid primary key,
    flow_name text not null,
    trigger_type text not null,
    week_start date not null,
    status text not null,
    phase text not null,
    started_at timestamptz not null,
    ended_at timestamptz null,
    source_counts jsonb not null default '{}'::jsonb,
    source_min_timestamp timestamptz null,
    source_max_timestamp timestamptz null,
    source_watermark timestamptz null,
    output_rows integer not null default 0,
    records_processed integer not null default 0,
    error_code text null,
    error_message text null,
    errors jsonb not null default '[]'::jsonb,
    local_mode boolean not null default false,
    created_at timestamptz not null default now()
);

create index if not exists pipeline_runs_started_at_idx
    on reporting.pipeline_runs (started_at desc);

alter table reporting.weekly_location_performance enable row level security;
alter table reporting.pipeline_runs enable row level security;

grant usage on schema reporting to service_role;
grant select, insert, update on reporting.weekly_location_performance to service_role;
grant select, insert, update on reporting.pipeline_runs to service_role;

-- The reporting reader uses GET only; the append-only telemetry receiver remains unchanged.
grant select on public.telemetry_events to service_role;