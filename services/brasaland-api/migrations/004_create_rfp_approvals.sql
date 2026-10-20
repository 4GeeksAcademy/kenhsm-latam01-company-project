create table if not exists public.rfp_human_approvals (
    ticket_id uuid not null references public.rfp_tickets(ticket_id) on delete cascade,
    approval_key text not null check (approval_key in ('marketing', 'operaciones', 'procurement', 'training', 'ceo')),
    approval_status text not null check (approval_status in ('pendiente', 'aprobado', 'rechazado', 'cambios_solicitados')),
    approver text not null,
    comment text,
    revision integer not null default 1 check (revision > 0),
    approved_at timestamptz,
    updated_at timestamptz not null default now(),
    primary key (ticket_id, approval_key)
);

create table if not exists public.rfp_execution_events (
    event_id uuid primary key,
    ticket_id uuid not null references public.rfp_tickets(ticket_id) on delete cascade,
    agent text not null,
    input jsonb not null,
    output jsonb not null,
    timestamp timestamptz not null
);

create index if not exists rfp_execution_events_ticket_timestamp_idx
    on public.rfp_execution_events (ticket_id, timestamp);

create table if not exists public.rfp_final_documents (
    ticket_id uuid primary key references public.rfp_tickets(ticket_id) on delete cascade,
    document_markdown text not null,
    sections jsonb not null,
    total_estimated_value numeric,
    currency text not null default 'USD' check (currency in ('USD', 'COP')),
    generated_at timestamptz not null default now()
);

alter table public.rfp_human_approvals enable row level security;
alter table public.rfp_execution_events enable row level security;
alter table public.rfp_final_documents enable row level security;

grant select, insert, update on public.rfp_human_approvals to service_role;
grant select, insert on public.rfp_execution_events to service_role;
grant select, insert, update on public.rfp_final_documents to service_role;