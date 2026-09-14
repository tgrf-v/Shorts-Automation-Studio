import { ApiError } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiException extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiException';
    this.status = status;
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      let errorMessage = `API request failed with status: ${response.status}`;
      try {
        const errorData = await response.json();
        if (errorData && typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (errorData && typeof errorData.message === 'string') {
          errorMessage = errorData.message;
        }
      } catch {
        // Response was not JSON
      }
      throw new ApiException(errorMessage, response.status);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiException) {
      throw error;
    }
    const message = error instanceof Error ? error.message : 'Unknown network error';
    throw new ApiException(message, 500);
  }
}

export function getAssetStreamUrl(assetId: string): string {
  return `${API_BASE_URL}/api/v1/assets/${assetId}/stream`;
}

export function getKeyframeImageUrl(keyframeId: string): string {
  return `${API_BASE_URL}/api/v1/keyframes/${keyframeId}/image`;
}

