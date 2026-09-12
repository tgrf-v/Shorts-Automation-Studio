export type ProjectStatus =
  | 'draft'
  | 'analyzing'
  | 'script_ready'
  | 'voice_ready'
  | 'footage_ready'
  | 'editing'
  | 'rendering'
  | 'completed'
  | 'failed';

export type JobStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface HealthResponse {
  status: string;
  app_env: string;
  version: string;
}

export interface ServiceCheckResult {
  name: string;
  status: 'healthy' | 'unhealthy' | 'pending';
  message?: string;
  latency_ms?: number;
}

export interface ProjectMetadata {
  id: string;
  name: string;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}
