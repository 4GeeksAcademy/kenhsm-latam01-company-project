create table if not exists public.telemetry_events (
    id uuid primary key default gen_random_uuid(),
    timestamp timestamptz not null,
    service text not null check (service in ('backoffice', 'api')),
    event_type text not null check (event_type ~ '^[a-z]+(_[a-z]+)+$'),
    level text not null default 'info' check (level in ('info', 'warn', 'error')),
    value numeric null,
    message text null,
    tags jsonb not null default '{}'::jsonb check (jsonb_typeof(tags) = 'object')
);

create index if not exists telemetry_events_timestamp_idx
    on public.telemetry_events (timestamp desc);

create index if not exists telemetry_events_event_type_idx
    on public.telemetry_events (event_type);

create index if not exists telemetry_events_tags_idx
    on public.telemetry_events using gin (tags jsonb_path_ops);

alter table public.telemetry_events enable row level security;

revoke all on table public.telemetry_events from anon, authenticated, service_role;
grant insert on table public.telemetry_events to service_role;

create policy telemetry_events_service_role_insert
    on public.telemetry_events
    for insert
    to service_role
    with check (true);