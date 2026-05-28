export interface AuthUser {
  subject: string;
  issuer: string;
  credential_type: string;
  is_admin: boolean;
  auth_mode: "validated" | "mock" | string;
}

export interface AuthResponse {
  authenticated: boolean;
  user: AuthUser | null;
  csrf_token: string | null;
  demo_auth_mode: boolean;
  expires_at?: string | null;
}

export interface AuthConfig {
  validation_enabled: boolean;
  mock_mode: boolean;
}

export interface SiteInfo {
  location_name: string;
  region_code: string;
  host_label: string;
  role: string;
  status: string;
}

export interface DemoEvent {
  event_id: number;
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
}

export interface DemoPhase {
  phase_no: number;
  location_name: string;
  region_code: string;
  target_percent: number;
  target_duration_seconds: number;
  status: string;
  command_id?: number | null;
  command_status?: string | null;
  training_run_id?: number | null;
  resume_checkpoint_s3_uri?: string | null;
  output_checkpoint_s3_uri?: string | null;
}

export interface LiveMetrics {
  command_id?: number | null;
  training_run_id?: number | null;
  current_status?: string | null;
  progress_percent?: number | null;
  epoch?: number | null;
  total_epochs?: number | null;
  map50?: number | null;
  precision?: number | null;
  recall?: number | null;
  message?: string | null;
  updated_at?: string | null;
}

export interface FinalResult {
  final_training_run_id?: number | null;
  final_checkpoint_s3_uri?: string | null;
  s3_best_model_uri?: string | null;
}

export interface DemoRunState {
  demo_run_id: number;
  demo_name: string;
  status: string;
  overall_progress_percent: number;
  requested_duration_seconds: number;
  started_by?: string | null;
  auth_subject?: string | null;
  current_phase?: DemoPhase | null;
  phases: DemoPhase[];
  latest_metrics?: LiveMetrics | null;
  final_result: FinalResult;
  events: DemoEvent[];
  error_message?: string | null;
  created_at: string;
  started_at?: string | null;
  finished_at?: string | null;
  updated_at: string;
}

export interface CurrentDemoResponse {
  active: boolean;
  latest: DemoRunState | null;
  migration_required: boolean;
}

export interface DemoStartResponse {
  demo_run_id: number;
  status: string;
}

export interface ResetStaleResponse {
  reset_runs: number;
  reset_commands: number;
}
