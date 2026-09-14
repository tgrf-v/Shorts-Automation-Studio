import {
  RenderChecklistResponse,
  RenderJob,
  RenderJobSummary,
  RenderJobCreatePayload,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getRenderChecklist(projectId: string): Promise<RenderChecklistResponse> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/render-checklist`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to fetch render checklist.');
  }
  return res.json();
}

export async function startRenderJob(
  projectId: string,
  payload?: RenderJobCreatePayload
): Promise<RenderJob> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/renders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to trigger video render job.');
  }
  return res.json();
}

export async function listProjectRenders(projectId: string): Promise<RenderJobSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/renders`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to list render jobs.');
  }
  return res.json();
}

export async function getRenderJob(jobId: string): Promise<RenderJob> {
  const res = await fetch(`${API_BASE}/api/v1/render-jobs/${jobId}`, {
    cache: 'no-store',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to get render job status.');
  }
  return res.json();
}

export async function cancelRenderJob(jobId: string): Promise<RenderJob> {
  const res = await fetch(`${API_BASE}/api/v1/render-jobs/${jobId}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to cancel render job.');
  }
  return res.json();
}

export function getRenderStreamUrl(jobId: string): string {
  return `${API_BASE}/api/v1/render-jobs/${jobId}/stream`;
}

export function getRenderDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/v1/render-jobs/${jobId}/download`;
}
