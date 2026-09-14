export type ProjectStatus = 'draft' | 'analyzing' | 'ready' | 'failed';

export type MediaAssetType =
  | 'reference'
  | 'footage'
  | 'audio'
  | 'caption'
  | 'render'
  | 'other';

export interface MediaAsset {
  id: string;
  project_id: string;
  type: MediaAssetType;
  filename: string;
  storage_path: string;

  source_url?: string | null;
  source_platform?: string | null;
  mime_type: string;
  duration?: number | null;
  width?: number | null;
  height?: number | null;
  fps?: number | null;
  codec?: string | null;
  size: number;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: string;
  name: string;
  status: ProjectStatus;
  reference_asset_id?: string | null;
  reference_asset?: MediaAsset | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  projects: Project[];
  total: number;
}

export interface CreateProjectPayload {
  name: string;
}

export interface ApiError {
  message: string;
  status?: number;
}

// Milestone 3: Reference Video Analysis Types
export type AnalysisJobStatus =
  | 'queued'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface TranscriptSegment {
  start: number;
  end: number;
  text: string;
}

export interface Transcript {
  id: string;
  project_id: string;
  media_asset_id: string;
  language: string;
  provider: string;
  content: string;
  segments: TranscriptSegment[];
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Keyframe {
  id: string;
  scene_id: string;
  timestamp: number;
  image_path: string;
  quality_score: number;
  created_at: string;
}

export interface Scene {
  id: string;
  project_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  duration: number;
  description?: string | null;
  transcript_segment: TranscriptSegment[];
  keyframes: Keyframe[];
  created_at: string;
  updated_at: string;
}

export interface AnalysisJob {
  id: string;
  project_id: string;
  status: AnalysisJobStatus;
  progress: number;
  current_step: string;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectAnalysisResponse {
  project_id: string;
  status: string;
  job?: AnalysisJob | null;
  transcript?: Transcript | null;
  scenes: Scene[];
}

// Milestone 4: Script Adaptation Types
export type ScriptStatus = 'draft' | 'generating' | 'ready' | 'failed';
export type ScriptJobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';

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

export interface ScriptSummary {
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

export interface Script extends ScriptSummary {
  content: string;
  segments: ScriptSegment[];
  instructions?: string | null;
  error?: string | null;
}

export interface ScriptJob {
  id: string;
  project_id: string;
  script_id: string;
  status: ScriptJobStatus;
  progress: number;
  current_step: string;
  error?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScriptGeneratePayload {
  source_transcript_id?: string | null;
  provider?: string | null;
  model?: string | null;
  instructions?: string | null;
}

export interface ScriptGenerateResponse {
  job_id: string;
  script_id: string;
  status: string;
}

export interface ScriptUpdatePayload {
  title?: string;
  content?: string;
  segments?: ScriptSegment[];
}

// Milestone 5: TTS & Audio Timeline Types
export type TTSStatus = 'queued' | 'processing' | 'completed' | 'failed';
export type TTSJobStatus = 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled';

export interface AudioSegment {
  id: string;
  tts_generation_id: string;
  scene_id?: string | null;
  sequence: number;
  text: string;
  start_time: number;
  end_time: number;
  duration: number;
  audio_path?: string | null;
}

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

export interface TTSGeneratePayload {
  script_id?: string | null;
  provider?: string | null;
  voice?: string | null;
  model?: string | null;
}

export interface TTSGenerateResponse {
  generation_id: string;
  job_id: string;
  status: string;
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

export interface FootageSearchPayload {
  query?: string | null;
  queries?: string[] | null;
  provider?: string | null;
  max_results?: number;
}

// Milestone 7: Production Timeline Types
export type TimelineStatus = 'draft' | 'ready';

export interface CandidateBrief {
  id: string;
  title: string;
  source_platform: string;
  source_url: string;
  thumbnail_url?: string | null;
  duration?: number | null;
  visual_score: number;
  context_score: number;
  final_score: number;
  match_type: string;
}

export interface SceneBrief {
  id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  visual_description?: string | null;
  primary_keyframe_url?: string | null;
}

export interface ProductionTimelineItem {
  id: string;
  timeline_id: string;
  scene_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  duration: number;
  script_text: string;
  audio_segment_id?: string | null;
  footage_candidate_id?: string | null;
  footage_source_url?: string | null;
  footage_start_time: number;
  footage_end_time: number;
  transition: string;
  insufficient_footage_duration: boolean;
  duration_unknown: boolean;
  notes?: string | null;
  scene?: SceneBrief | null;
  candidate?: CandidateBrief | null;
  created_at: string;
  updated_at: string;
}

export interface ProductionTimelineSummary {
  id: string;
  project_id: string;
  script_id: string;
  tts_generation_id: string;
  version: number;
  status: TimelineStatus;
  duration: number;
  total_scenes: number;
  scenes_with_footage: number;
  scenes_missing_footage: number;
  is_active: boolean;
  is_stale?: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductionTimeline extends ProductionTimelineSummary {
  stale_reasons?: string[];
  average_similarity?: number | null;
  items: ProductionTimelineItem[];
}

export interface ProductionTimelineGeneratePayload {
  script_id?: string | null;
  tts_generation_id?: string | null;
}

export interface ProductionTimelineItemUpdatePayload {
  footage_candidate_id?: string | null;
  footage_start_time?: number | null;
  footage_end_time?: number | null;
  transition?: string | null;
  notes?: string | null;
}

// Milestone 8: Captions & Subtitles Types
export type CaptionTrackStatus = 'draft' | 'ready';
export type CaptionStyle = 'default' | 'bold' | 'highlight';
export type CaptionPosition = 'top' | 'center' | 'bottom';

export interface CaptionSegment {
  id: string;
  caption_track_id: string;
  sequence: number;
  start_time: number;
  end_time: number;
  duration: number;
  text: string;
  source_audio_segment_id?: string | null;
  scene_id?: string | null;
  scene_sequence?: number | null;
  style: CaptionStyle | string;
  position: CaptionPosition | string;
  created_at: string;
  updated_at: string;
}

export interface CaptionTrackSummary {
  id: string;
  project_id: string;
  script_id: string;
  tts_generation_id: string;
  production_timeline_id: string;
  version: number;
  language: string;
  status: CaptionTrackStatus;
  total_duration: number;
  total_segments: number;
  is_active: boolean;
  is_stale?: boolean;
  created_at: string;
  updated_at: string;
}

export interface CaptionTrack extends CaptionTrackSummary {
  stale_reasons?: string[];
  average_caption_duration?: number | null;
  scenes_covered?: number;
  segments: CaptionSegment[];
}

export interface CaptionGeneratePayload {
  script_id?: string | null;
  tts_generation_id?: string | null;
  production_timeline_id?: string | null;
  target_words_per_segment?: number;
}

export interface CaptionSegmentUpdatePayload {
  text?: string | null;
  start_time?: number | null;
  end_time?: number | null;
  style?: string | null;
  position?: string | null;
}
