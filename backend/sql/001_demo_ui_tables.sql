CREATE SCHEMA IF NOT EXISTS ml_ops;

CREATE TABLE IF NOT EXISTS ml_ops.demo_ui_runs (
    demo_run_id BIGSERIAL PRIMARY KEY,
    demo_name TEXT NOT NULL,
    status TEXT NOT NULL,
    requested_duration_seconds INTEGER NOT NULL DEFAULT 300,
    started_by TEXT,
    auth_subject TEXT,
    linked_chain_test_id BIGINT,
    current_phase_no INTEGER,
    current_command_id BIGINT,
    final_training_run_id BIGINT,
    final_checkpoint_s3_uri TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ml_ops.demo_ui_events (
    event_id BIGSERIAL PRIMARY KEY,
    demo_run_id BIGINT REFERENCES ml_ops.demo_ui_runs(demo_run_id),
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    location_name TEXT,
    region_code TEXT,
    phase_no INTEGER,
    command_id BIGINT,
    training_run_id BIGINT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
