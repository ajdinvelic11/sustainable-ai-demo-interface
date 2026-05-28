create schema if not exists ml_ops;

create table if not exists ml_ops.demo_ui_runs (
    demo_run_id bigserial primary key,
    demo_name text not null,
    status text not null,
    requested_duration_seconds integer not null default 300,
    started_by text,
    auth_subject text,
    linked_chain_test_id bigint,
    current_phase_no integer,
    current_command_id bigint,
    final_training_run_id bigint,
    final_checkpoint_s3_uri text,
    error_message text,
    created_at timestamptz not null default now(),
    started_at timestamptz,
    finished_at timestamptz,
    updated_at timestamptz not null default now()
);

create table if not exists ml_ops.demo_ui_events (
    event_id bigserial primary key,
    demo_run_id bigint references ml_ops.demo_ui_runs(demo_run_id),
    event_type text not null,
    severity text not null default 'INFO',
    message text not null,
    location_name text,
    region_code text,
    phase_no integer,
    command_id bigint,
    training_run_id bigint,
    metadata jsonb,
    created_at timestamptz not null default now()
);

