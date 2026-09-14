import {
  CaptionTrack,
  CaptionTrackSummary,
  CaptionGeneratePayload,
  CaptionSegmentUpdatePayload,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function generateCaptions(
  projectId: string,
  payload?: CaptionGeneratePayload
): Promise<CaptionTrack> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/captions/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate captions.');
  }

  return res.json();
}

export async function getActiveCaptionTrack(
  projectId: string
): Promise<CaptionTrack | null> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/captions/active`, {
    cache: 'no-store',
  });

  if (res.status === 404) {
    return null;
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch active caption track.');
  }

  return res.json();
}

export async function getCaptionTrackVersions(
  projectId: string
): Promise<CaptionTrackSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/captions`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch caption tracks.');
  }

  return res.json();
}

export async function getCaptionTrack(
  trackId: string
): Promise<CaptionTrack> {
  const res = await fetch(`${API_BASE}/api/v1/captions/${trackId}`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch caption track.');
  }

  return res.json();
}

export async function activateCaptionTrack(
  trackId: string
): Promise<CaptionTrack> {
  const res = await fetch(`${API_BASE}/api/v1/captions/${trackId}/activate`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to activate caption track.');
  }

  return res.json();
}

export async function updateCaptionSegment(
  segmentId: string,
  payload: CaptionSegmentUpdatePayload
): Promise<CaptionTrack> {
  const res = await fetch(`${API_BASE}/api/v1/caption-segments/${segmentId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to update caption segment.');
  }

  return res.json();
}

export async function exportCaptionSrt(trackId: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/v1/captions/${trackId}/srt`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    throw new Error('Failed to export SRT captions.');
  }

  return res.text();
}

export function getCaptionSrtDownloadUrl(trackId: string): string {
  return `${API_BASE}/api/v1/captions/${trackId}/srt?download=true`;
}
