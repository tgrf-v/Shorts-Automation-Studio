import { apiFetch } from './client';
import {
  Script,
  ScriptSummary,
  ScriptJob,
  ScriptGeneratePayload,
  ScriptGenerateResponse,
  ScriptUpdatePayload,
} from './types';

export async function generateScript(
  projectId: string,
  payload?: ScriptGeneratePayload
): Promise<ScriptGenerateResponse> {
  return apiFetch<ScriptGenerateResponse>(
    `/api/v1/projects/${projectId}/scripts/generate`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload || {}),
    }
  );
}

export async function getScriptJob(jobId: string): Promise<ScriptJob> {
  return apiFetch<ScriptJob>(`/api/v1/script-jobs/${jobId}`);
}

export async function getProjectScripts(projectId: string): Promise<ScriptSummary[]> {
  return apiFetch<ScriptSummary[]>(`/api/v1/projects/${projectId}/scripts`);
}

export async function getScript(scriptId: string): Promise<Script> {
  return apiFetch<Script>(`/api/v1/scripts/${scriptId}`);
}

export async function updateScript(
  scriptId: string,
  payload: ScriptUpdatePayload
): Promise<Script> {
  return apiFetch<Script>(`/api/v1/scripts/${scriptId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function activateScript(scriptId: string): Promise<Script> {
  return apiFetch<Script>(`/api/v1/scripts/${scriptId}/activate`, {
    method: 'POST',
  });
}
