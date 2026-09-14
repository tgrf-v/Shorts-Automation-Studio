import {
  AudioAsset,
  AudioTimeline,
  AudioTimelineSummary,
  AudioLayer,
  AudioType,
  AudioTimelineGeneratePayload,
  AudioLayerCreatePayload,
  AudioLayerUpdatePayload,
  SceneSFXSuggestionsResponse,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function uploadAudioAsset(
  projectId: string,
  file: File,
  type: AudioType,
  name?: string,
  volume?: number
): Promise<AudioAsset> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('type', type);
  if (name) formData.append('name', name);
  if (volume !== undefined) formData.append('volume', volume.toString());

  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/audio-assets/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to upload audio asset.');
  }

  return res.json();
}

export async function listAudioAssets(
  projectId: string,
  type?: AudioType
): Promise<AudioAsset[]> {
  const url = new URL(`${API_BASE}/api/v1/projects/${projectId}/audio-assets`);
  if (type) url.searchParams.set('type', type);

  const res = await fetch(url.toString(), { cache: 'no-store' });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to list audio assets.');
  }

  return res.json();
}

export async function deleteAudioAsset(assetId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/audio-assets/${assetId}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to delete audio asset.');
  }
}

export function getAudioStreamUrl(assetId: string): string {
  return `${API_BASE}/api/v1/audio-assets/${assetId}/stream`;
}

export async function generateAudioTimeline(
  projectId: string,
  payload?: AudioTimelineGeneratePayload
): Promise<AudioTimeline> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/audio-timeline/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate audio timeline.');
  }

  return res.json();
}

export async function getActiveAudioTimeline(
  projectId: string
): Promise<AudioTimeline | null> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/audio-timeline`, {
    cache: 'no-store',
  });

  if (res.status === 404) {
    return null;
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch active audio timeline.');
  }

  return res.json();
}

export async function getAudioTimelineVersions(
  projectId: string
): Promise<AudioTimelineSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/audio-timeline/versions`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch audio timeline versions.');
  }

  return res.json();
}

export async function getAudioTimeline(
  timelineId: string
): Promise<AudioTimeline> {
  const res = await fetch(`${API_BASE}/api/v1/audio-timelines/${timelineId}`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch audio timeline.');
  }

  return res.json();
}

export async function activateAudioTimeline(
  timelineId: string
): Promise<AudioTimeline> {
  const res = await fetch(`${API_BASE}/api/v1/audio-timelines/${timelineId}/activate`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to activate audio timeline.');
  }

  return res.json();
}

export async function addAudioLayer(
  projectId: string,
  payload: AudioLayerCreatePayload,
  timelineId?: string
): Promise<AudioLayer> {
  const url = new URL(`${API_BASE}/api/v1/projects/${projectId}/audio-layers`);
  if (timelineId) url.searchParams.set('timeline_id', timelineId);

  const res = await fetch(url.toString(), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to add audio layer.');
  }

  return res.json();
}

export async function updateAudioLayer(
  layerId: string,
  payload: AudioLayerUpdatePayload
): Promise<AudioLayer> {
  const res = await fetch(`${API_BASE}/api/v1/audio-layers/${layerId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to update audio layer.');
  }

  return res.json();
}

export async function deleteAudioLayer(layerId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/v1/audio-layers/${layerId}`, {
    method: 'DELETE',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to delete audio layer.');
  }
}

export async function getSceneSFXSuggestions(
  sceneId: string
): Promise<SceneSFXSuggestionsResponse> {
  const res = await fetch(`${API_BASE}/api/v1/scenes/${sceneId}/sfx-suggestions`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch scene SFX suggestions.');
  }

  return res.json();
}
