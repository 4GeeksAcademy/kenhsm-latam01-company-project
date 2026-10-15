create table if not exists public.rfp_tickets (
    ticket_id uuid primary key,
    rfp_id uuid not null unique,
    status text not null check (status in (
        'analizando', 'descartado', 'analisis_completo', 'generando_borrador',
        'en_evaluación', 'needs_human_review', 'esperando_aprobación', 'terminado'
    )),
    raw_pdf_path text not null,
    submitted_by text not null,
    processing_error text,
    handoff_payload jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists rfp_tickets_created_at_idx on public.rfp_tickets (created_at desc);
create index if not exists rfp_tickets_status_idx on public.rfp_tickets (status);

create table if not exists public.rfp_metadata (
    ticket_id uuid primary key references public.rfp_tickets(ticket_id) on delete cascade,
    client_name text,
    location text,
    service_type text,
    scope jsonb,
    deadline text,
    budget_range text,
    departments_needed jsonb not null default '[]'::jsonb,
    open_questions jsonb not null default '[]'::jsonb,
    readability_metrics jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.department_sections (
    ticket_id uuid not null references public.rfp_tickets(ticket_id) on delete cascade,
    department_id text not null check (department_id in ('marketing', 'operaciones', 'procurement', 'training')),
    key_aspects jsonb not null default '{}'::jsonb,
    draft_content text,
    evaluation_results jsonb,
    approval_status text not null default 'pendiente' check (approval_status in ('pendiente', 'aprobado', 'rechazado')),
    approver text,
    approved_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (ticket_id, department_id)
);

alter table public.rfp_tickets enable row level security;
alter table public.rfp_metadata enable row level security;
alter table public.department_sections enable row level security;

grant select, insert, update on public.rfp_tickets to service_role;
grant select, insert, update on public.rfp_metadata to service_role;
grant select, insert, update on public.department_sections to service_role;