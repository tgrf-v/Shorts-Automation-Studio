import { apiFetch } from './client';
import {
  TTSGeneration,
  TTSGenerationSummary,
  TTSJob,
  TTSVoice,
  AudioTimeline,
  TTSGeneratePayload,
  TTSGenerateResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function generateTTS(
  projectId: string,
  payload?: TTSGeneratePayload
): Promise<TTSGenerateResponse> {
  return apiFetch<TTSGenerateResponse>(
    `/api/v1/projects/${projectId}/tts/generate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function getTTSJob(jobId: string): Promise<TTSJob> {
  return apiFetch<TTSJob>(`/api/v1/tts/jobs/${jobId}`);
}

export async function getProjectTTSGenerations(projectId: string): Promise<TTSGenerationSummary[]> {
  return apiFetch<TTSGenerationSummary[]>(`/api/v1/projects/${projectId}/tts`);
}

export async function getTTSGeneration(generationId: string): Promise<TTSGeneration> {
  return apiFetch<TTSGeneration>(`/api/v1/tts/${generationId}`);
}

export async function getTTSTimeline(generationId: string): Promise<AudioTimeline> {
  return apiFetch<AudioTimeline>(`/api/v1/tts/${generationId}/timeline`);
}

export async function activateTTSGeneration(generationId: string): Promise<TTSGenerationSummary> {
  return apiFetch<TTSGenerationSummary>(`/api/v1/tts/${generationId}/activate`, {
    method: 'POST',
  });
}

export async function getTTSVoices(provider?: string): Promise<TTSVoice[]> {
  const query = provider ? `?provider=${encodeURIComponent(provider)}` : '';
  return apiFetch<TTSVoice[]>(`/api/v1/tts/voices${query}`);
}

export function getTTSStreamUrl(generationId: string): string {
  return `${API_BASE}/api/v1/tts/${generationId}/stream`;
}

export function getSegmentStreamUrl(segmentId: string): string {
  return `${API_BASE}/api/v1/tts/segments/${segmentId}/stream`;
}
