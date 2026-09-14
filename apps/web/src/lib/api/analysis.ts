import { apiFetch } from './client';
import { AnalysisJob, ProjectAnalysisResponse } from './types';

export async function startAnalysis(
  projectId: string,
  reanalyze: boolean = false
): Promise<AnalysisJob> {
  const query = reanalyze ? '?reanalyze=true' : '';
  return apiFetch<AnalysisJob>(`/api/v1/projects/${projectId}/analyze${query}`, {
    method: 'POST',
  });
}

export async function getProjectAnalysis(
  projectId: string
): Promise<ProjectAnalysisResponse> {
  return apiFetch<ProjectAnalysisResponse>(`/api/v1/projects/${projectId}/analysis`);
}

export async function getAnalysisJob(
  jobId: string
): Promise<AnalysisJob> {
  return apiFetch<AnalysisJob>(`/api/v1/analysis-jobs/${jobId}`);
}
