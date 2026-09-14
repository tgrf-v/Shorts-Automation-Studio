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

export type ScriptStatus = 'draft' | 'generating' | 'ready' | 'failed';

export interface ScriptSegment {
  scene_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  duration: number;
  visual_description?: string | null;
  source_text?: string | null;
  adapted_text: string;
  word_count?: number;
  estimated_duration?: number;
}

export interface ScriptMetadata {
  id: string;
  project_id: string;
  source_transcript_id?: string | null;
  version: number;
  is_active: boolean;
  language: string;
  status: ScriptStatus;
  title: string;
  generation_provider: string;
  generation_model?: string | null;
  is_manually_edited: boolean;
  word_count: number;
  estimated_duration: number;
  source_duration?: number | null;
  duration_ratio?: number | null;
  created_at: string;
  updated_at: string;
}
