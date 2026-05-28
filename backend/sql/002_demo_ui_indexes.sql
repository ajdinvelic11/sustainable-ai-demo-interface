CREATE INDEX IF NOT EXISTS demo_ui_runs_status_idx
    ON ml_ops.demo_ui_runs (status);

CREATE INDEX IF NOT EXISTS demo_ui_runs_created_at_idx
    ON ml_ops.demo_ui_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS demo_ui_events_demo_run_created_at_idx
    ON ml_ops.demo_ui_events (demo_run_id, created_at);
