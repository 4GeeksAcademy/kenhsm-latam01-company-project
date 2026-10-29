create table if not exists public.job_runs (
    id uuid primary key default gen_random_uuid(),
    job_name text not null,
    target_date date not null,
    status text not null default 'pending'
        check (status in ('pending', 'processing', 'completed', 'failed')),
    started_at timestamptz null,
    finished_at timestamptz null,
    error_message text null,
    created_at timestamptz not null default now()
);

create index if not exists job_runs_job_date_idx
    on public.job_runs (job_name, target_date);

-- The processing state itself is the lock; this index makes the transition atomic across processes.
create unique index if not exists job_runs_one_processing_job_idx
    on public.job_runs (job_name)
    where status = 'processing';

alter table public.job_runs enable row level security;
revoke all on table public.job_runs from anon, authenticated;
grant select, insert, update on table public.job_runs to service_role;

create policy job_runs_service_role_all
    on public.job_runs
    for all
    to service_role
    using (true)
    with check (true);