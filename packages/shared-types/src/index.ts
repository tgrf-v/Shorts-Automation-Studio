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

// Milestone 5: TTS & Audio Timeline Types
export type TTSStatus = 'queued' | 'processing' | 'completed' | 'failed';

export interface AudioSegment {
  id: string;
  tts_generation_id: string;
  scene_id?: string | null;
  sequence: number;
  text: string;
  start_time: float_number;
  end_time: float_number;
  duration: float_number;
  audio_path?: string | null;
}

type float_number = number;

export interface AudioTimeline {
  generation_id: string;
  project_id: string;
  script_id: string;
  duration: number;
  segments_count: number;
  segments: AudioSegment[];
}

export interface TTSGenerationSummary {
  id: string;
  project_id: string;
  script_id: string;
  provider: string;
  model?: string | null;
  voice?: string | null;
  status: TTSStatus;
  duration?: number | null;
  audio_format: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TTSGeneration extends TTSGenerationSummary {
  audio_path?: string | null;
  sample_rate?: number | null;
  channels?: number | null;
  error?: string | null;
  segments: AudioSegment[];
}

export interface TTSJob {
  id: string;
  project_id: string;
  tts_generation_id: string;
  status: string;
  progress: number;
  current_step: string;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface TTSVoice {
  id: string;
  name: string;
  gender?: string | null;
  language_codes: string[];
  description?: string | null;
}

// Milestone 6: Visual Footage Search Types
export type FootageSearchStatus = 'queued' | 'searching' | 'ranking' | 'completed' | 'failed';

export interface FootageSearch {
  search_id: string;
  scene_id: string;
  project_id: string;
  query: string;
  search_provider: string;
  status: FootageSearchStatus;
  progress: number;
  current_step: string;
  total_results: number;
  error?: string | null;
  created_at: string;
}

export interface FootageCandidate {
  id: string;
  footage_search_id: string;
  scene_id: string;
  source_platform: string;
  source_url: string;
  video_url?: string | null;
  title: string;
  description?: string | null;
  thumbnail_url?: string | null;
  creator?: string | null;
  duration?: number | null;
  published_at?: string | null;
  search_query?: string | null;
  context_score: number;
  visual_score: number;
  similarity_score: number;
  final_score: number;
  match_type: string;
  is_selected: boolean;
  created_at: string;
}

export interface SceneFootageSelection {
  id: string;
  scene_id: string;
  candidate_id: string;
  status: string;
  notes?: string | null;
  candidate?: FootageCandidate | null;
  created_at: string;
  updated_at: string;
}

export interface SceneFootageSummaryItem {
  scene_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  duration: number;
  description?: string | null;
  total_candidates: number;
  has_selection: boolean;
  selected_candidate?: FootageCandidate | null;
}
