create index if not exists idx_demo_ui_runs_status
    on ml_ops.demo_ui_runs(status);

create index if not exists idx_demo_ui_runs_created_at_desc
    on ml_ops.demo_ui_runs(created_at desc);

create index if not exists idx_demo_ui_events_demo_run_created_at
    on ml_ops.demo_ui_events(demo_run_id, created_at);

