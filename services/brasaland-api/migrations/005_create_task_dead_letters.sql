create table if not exists public.task_dead_letters (
    id uuid primary key default gen_random_uuid(),
    task_id text not null unique,
    task_name text not null,
    attempt integer not null check (attempt >= 1),
    error_message text not null,
    failed_at timestamptz not null default now()
);

create index if not exists task_dead_letters_failed_at_idx
    on public.task_dead_letters (failed_at desc);

alter table public.task_dead_letters enable row level security;
revoke all on table public.task_dead_letters from anon, authenticated;
grant insert on table public.task_dead_letters to service_role;

create policy task_dead_letters_service_role_insert
    on public.task_dead_letters
    for insert
    to service_role
    with check (true);