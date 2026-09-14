import { apiFetch } from './client';
import { Project, ProjectListResponse, CreateProjectPayload, MediaAsset } from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function getProjects(skip = 0, limit = 50): Promise<ProjectListResponse> {
  return apiFetch<ProjectListResponse>(`/api/v1/projects?skip=${skip}&limit=${limit}`);
}

export async function getProject(id: string): Promise<Project> {
  return apiFetch<Project>(`/api/v1/projects/${id}`);
}

export async function createProject(payload: CreateProjectPayload): Promise<Project> {
  return apiFetch<Project>('/api/v1/projects', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}

export async function deleteProject(id: string): Promise<void> {
  return apiFetch<void>(`/api/v1/projects/${id}`, {
    method: 'DELETE',
  });
}

export function uploadReferenceVideo(
  projectId: string,
  file: File,
  onProgress?: (percentage: number) => void
): Promise<MediaAsset> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);

    xhr.upload.addEventListener('progress', (event) => {
      if (event.lengthComputable && onProgress) {
        const percent = Math.round((event.loaded / event.total) * 100);
        onProgress(percent);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data: MediaAsset = JSON.parse(xhr.responseText);
          resolve(data);
        } catch {
          reject(new Error('Failed to parse upload response.'));
        }
      } else {
        let errorMsg = `Upload failed with status: ${xhr.status}`;
        try {
          const err = JSON.parse(xhr.responseText);
          if (err && err.detail) {
            errorMsg = err.detail;
          }
        } catch {
          // Response is not JSON
        }
        reject(new Error(errorMsg));
      }
    });

    xhr.addEventListener('error', () => {
      reject(new Error('Network error during file upload.'));
    });

    xhr.open('POST', `${API_BASE_URL}/api/v1/projects/${projectId}/reference`);
    xhr.send(formData);
  });
}
