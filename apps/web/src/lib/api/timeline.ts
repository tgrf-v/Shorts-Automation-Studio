import {
  ProductionTimeline,
  ProductionTimelineSummary,
  ProductionTimelineGeneratePayload,
  ProductionTimelineItemUpdatePayload,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function generateProductionTimeline(
  projectId: string,
  payload?: ProductionTimelineGeneratePayload
): Promise<ProductionTimeline> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/production-timeline/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload || {}),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to generate production timeline.');
  }

  return res.json();
}

export async function getActiveProductionTimeline(
  projectId: string
): Promise<ProductionTimeline | null> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/production-timeline`, {
    cache: 'no-store',
  });

  if (res.status === 404) {
    return null;
  }

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch active production timeline.');
  }

  return res.json();
}

export async function getProductionTimelineVersions(
  projectId: string
): Promise<ProductionTimelineSummary[]> {
  const res = await fetch(`${API_BASE}/api/v1/projects/${projectId}/production-timeline/versions`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch timeline versions.');
  }

  return res.json();
}

export async function getProductionTimeline(
  timelineId: string
): Promise<ProductionTimeline> {
  const res = await fetch(`${API_BASE}/api/v1/production-timelines/${timelineId}`, {
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to fetch timeline.');
  }

  return res.json();
}

export async function activateProductionTimeline(
  timelineId: string
): Promise<ProductionTimeline> {
  const res = await fetch(`${API_BASE}/api/v1/production-timelines/${timelineId}/activate`, {
    method: 'POST',
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to activate timeline.');
  }

  return res.json();
}

export async function updateProductionTimelineItem(
  itemId: string,
  payload: ProductionTimelineItemUpdatePayload
): Promise<ProductionTimeline> {
  const res = await fetch(`${API_BASE}/api/v1/production-timeline-items/${itemId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to update timeline item.');
  }

  return res.json();
}
