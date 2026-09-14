import { apiFetch } from './client';
import {
  FootageSearch,
  FootageCandidate,
  SceneFootageSelection,
  SceneFootageSummaryItem,
  FootageSearchPayload,
} from './types';

export async function searchFootageForScene(
  sceneId: string,
  payload?: FootageSearchPayload
): Promise<FootageSearch> {
  return apiFetch<FootageSearch>(
    `/api/v1/scenes/${sceneId}/footage-search`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function getFootageSearch(searchId: string): Promise<FootageSearch> {
  return apiFetch<FootageSearch>(`/api/v1/footage-searches/${searchId}`);
}

export async function listSceneFootageCandidates(
  sceneId: string,
  options?: { platform?: string; searchId?: string; skip?: number; limit?: number }
): Promise<FootageCandidate[]> {
  const params = new URLSearchParams();
  if (options?.platform) params.append('platform', options.platform);
  if (options?.searchId) params.append('search_id', options.searchId);
  if (options?.skip !== undefined) params.append('skip', String(options.skip));
  if (options?.limit !== undefined) params.append('limit', String(options.limit));

  const query = params.toString() ? `?${params.toString()}` : '';
  return apiFetch<FootageCandidate[]>(`/api/v1/scenes/${sceneId}/footage-candidates${query}`);
}

export async function getFootageCandidate(candidateId: string): Promise<FootageCandidate> {
  return apiFetch<FootageCandidate>(`/api/v1/footage-candidates/${candidateId}`);
}

export async function selectFootageCandidate(
  candidateId: string,
  notes?: string
): Promise<SceneFootageSelection> {
  return apiFetch<SceneFootageSelection>(
    `/api/v1/footage-candidates/${candidateId}/select`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
    }
  );
}

export async function getSceneFootageSelection(sceneId: string): Promise<SceneFootageSelection | null> {
  return apiFetch<SceneFootageSelection | null>(`/api/v1/scenes/${sceneId}/footage-selection`);
}

export async function getProjectFootageSummary(projectId: string): Promise<SceneFootageSummaryItem[]> {
  return apiFetch<SceneFootageSummaryItem[]>(`/api/v1/projects/${projectId}/footage/summary`);
}

export async function listSceneFootageSearches(sceneId: string): Promise<FootageSearch[]> {
  return apiFetch<FootageSearch[]>(`/api/v1/scenes/${sceneId}/footage-searches`);
}

export async function uploadCustomFootage(
  sceneId: string,
  formData: FormData
): Promise<FootageCandidate> {
  return apiFetch<FootageCandidate>(
    `/api/v1/scenes/${sceneId}/custom-footage`,
    {
      method: 'POST',
      body: formData,
    }
  );
}

export async function selectCandidateForRange(
  candidateId: string,
  startSequence: number,
  endSequence: number,
  projectId?: string
): Promise<SceneFootageSelection[]> {
  return apiFetch<SceneFootageSelection[]>(
    `/api/v1/footage-candidates/${candidateId}/range-select`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        start_sequence: startSequence,
        end_sequence: endSequence,
        project_id: projectId,
      }),
    }
  );
}
