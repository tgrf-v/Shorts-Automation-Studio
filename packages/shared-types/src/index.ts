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

export interface ProductionTimelineGenerateRequest {
  script_id?: string | null;
  tts_generation_id?: string | null;
}

export interface ProductionTimelineItemUpdateRequest {
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

export interface CaptionGenerateRequest {
  script_id?: string | null;
  tts_generation_id?: string | null;
  production_timeline_id?: string | null;
  target_words_per_segment?: number;
}

export interface CaptionSegmentUpdateRequest {
  text?: string | null;
  start_time?: number | null;
  end_time?: number | null;
  style?: string | null;
  position?: string | null;
}

// Milestone 9: BGM & SFX Audio Layer Timeline Types
export type AudioType = 'bgm' | 'sfx';
export type AudioTimelineStatus = 'draft' | 'ready';

export interface AudioAsset {
  id: string;
  project_id?: string | null;
  type: AudioType;
  name: string;
  file_path: string;
  source_url?: string | null;
  duration: number;
  format: string;
  sample_rate: number;
  channels: number;
  volume: number;
  created_at: string;
  updated_at: string;
}

export interface AudioLayer {
  id: string;
  project_id: string;
  audio_timeline_id: string;
  audio_asset_id: string;
  scene_id?: string | null;
  type: AudioType;
  name: string;
  start_time: number;
  end_time: number;
  volume: number;
  fade_in: number;
  fade_out: number;
  loop: boolean;
  enabled: boolean;
  ducking_enabled: boolean;
  ducking_level: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  audio_asset?: AudioAsset | null;
}

export interface AudioTimelineSummary {
  id: string;
  project_id: string;
  production_timeline_id: string;
  version: number;
  status: AudioTimelineStatus;
  total_duration: number;
  is_active: boolean;
  ducking_enabled: boolean;
  ducking_level: number;
  total_layers: number;
  bgm_layers_count: number;
  sfx_layers_count: number;
  created_at: string;
}

export interface AudioTimeline extends AudioTimelineSummary {
  updated_at: string;
  is_stale?: boolean;
  stale_reasons?: string[];
  layers: AudioLayer[];
}

export interface AudioTimelineGenerateRequest {
  bgm_asset_id?: string | null;
  production_timeline_id?: string | null;
  ducking_enabled?: boolean;
  ducking_level?: number;
}

export interface AudioLayerCreateRequest {
  audio_asset_id: string;
  type: AudioType;
  name?: string | null;
  start_time?: number;
  end_time?: number | null;
  volume?: number | null;
  fade_in?: number;
  fade_out?: number;
  loop?: boolean | null;
  enabled?: boolean;
  ducking_enabled?: boolean | null;
  ducking_level?: number;
  scene_id?: string | null;
  notes?: string | null;
}

export interface AudioLayerUpdateRequest {
  name?: string | null;
  start_time?: number | null;
  end_time?: number | null;
  volume?: number | null;
  fade_in?: number | null;
  fade_out?: number | null;
  loop?: boolean | null;
  enabled?: boolean | null;
  ducking_enabled?: boolean | null;
  ducking_level?: number | null;
  notes?: string | null;
}

export interface SFXSuggestionItem {
  type: string;
  category: string;
  keyword: string;
  reason: string;
  recommended_position: number;
  recommended_volume: number;
  recommended_duration: number;
}

export interface SceneSFXSuggestionsResponse {
  scene_id: string;
  scene_sequence: number;
  suggestions: SFXSuggestionItem[];
}


