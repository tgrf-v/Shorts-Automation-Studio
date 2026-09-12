'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { ProjectAnalysisResponse, AnalysisJob } from '@/lib/api/types';
import { startAnalysis, getProjectAnalysis, getAnalysisJob } from '@/lib/api/analysis';
import { AnalysisProgress } from '@/components/analysis/analysis-progress';
import { TranscriptViewer } from '@/components/analysis/transcript-viewer';
import { SceneList } from '@/components/analysis/scene-list';
import { Sparkles, RefreshCw, AlertCircle } from 'lucide-react';

interface AnalysisWorkspaceProps {
  projectId: string;
  hasReference: boolean;
  onStatusChange?: () => void;
}

export function AnalysisWorkspace({ projectId, hasReference, onStatusChange }: AnalysisWorkspaceProps) {
  const [analysis, setAnalysis] = useState<ProjectAnalysisResponse | null>(null);
  const [activeJob, setActiveJob] = useState<AnalysisJob | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [triggering, setTriggering] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalysis = useCallback(async () => {
    try {
      const data = await getProjectAnalysis(projectId);
      setAnalysis(data);
      if (data.job && (data.job.status === 'queued' || data.job.status === 'processing')) {
        setActiveJob(data.job);
      } else {
        setActiveJob(null);
      }
    } catch (err) {
      // Non-blocking initial error
      console.warn('Could not load analysis:', err);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  // Polling loop when an analysis job is active
  useEffect(() => {
    if (!activeJob) return;

    const interval = setInterval(async () => {
      try {
        const updated = await getAnalysisJob(activeJob.id);
        setActiveJob(updated);
        if (updated.status === 'completed') {
          clearInterval(interval);
          await fetchAnalysis();
          if (onStatusChange) onStatusChange();
        } else if (updated.status === 'failed' || updated.status === 'cancelled') {
          clearInterval(interval);
          setError(updated.error || 'Video analysis failed. Please try again.');
          await fetchAnalysis();
          if (onStatusChange) onStatusChange();
        }
      } catch (pollErr) {
        console.warn('Error polling job status:', pollErr);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob, fetchAnalysis, onStatusChange]);

  const handleStartAnalysis = async (reanalyze: boolean = false) => {
    setError(null);
    setTriggering(true);
    try {
      const job = await startAnalysis(projectId, reanalyze);
      setActiveJob(job);
      if (onStatusChange) onStatusChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis.');
    } finally {
      setTriggering(false);
    }
  };

  const handleSeekVideo = (timestamp: number) => {
    const video = document.getElementById('reference-video-player') as HTMLVideoElement | null;
    if (video) {
      video.currentTime = Math.max(0, timestamp);
      video.play().catch(() => {});
      video.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  if (!hasReference) {
    return (
      <div className="rounded-2xl border border-surface-border/60 bg-surface/30 p-8 text-center">
        <p className="text-xs text-slate-400">
          Upload a reference video above to enable structural video analysis.
        </p>
      </div>
    );
  }

  const isCompleted = Boolean(analysis?.transcript && analysis?.scenes && analysis.scenes.length > 0);

  return (
    <div className="space-y-8">
      {/* Top Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 rounded-2xl border border-surface-border bg-surface/50 p-6 backdrop-blur-sm">
        <div>
          <h3 className="text-sm font-semibold text-white">Reference Video Analysis</h3>
          <p className="text-xs text-slate-400">
            {isCompleted
              ? 'Analysis completed. Spoken dialogue, visual cuts, and scene descriptions are ready.'
              : 'Extract transcript, keyframes, and scene segmentation from reference video.'}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isCompleted ? (
            <button
              onClick={() => handleStartAnalysis(true)}
              disabled={triggering || Boolean(activeJob)}
              className="inline-flex items-center gap-2 rounded-xl border border-surface-border bg-surface px-4 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${triggering ? 'animate-spin' : ''}`} />
              <span>Reanalyze Reference</span>
            </button>
          ) : (
            <button
              onClick={() => handleStartAnalysis(false)}
              disabled={triggering || Boolean(activeJob)}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-blue-600/20 hover:bg-blue-500 transition-all disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" />
              <span>{triggering ? 'Queuing Task...' : 'Analyze Reference Video'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-rose-400 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => handleStartAnalysis(true)}
            className="rounded-lg bg-rose-500/20 px-3 py-1 font-medium hover:bg-rose-500/30 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Live Processing Indicator */}
      {activeJob && <AnalysisProgress job={activeJob} />}

      {/* Analysis Results View */}
      {isCompleted && analysis && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Transcript Viewer */}
          {analysis.transcript && (
            <div className="lg:col-span-5">
              <TranscriptViewer transcript={analysis.transcript} onSeek={handleSeekVideo} />
            </div>
          )}

          {/* Scene and Keyframe List */}
          <div className={analysis.transcript ? 'lg:col-span-7' : 'lg:col-span-12'}>
            <SceneList scenes={analysis.scenes} onSeek={handleSeekVideo} />
          </div>
        </div>
      )}
    </div>
  );
}
