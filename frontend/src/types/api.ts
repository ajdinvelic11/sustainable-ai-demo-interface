export type SessionUser = {
  subject: string;
  issuer?: string | null;
  name?: string | null;
  email?: string | null;
  roles: string[];
  is_admin: boolean;
  auth_mode: string;
  expires_at: string;
};

export type AuthConfig = {
  validation_enabled: boolean;
  mock_mode: boolean;
  validation_url_configured: boolean;
};

export type MeResponse = {
  authenticated: boolean;
  user: SessionUser | null;
  demo_auth_mode: boolean;
};

export type SiteInfo = {
  location_name: string;
  region_code: string;
  host?: string | null;
  role?: string | null;
  current_status?: string | null;
  last_seen_at?: string | null;
};

export type DemoEvent = {
  event_id?: number | null;
  demo_run_id: number;
  event_type: string;
  severity: string;
  message: string;
  location_name?: string | null;
  region_code?: string | null;
  phase_no?: number | null;
  command_id?: number | null;
  training_run_id?: number | null;
  metadata?: Record<string, unknown> | null;
  created_at: string;
};

export type DemoPhase = {
  phase_no: number;
  location_name: string;
  region_code: string;
  target_percent: number;
  target_duration_seconds: number;
  status: string;
  command_id?: number | null;
  command_status?: string | null;
  training_run_id?: number | null;
  output_checkpoint_s3_uri?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
};

export type LiveMetrics = {
  command_id?: number | null;
  training_run_id?: number | null;
  current_status?: string | null;
  progress_percent?: number | null;
  epoch?: number | null;
  total_epochs?: number | null;
  mAP50?: number | null;
  precision?: number | null;
  recall?: number | null;
  message?: string | null;
  updated_at?: string | null;
};

export type DemoState = {
  demo_run_id?: number | null;
  demo_name?: string | null;
  status: string;
  setup_required: boolean;
  warning?: string | null;
  overall_progress_percent: number;
  current_phase?: {
    phase_no: number;
    location_name: string;
    region_code: string;
    target_percent: number;
    status: string;
    command_id?: number | null;
    training_run_id?: number | null;
  } | null;
  phases: DemoPhase[];
  latest_metrics?: LiveMetrics | null;
  latest_checkpoint_s3_uri?: string | null;
  final_result: {
    final_training_run_id?: number | null;
    final_checkpoint_s3_uri?: string | null;
    best_model_s3_uri?: string | null;
  };
  events: DemoEvent[];
  created_at?: string | null;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at?: string | null;
};

export type StartDemoResponse = {
  demo_run_id: number;
  status: string;
  message: string;
};

