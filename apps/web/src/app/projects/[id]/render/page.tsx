'use client';

import React, { useEffect, useState, use, useCallback, useRef } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Film,
  Play,
  Download,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Clock,
  Sliders,
  Sparkles,
  Loader2,
  Video,
  Volume2,
  Subtitles,
  Music,
  Clapperboard,
  ExternalLink,
  ChevronDown,
  Check,
  Ban,
  FileVideo,
  Terminal,
  ShieldCheck,
  ShieldAlert,
} from 'lucide-react';
import { getProject } from '@/lib/api/projects';
import {
  getRenderChecklist,
  startRenderJob,
  listProjectRenders,
  getRenderJob,
  cancelRenderJob,
  getRenderStreamUrl,
  getRenderDownloadUrl,
} from '@/lib/api/render';
import {
  Project,
  RenderChecklistResponse,
  RenderJob,
  RenderJobSummary,
  RenderConfig,
} from '@/lib/api/types';

interface RenderPageProps {
  params: Promise<{ id: string }>;
}

export default function RenderPage({ params }: RenderPageProps) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  // State
  const [project, setProject] = useState<Project | null>(null);
  const [checklist, setChecklist] = useState<RenderChecklistResponse | null>(null);
  const [renders, setRenders] = useState<RenderJobSummary[]>([]);
  const [currentJob, setCurrentJob] = useState<RenderJob | null>(null);

  // Config State
  const [fps, setFps] = useState<number>(30);
  const [crf, setCrf] = useState<number>(23);
  const [preset, setPreset] = useState<string>('medium');
  const [showConfig, setShowConfig] = useState<boolean>(false);
  const [showLogs, setShowLogs] = useState<boolean>(false);

  // UI state
  const [loading, setLoading] = useState(true);
  const [startingRender, setStartingRender] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Polling ref
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Load initial data
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const [projData, chkData, renderList] = await Promise.all([
        getProject(projectId),
        getRenderChecklist(projectId),
        listProjectRenders(projectId),
      ]);

      setProject(projData);
      setChecklist(chkData);
      setRenders(renderList);

      // If there's an active or recent job, load it
      if (renderList.length > 0) {
        const latestSummary = renderList[0];
        const latestJob = await getRenderJob(latestSummary.id);
        setCurrentJob(latestJob);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load render workspace.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Polling for active render job
  useEffect(() => {
    if (!currentJob) return;

    const isActive =
      currentJob.status === 'pending' ||
      currentJob.status === 'validating' ||
      currentJob.status === 'preparing' ||
      currentJob.status === 'rendering';

    if (isActive) {
      pollIntervalRef.current = setInterval(async () => {
        try {
          const updated = await getRenderJob(currentJob.id);
          setCurrentJob(updated);

          // If it finished, refresh renders list and checklist
          if (updated.status === 'completed' || updated.status === 'failed' || updated.status === 'cancelled') {
            const list = await listProjectRenders(projectId);
            setRenders(list);
            if (updated.status === 'completed') {
              setActionSuccess('Video rendering completed successfully!');
            }
          }
        } catch {
          // ignore transient poll error
        }
      }, 2000);
    } else {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    };
  }, [currentJob?.id, currentJob?.status, projectId]);

  // Start Render Handler
  const handleStartRender = async () => {
    if (!checklist?.ready) return;

    setStartingRender(true);
    setError(null);
    setActionSuccess(null);

    const configPayload: RenderConfig = {
      width: 1080,
      height: 1920,
      fps,
      crf,
      preset,
      video_codec: 'libx264',
      audio_codec: 'aac',
      audio_bitrate: '192k',
      pixel_format: 'yuv420p',
      container: 'mp4',
    };

    try {
      const job = await startRenderJob(projectId, { config: configPayload });
      setCurrentJob(job);
      const list = await listProjectRenders(projectId);
      setRenders(list);
      setActionSuccess('Render job initiated.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start render.');
    } finally {
      setStartingRender(false);
    }
  };

  // Cancel Render Handler
  const handleCancelRender = async () => {
    if (!currentJob) return;

    setCancelling(true);
    try {
      const cancelled = await cancelRenderJob(currentJob.id);
      setCurrentJob(cancelled);
      const list = await listProjectRenders(projectId);
      setRenders(list);
      setActionSuccess('Render job cancelled.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel render.');
    } finally {
      setCancelling(false);
    }
  };

  // Select Job from History
  const handleSelectJob = async (jobId: string) => {
    try {
      setLoading(true);
      const job = await getRenderJob(jobId);
      setCurrentJob(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load selected job.');
    } finally {
      setLoading(false);
    }
  };

  // Format bytes helper
  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return 'N/A';
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(2)} MB`;
  };

  // Format seconds helper
  const formatSeconds = (sec?: number | null) => {
    if (sec === undefined || sec === null) return '0:00';
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const isRendering =
    currentJob?.status === 'pending' ||
    currentJob?.status === 'validating' ||
    currentJob?.status === 'preparing' ||
    currentJob?.status === 'rendering';

  if (loading && !currentJob) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-rose-500" />
          <p className="text-sm text-slate-400">Loading Render Workspace...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-20">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-surface-border pb-6">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="flex h-9 w-9 items-center justify-center rounded-xl border border-surface-border bg-surface text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                Video Rendering & Composition
              </h1>
              <span className="rounded-full border border-rose-500/30 bg-rose-500/10 px-2.5 py-0.5 text-xs text-rose-400">
                Milestone 10
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Project: <span className="text-slate-200 font-medium">{project?.name}</span> • Compose final 9:16 Shorts video with FFmpeg
            </p>
          </div>
        </div>

        {/* Navigation / Quick Links */}
        <div className="flex items-center gap-2 flex-wrap">
          <Link
            href={`/projects/${projectId}/timeline`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 transition-colors"
          >
            <Clapperboard className="h-3.5 w-3.5" />
            <span>Timeline (M7)</span>
          </Link>
          <Link
            href={`/projects/${projectId}/captions`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors"
          >
            <Subtitles className="h-3.5 w-3.5" />
            <span>Captions (M8)</span>
          </Link>
          <Link
            href={`/projects/${projectId}/audio`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-purple-500/30 bg-purple-500/10 px-3 py-1.5 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 transition-colors"
          >
            <Music className="h-3.5 w-3.5" />
            <span>Audio (M9)</span>
          </Link>
          <button
            onClick={loadData}
            className="flex h-8 w-8 items-center justify-center rounded-xl border border-surface-border bg-surface text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Refresh workspace"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-300 flex items-start gap-3">
          <AlertTriangle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold">Error:</span> {error}
          </div>
        </div>
      )}

      {actionSuccess && (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {/* Pre-flight Checklist Card */}
      <div className="rounded-2xl border border-surface-border bg-surface p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border/60 pb-4">
          <div className="flex items-center gap-2.5">
            {checklist?.ready ? (
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                <ShieldCheck className="h-4 w-4" />
              </div>
            ) : (
              <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400">
                <ShieldAlert className="h-4 w-4" />
              </div>
            )}
            <div>
              <h2 className="text-sm font-semibold text-white">Pre-Flight Dependency Checklist</h2>
              <p className="text-xs text-slate-400">
                Validates visual footage, narration timing, subtitle burn-in, and audio multi-tracks
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
                checklist?.ready
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/30'
              }`}
            >
              {checklist?.ready ? <Check className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
              {checklist?.ready ? 'Ready to Render' : 'Requirements Incomplete'}
            </span>
          </div>
        </div>

        {/* Requirements Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-4 text-xs">
          {/* 1. Production Timeline & Footage */}
          <div className="rounded-xl border border-surface-border/80 bg-slate-900/40 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                <Clapperboard className="h-3.5 w-3.5 text-emerald-400" />
                Footage & Timeline
              </span>
              {checklist?.details?.production_timeline && !checklist.errors.some(e => e.includes('footage')) ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <XCircle className="h-3.5 w-3.5 text-red-400" />
              )}
            </div>
            <p className="text-slate-400 leading-relaxed">
              {checklist?.details?.production_timeline ? (
                <>
                  Timeline v{checklist.details.production_timeline.version} ({checklist.details.production_timeline.total_scenes} scenes, {formatSeconds(checklist.details.production_timeline.duration)})
                </>
              ) : (
                'No active production timeline.'
              )}
            </p>
          </div>

          {/* 2. TTS Narration */}
          <div className="rounded-xl border border-surface-border/80 bg-slate-900/40 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                <Volume2 className="h-3.5 w-3.5 text-blue-400" />
                TTS Narration
              </span>
              {checklist?.details?.tts_generation ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <XCircle className="h-3.5 w-3.5 text-red-400" />
              )}
            </div>
            <p className="text-slate-400 leading-relaxed">
              {checklist?.details?.tts_generation ? (
                <>
                  Master narration ({formatSeconds(checklist.details.tts_generation.duration)})
                </>
              ) : (
                'No active TTS narration.'
              )}
            </p>
          </div>

          {/* 3. Captions */}
          <div className="rounded-xl border border-surface-border/80 bg-slate-900/40 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                <Subtitles className="h-3.5 w-3.5 text-amber-400" />
                Burn-In Captions
              </span>
              {checklist?.details?.caption_track ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <span className="text-[10px] text-amber-400 font-medium">Optional</span>
              )}
            </div>
            <p className="text-slate-400 leading-relaxed">
              {checklist?.details?.caption_track ? (
                <>
                  Track v{checklist.details.caption_track.version} ({checklist.details.caption_track.total_segments} styled segments)
                </>
              ) : (
                'No active captions (video rendered without subtitles).'
              )}
            </p>
          </div>

          {/* 4. Audio Timeline (BGM/SFX) */}
          <div className="rounded-xl border border-surface-border/80 bg-slate-900/40 p-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-200 flex items-center gap-1.5">
                <Music className="h-3.5 w-3.5 text-purple-400" />
                BGM & SFX Mix
              </span>
              {checklist?.details?.audio_timeline ? (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <span className="text-[10px] text-purple-400 font-medium">Optional</span>
              )}
            </div>
            <p className="text-slate-400 leading-relaxed">
              {checklist?.details?.audio_timeline ? (
                <>
                  Mix v{checklist.details.audio_timeline.version} ({checklist.details.audio_timeline.total_layers} audio layers)
                </>
              ) : (
                'No active audio mix (only narration included).'
              )}
            </p>
          </div>
        </div>

        {/* Errors & Warnings Callout */}
        {checklist?.errors && checklist.errors.length > 0 && (
          <div className="mt-4 rounded-xl border border-red-500/20 bg-red-500/5 p-3 space-y-1 text-xs text-red-300">
            <div className="font-semibold text-red-400 flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5" />
              Blocking Issues (Must resolve to render):
            </div>
            <ul className="list-disc list-inside space-y-1 text-slate-300 pl-1">
              {checklist.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))}
            </ul>
          </div>
        )}

        {checklist?.warnings && checklist.warnings.length > 0 && (
          <div className="mt-3 rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 space-y-1 text-xs text-amber-300">
            <div className="font-semibold text-amber-400 flex items-center gap-1.5">
              <AlertTriangle className="h-3.5 w-3.5" />
              Non-blocking Warnings:
            </div>
            <ul className="list-disc list-inside space-y-0.5 text-slate-300 pl-1">
              {checklist.warnings.map((warn, i) => (
                <li key={i}>{warn}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Main Workspace: Render Controls + Video Player */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: Render Job Controls & Status (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Active / Current Job Card */}
          <div className="rounded-2xl border border-surface-border bg-surface p-5 space-y-5">
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  <Film className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Renderer Studio</h2>
                  <p className="text-xs text-slate-400">Vertical 9:16 (1080x1920) H.264 / AAC Encoding</p>
                </div>
              </div>

              {/* Status Badge */}
              {currentJob ? (
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold capitalize ${
                    currentJob.status === 'completed'
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      : currentJob.status === 'failed'
                      ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                      : currentJob.status === 'cancelled'
                      ? 'bg-slate-500/10 text-slate-400 border border-slate-500/30'
                      : 'bg-rose-500/10 text-rose-400 border border-rose-500/30 animate-pulse'
                  }`}
                >
                  {isRendering && <Loader2 className="h-3 w-3 animate-spin" />}
                  {currentJob.status === 'completed' && <Check className="h-3 w-3" />}
                  {currentJob.status === 'failed' && <XCircle className="h-3 w-3" />}
                  {currentJob.status === 'cancelled' && <Ban className="h-3 w-3" />}
                  {currentJob.status}
                </span>
              ) : (
                <span className="text-xs text-slate-500">No active job</span>
              )}
            </div>

            {/* Progress Bar (when active) */}
            {isRendering && currentJob && (
              <div className="space-y-2 rounded-xl border border-rose-500/30 bg-rose-500/5 p-4">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-rose-300 flex items-center gap-2">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-rose-400" />
                    {currentJob.current_step || 'Rendering in progress...'}
                  </span>
                  <span className="font-mono font-bold text-rose-300">{currentJob.progress_percentage}%</span>
                </div>
                <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-rose-500 to-amber-500 transition-all duration-300"
                    style={{ width: `${currentJob.progress_percentage}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-400 pt-1">
                  Applying smart center-crop, multi-track audio ducking, and subtitle burn-in.
                </p>
              </div>
            )}

            {/* Render Execution Error Callout */}
            {currentJob?.status === 'failed' && (
              <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 space-y-2 text-xs text-red-300">
                <div className="font-semibold text-red-400 flex items-center gap-2">
                  <XCircle className="h-4 w-4" />
                  Render Failed:
                </div>
                <p className="font-mono text-[11px] text-red-200 bg-black/40 p-2.5 rounded-lg overflow-x-auto whitespace-pre-wrap">
                  {currentJob.error_message || 'Unknown render error.'}
                </p>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center gap-3 flex-wrap pt-2">
              <button
                onClick={handleStartRender}
                disabled={!checklist?.ready || startingRender || isRendering}
                className="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-rose-600/25 hover:bg-rose-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                {startingRender ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Initiating Render...</span>
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 fill-white" />
                    <span>Start Video Render</span>
                  </>
                )}
              </button>

              {isRendering && (
                <button
                  onClick={handleCancelRender}
                  disabled={cancelling}
                  className="inline-flex items-center gap-2 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-xs font-semibold text-red-300 hover:bg-red-500/20 disabled:opacity-50 transition-colors"
                >
                  {cancelling ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Ban className="h-3.5 w-3.5" />
                  )}
                  <span>Cancel Job</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => setShowConfig(!showConfig)}
                className="inline-flex items-center gap-2 rounded-xl border border-surface-border bg-slate-900/60 px-3.5 py-2.5 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
              >
                <Sliders className="h-3.5 w-3.5 text-slate-400" />
                <span>Encoder Settings</span>
                <ChevronDown
                  className={`h-3 w-3 text-slate-400 transition-transform ${
                    showConfig ? 'rotate-180' : ''
                  }`}
                />
              </button>
            </div>

            {/* Collapsible Encoder Config Settings */}
            {showConfig && (
              <div className="rounded-xl border border-surface-border/80 bg-slate-900/50 p-4 space-y-4 text-xs">
                <h3 className="font-semibold text-slate-200">Encoding Parameters</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {/* Framerate */}
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">Frame Rate (FPS)</label>
                    <select
                      value={fps}
                      onChange={(e) => setFps(Number(e.target.value))}
                      disabled={isRendering}
                      className="w-full rounded-lg border border-surface-border bg-surface px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      <option value={30}>30 FPS (Standard)</option>
                      <option value={60}>60 FPS (Ultra Smooth)</option>
                    </select>
                  </div>

                  {/* CRF Quality */}
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">
                      Quality CRF ({crf}) <span className="text-slate-500">(18=High, 28=Low)</span>
                    </label>
                    <select
                      value={crf}
                      onChange={(e) => setCrf(Number(e.target.value))}
                      disabled={isRendering}
                      className="w-full rounded-lg border border-surface-border bg-surface px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      <option value={18}>18 (Near Lossless, larger file)</option>
                      <option value={20}>20 (Very High)</option>
                      <option value={23}>23 (Balanced - Recommended)</option>
                      <option value={26}>26 (Smaller file)</option>
                    </select>
                  </div>

                  {/* Preset */}
                  <div>
                    <label className="block text-[11px] text-slate-400 mb-1">Encoding Preset</label>
                    <select
                      value={preset}
                      onChange={(e) => setPreset(e.target.value)}
                      disabled={isRendering}
                      className="w-full rounded-lg border border-surface-border bg-surface px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
                    >
                      <option value="ultrafast">Ultrafast (Draft)</option>
                      <option value="fast">Fast</option>
                      <option value="medium">Medium (Standard)</option>
                      <option value="slow">Slow (Best Compression)</option>
                    </select>
                  </div>
                </div>

                <div className="pt-2 text-[11px] text-slate-500 space-y-1">
                  <p>• Output Resolution: 1080x1920 (9:16 Vertical YouTube Shorts standard)</p>
                  <p>• Video Codec: H.264 (`libx264`, yuv420p) • Audio Codec: AAC stereo (192 kbps)</p>
                </div>
              </div>
            )}
          </div>

          {/* Execution Command / Logs Card */}
          {currentJob && (
            <div className="rounded-2xl border border-surface-border bg-surface p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-slate-400" />
                  <h3 className="text-xs font-semibold text-slate-200">Execution Pipeline Log</h3>
                </div>
                <button
                  type="button"
                  onClick={() => setShowLogs(!showLogs)}
                  className="text-[11px] text-slate-400 hover:text-white transition-colors"
                >
                  {showLogs ? 'Hide Log' : 'View Command'}
                </button>
              </div>

              {showLogs && (
                <div className="mt-2 rounded-xl bg-black/70 border border-slate-800 p-3 font-mono text-[10px] text-slate-300 overflow-x-auto whitespace-pre-wrap max-h-48">
                  {currentJob.execution_log || 'No command execution log available.'}
                </div>
              )}
            </div>
          )}

          {/* Render History Table */}
          <div className="rounded-2xl border border-surface-border bg-surface p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-3">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-slate-400" />
                <h3 className="text-sm font-semibold text-white">Render History</h3>
              </div>
              <span className="text-xs text-slate-400">{renders.length} renders</span>
            </div>

            {renders.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-6">
                No render jobs executed yet.
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="border-b border-surface-border text-[11px] uppercase text-slate-400">
                    <tr>
                      <th className="pb-2.5">Date</th>
                      <th className="pb-2.5">Status</th>
                      <th className="pb-2.5">Duration</th>
                      <th className="pb-2.5">Size</th>
                      <th className="pb-2.5 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border/60">
                    {renders.map((r) => (
                      <tr
                        key={r.id}
                        className={`hover:bg-slate-800/40 cursor-pointer transition-colors ${
                          currentJob?.id === r.id ? 'bg-rose-500/5' : ''
                        }`}
                        onClick={() => handleSelectJob(r.id)}
                      >
                        <td className="py-2.5 text-slate-300 font-medium">
                          {new Date(r.created_at).toLocaleDateString()} {new Date(r.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </td>
                        <td className="py-2.5">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold capitalize ${
                              r.status === 'completed'
                                ? 'bg-emerald-500/10 text-emerald-400'
                                : r.status === 'failed'
                                ? 'bg-red-500/10 text-red-400'
                                : r.status === 'cancelled'
                                ? 'bg-slate-500/10 text-slate-400'
                                : 'bg-rose-500/10 text-rose-400'
                            }`}
                          >
                            {r.status}
                          </span>
                        </td>
                        <td className="py-2.5 text-slate-400 font-mono">
                          {formatSeconds(r.duration)}
                        </td>
                        <td className="py-2.5 text-slate-400 font-mono">
                          {formatBytes(r.file_size_bytes)}
                        </td>
                        <td className="py-2.5 text-right">
                          {r.status === 'completed' && (
                            <a
                              href={getRenderDownloadUrl(r.id)}
                              target="_blank"
                              rel="noreferrer"
                              onClick={(e) => e.stopPropagation()}
                              className="inline-flex items-center gap-1 text-[11px] font-medium text-rose-400 hover:text-rose-300"
                            >
                              <Download className="h-3 w-3" />
                              <span>MP4</span>
                            </a>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: 9:16 Video Player Showcase (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="rounded-2xl border border-surface-border bg-surface p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-surface-border/60 pb-3">
              <div className="flex items-center gap-2">
                <Video className="h-4 w-4 text-rose-400" />
                <h3 className="text-sm font-semibold text-white">Preview Output (9:16)</h3>
              </div>
              {currentJob?.status === 'completed' && (
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                  1080 × 1920
                </span>
              )}
            </div>

            {/* Video Player Display Container */}
            <div className="flex flex-col items-center justify-center">
              {currentJob?.status === 'completed' ? (
                <div className="w-full max-w-[280px] sm:max-w-[320px] rounded-2xl overflow-hidden border-2 border-slate-700/80 shadow-2xl bg-black aspect-[9/16] relative flex items-center justify-center">
                  <video
                    key={currentJob.id}
                    src={getRenderStreamUrl(currentJob.id)}
                    controls
                    playsInline
                    className="w-full h-full object-cover"
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>
              ) : (
                <div className="w-full max-w-[280px] sm:max-w-[320px] rounded-2xl border border-dashed border-surface-border bg-slate-900/60 aspect-[9/16] flex flex-col items-center justify-center p-6 text-center space-y-3">
                  {isRendering ? (
                    <>
                      <Loader2 className="h-10 w-10 text-rose-500 animate-spin" />
                      <p className="text-xs font-semibold text-slate-200">
                        Composing Video...
                      </p>
                      <p className="text-[11px] text-slate-400">
                        FFmpeg is processing 9:16 crops, visual transitions, audio mix, and subtitles.
                      </p>
                    </>
                  ) : (
                    <>
                      <FileVideo className="h-12 w-12 text-slate-600 stroke-[1.5]" />
                      <p className="text-xs font-semibold text-slate-300">
                        No Rendered Video Yet
                      </p>
                      <p className="text-[11px] text-slate-500 leading-relaxed">
                        Verify pre-flight requirements and press &ldquo;Start Video Render&rdquo; to generate your final YouTube Shorts video.
                      </p>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* Video Details & Download */}
            {currentJob?.status === 'completed' && (
              <div className="pt-3 border-t border-surface-border/60 space-y-4">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-slate-900/50 p-2 rounded-lg">
                    <span className="text-slate-500 block text-[10px]">Duration</span>
                    <span className="font-mono text-slate-200 font-semibold">
                      {formatSeconds(currentJob.duration)}
                    </span>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded-lg">
                    <span className="text-slate-500 block text-[10px]">File Size</span>
                    <span className="font-mono text-slate-200 font-semibold">
                      {formatBytes(currentJob.file_size_bytes)}
                    </span>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded-lg">
                    <span className="text-slate-500 block text-[10px]">Codecs</span>
                    <span className="font-mono text-slate-200 text-[11px]">
                      {currentJob.video_codec} / {currentJob.audio_codec}
                    </span>
                  </div>
                  <div className="bg-slate-900/50 p-2 rounded-lg">
                    <span className="text-slate-500 block text-[10px]">Framerate</span>
                    <span className="font-mono text-slate-200 font-semibold">
                      {currentJob.fps} FPS
                    </span>
                  </div>
                </div>

                <a
                  href={getRenderDownloadUrl(currentJob.id)}
                  download
                  className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-rose-600 to-amber-600 px-4 py-2.5 text-xs font-semibold text-white shadow-md shadow-rose-600/20 hover:from-rose-500 hover:to-amber-500 transition-all"
                >
                  <Download className="h-4 w-4" />
                  <span>Download Final Shorts Video (.mp4)</span>
                </a>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
