import { apiFetch } from './client';
import { MediaAsset } from './types';

export async function getAsset(assetId: string): Promise<MediaAsset> {
  return apiFetch<MediaAsset>(`/api/v1/assets/${assetId}`);
}

export async function deleteAsset(assetId: string): Promise<void> {
  return apiFetch<void>(`/api/v1/assets/${assetId}`, {
    method: 'DELETE',
  });
}
