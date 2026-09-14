'use client';

import React, { useEffect, useState, use, useCallback } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Subtitles,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ChevronDown,
  Loader2,
  Download,
  Check,
  Edit2,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Sliders,
  X,
  Copy,
  AlertCircle,
  Music,
  Clapperboard,
} from 'lucide-react';
import { getProject } from '@/lib/api/projects';
import {
  generateCaptions,
  getActiveCaptionTrack,
  getCaptionTrackVersions,
  getCaptionTrack,
  activateCaptionTrack,
  updateCaptionSegment,
  exportCaptionSrt,
  getCaptionSrtDownloadUrl,
} from '@/lib/api/captions';
import {
  Project,
  CaptionTrack,
  CaptionTrackSummary,
  CaptionSegment,
} from '@/lib/api/types';

interface CaptionsPageProps {
  params: Promise<{ id: string }>;
}

export default function CaptionsPage({ params }: CaptionsPageProps) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  const [project, setProject] = useState<Project | null>(null);
  const [track, setTrack] = useState<CaptionTrack | null>(null);
  const [versions, setVersions] = useState<CaptionTrackSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Selected segment for 9:16 phone preview
  const [selectedSegmentIndex, setSelectedSegmentIndex] = useState<number>(0);

  // Editing state for segment: segmentId -> { text, start, end, style, position, saving, error }
  const [editingSegmentId, setEditingSegmentId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<{
    text: string;
    start: number;
    end: number;
    style: string;
    position: string;
    saving: boolean;
    error: string | null;
  }>({
    text: '',
    start: 0,
    end: 0,
    style: 'default',
    position: 'bottom',
    saving: false,
    error: null,
  });

  // SRT Modal State
  const [srtModalOpen, setSrtModalOpen] = useState(false);
  const [srtContent, setSrtContent] = useState<string>('');
  const [copyingSrt, setCopyingSrt] = useState(false);

  // 1. Initial Load
  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [projData, versData] = await Promise.all([
        getProject(projectId),
        getCaptionTrackVersions(projectId).catch(() => []),
      ]);
      setProject(projData);
      setVersions(versData);

      const activeTrack = await getActiveCaptionTrack(projectId);
      setTrack(activeTrack);
      if (activeTrack && activeTrack.segments.length > 0) {
        setSelectedSegmentIndex(0);
      }
    } catch (err) {
      console.error('Failed to load captions workspace:', err);
      setError(err instanceof Error ? err.message : 'Failed to load captions workspace.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 2. Generate New Caption Track
  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      setActionSuccess(null);

      const newTrack = await generateCaptions(projectId);
      setTrack(newTrack);
      setSelectedSegmentIndex(0);

      const vers = await getCaptionTrackVersions(projectId);
      setVersions(vers);

      setActionSuccess(`Captions v${newTrack.version} generated successfully!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate captions.');
    } finally {
      setGenerating(false);
    }
  };

  // 3. Switch Track Version
  const handleSelectVersion = async (versionId: string) => {
    try {
      setLoading(true);
      const fullTrack = await getCaptionTrack(versionId);
      setTrack(fullTrack);
      setSelectedSegmentIndex(0);
      setEditingSegmentId(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load caption track.');
    } finally {
      setLoading(false);
    }
  };

  // 4. Activate Track
  const handleActivate = async () => {
    if (!track) return;
    try {
      setLoading(true);
      const active = await activateCaptionTrack(track.id);
      setTrack(active);
      const vers = await getCaptionTrackVersions(projectId);
      setVersions(vers);
      setActionSuccess(`Captions v${track.version} is now active!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate caption track.');
    } finally {
      setLoading(false);
    }
  };

  // 5. Open Edit Form
  const handleOpenEdit = (seg: CaptionSegment) => {
    setEditingSegmentId(seg.id);
    setEditForm({
      text: seg.text,
      start: seg.start_time,
      end: seg.end_time,
      style: seg.style || 'default',
      position: seg.position || 'bottom',
      saving: false,
      error: null,
    });
  };

  // 6. Save Segment Edit
  const handleSaveSegment = async (segmentId: string) => {
    setEditForm((prev) => ({ ...prev, saving: true, error: null }));
    try {
      const updatedTrack = await updateCaptionSegment(segmentId, {
        text: editForm.text,
        start_time: Number(editForm.start),
        end_time: Number(editForm.end),
        style: editForm.style,
        position: editForm.position,
      });
      setTrack(updatedTrack);
      setEditingSegmentId(null);
      setActionSuccess('Caption segment updated successfully.');
    } catch (err) {
      setEditForm((prev) => ({
        ...prev,
        saving: false,
        error: err instanceof Error ? err.message : 'Failed to update caption segment.',
      }));
    }
  };

  // 7. View / Export SRT
  const handleOpenSrtModal = async () => {
    if (!track) return;
    try {
      const content = await exportCaptionSrt(track.id);
      setSrtContent(content);
      setSrtModalOpen(true);
    } catch (err) {
      alert('Failed to generate SRT output.');
    }
  };

  const handleCopySrt = () => {
    navigator.clipboard.writeText(srtContent);
    setCopyingSrt(true);
    setTimeout(() => setCopyingSrt(false), 2000);
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = (sec % 60).toFixed(2);
    return `${m.toString().padStart(2, '0')}:${parseFloat(s) < 10 ? '0' : ''}${s}`;
  };

  const activeSegment = track?.segments[selectedSegmentIndex];

  if (loading && !project) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center p-8">
        <div className="flex flex-col items-center space-y-3 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin text-cyan-500" />
          <span className="text-sm">Loading Captions & Subtitles workspace...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Header & Breadcrumb */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-surface-border">
        <div className="flex items-center space-x-4">
          <Link
            href={`/projects/${projectId}`}
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-surface-border bg-surface text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                Captions & Subtitles
              </h1>
              <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 text-xs text-cyan-400">
                Milestone 8
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Project: <span className="text-slate-200 font-medium">{project?.name}</span> • Readability-split subtitles synchronized with TTS
            </p>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Version Switcher */}
          {versions.length > 0 && (
            <div className="relative">
              <select
                value={track?.id || ''}
                onChange={(e) => handleSelectVersion(e.target.value)}
                className="appearance-none rounded-xl border border-surface-border bg-surface pl-3 pr-8 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 cursor-pointer focus:outline-none"
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    Captions v{v.version} {v.is_active ? '(Active)' : ''} — {v.total_segments} lines
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            </div>
          )}

          {/* Activate Button */}
          {track && !track.is_active && (
            <button
              onClick={handleActivate}
              className="inline-flex items-center gap-1.5 rounded-xl border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition-colors"
            >
              <Check className="h-3.5 w-3.5" />
              <span>Set as Active</span>
            </button>
          )}

          {/* Export SRT */}
          {track && (
            <button
              onClick={handleOpenSrtModal}
              className="inline-flex items-center gap-1.5 rounded-xl border border-surface-border bg-surface px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
            >
              <Download className="h-3.5 w-3.5 text-cyan-400" />
              <span>Export SRT</span>
            </button>
          )}

          {/* Generate / Regenerate */}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-cyan-600/20 hover:bg-cyan-500 disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Generating Captions...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" />
                <span>{track ? 'Regenerate Captions' : 'Generate Captions'}</span>
              </>
            )}
          </button>

          <Link
            href={`/projects/${projectId}/timeline`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 transition-colors"
          >
            <Clapperboard className="h-3.5 w-3.5" />
            <span>Timeline (M7)</span>
          </Link>

          <Link
            href={`/projects/${projectId}/audio`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-purple-500/30 bg-purple-500/10 px-3 py-2 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 transition-colors"
          >
            <Music className="h-3.5 w-3.5" />
            <span>Audio & SFX (M9)</span>
          </Link>

          <button
            onClick={fetchData}
            className="inline-flex items-center gap-1.5 rounded-xl border border-surface-border bg-surface px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 flex items-start gap-3 text-rose-400">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium">Error</p>
            <p className="text-xs text-rose-300/80 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {actionSuccess && (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 flex items-start gap-3 text-emerald-400">
          <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium">Success</p>
            <p className="text-xs text-emerald-300/80 mt-0.5">{actionSuccess}</p>
          </div>
        </div>
      )}

      {/* Stale State Banner */}
      {track?.is_stale && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-amber-300">Captions are outdated</h4>
              <p className="text-xs text-amber-300/80 mt-0.5">
                {track.stale_reasons && track.stale_reasons.length > 0
                  ? track.stale_reasons.join(' • ')
                  : 'Active script, narration audio, or production timeline has changed.'}
              </p>
            </div>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-500 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Regenerate Captions</span>
          </button>
        </div>
      )}

      {/* Empty State */}
      {!track && (
        <div className="rounded-2xl border border-dashed border-surface-border bg-surface/30 p-12 text-center space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
            <Subtitles className="h-7 w-7" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-base font-semibold text-white">No Caption Track Yet</h3>
            <p className="text-xs text-slate-400 mt-1">
              Generate synchronized, readability-split subtitle lines from your active Indonesian script and TTS narration audio.
            </p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-600 px-5 py-2.5 text-xs font-semibold text-white shadow-md shadow-cyan-600/20 hover:bg-cyan-500 transition-colors"
          >
            {generating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Generating Captions...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Generate Captions v1</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Track Workspace Content */}
      {track && (
        <div className="space-y-8">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Total Duration</span>
                <Clock className="h-4 w-4 text-cyan-400" />
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                {track.total_duration}s
              </p>
              <span className="text-[11px] text-slate-400">
                {formatSeconds(track.total_duration)} audio length
              </span>
            </div>

            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Caption Count</span>
                <Subtitles className="h-4 w-4 text-emerald-400" />
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                {track.total_segments}
              </p>
              <span className="text-[11px] text-slate-400">Subtitle lines</span>
            </div>

            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Scenes Covered</span>
                <Layers className="h-4 w-4 text-purple-400" />
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                {track.scenes_covered}
              </p>
              <span className="text-[11px] text-slate-400">Mapped scene shots</span>
            </div>

            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Avg Duration</span>
                <Clock className="h-4 w-4 text-amber-400" />
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                {track.average_caption_duration ? `${track.average_caption_duration}s` : 'N/A'}
              </p>
              <span className="text-[11px] text-slate-400">Per caption line</span>
            </div>

            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Track Version</span>
                <span className="rounded-full bg-cyan-500/10 px-2 py-0.5 text-[10px] font-semibold text-cyan-400 border border-cyan-500/20">
                  {track.is_active ? 'Active' : 'Draft'}
                </span>
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                v{track.version}
              </p>
              <span className="text-[11px] text-slate-400 uppercase">
                Lang: {track.language}
              </span>
            </div>
          </div>

          {/* Main 2-Column Split View: List (7 cols) | Phone Preview (5 cols) */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Caption Segments List */}
            <div className="lg:col-span-7 space-y-3">
              <div className="flex items-center justify-between pb-1">
                <h3 className="text-base font-semibold text-white">Timestamped Subtitle Segments</h3>
                <span className="text-xs text-slate-400">
                  {track.segments.length} segments • Target ~4 words
                </span>
              </div>

              <div className="space-y-3 max-h-[750px] overflow-y-auto pr-1">
                {track.segments.map((seg, idx) => {
                  const isSelected = selectedSegmentIndex === idx;
                  const isEditing = editingSegmentId === seg.id;

                  return (
                    <div
                      key={seg.id}
                      onClick={() => {
                        setSelectedSegmentIndex(idx);
                      }}
                      className={`rounded-xl border p-4 transition-all cursor-pointer ${
                        isSelected
                          ? 'border-cyan-500/80 bg-cyan-500/5 shadow-md shadow-cyan-500/5'
                          : 'border-surface-border bg-surface/60 hover:border-surface-border/80'
                      }`}
                    >
                      {/* Segment Top Bar */}
                      <div className="flex items-center justify-between pb-2 border-b border-surface-border/40">
                        <div className="flex items-center gap-2.5">
                          <span
                            className={`flex h-5 w-5 items-center justify-center rounded text-[11px] font-bold ${
                              isSelected
                                ? 'bg-cyan-600 text-white'
                                : 'bg-slate-800 text-slate-300'
                            }`}
                          >
                            #{seg.sequence}
                          </span>
                          <span className="text-xs font-mono font-semibold text-emerald-400">
                            {formatSeconds(seg.start_time)} → {formatSeconds(seg.end_time)}
                          </span>
                          <span className="text-[11px] text-slate-400">
                            ({seg.duration.toFixed(2)}s)
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          {seg.scene_sequence && (
                            <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300 font-medium">
                              Scene #{seg.scene_sequence}
                            </span>
                          )}
                          <span className="rounded bg-cyan-500/10 px-1.5 py-0.5 text-[10px] font-medium text-cyan-400 capitalize">
                            {seg.style}
                          </span>
                          <span className="rounded bg-purple-500/10 px-1.5 py-0.5 text-[10px] font-medium text-purple-400 capitalize">
                            {seg.position}
                          </span>

                          {!isEditing && (
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenEdit(seg);
                              }}
                              className="rounded p-1 text-slate-400 hover:text-white hover:bg-slate-800 transition-colors ml-1"
                            >
                              <Edit2 className="h-3 w-3" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Content / Edit Form */}
                      {isEditing ? (
                        <div
                          className="pt-3 space-y-3"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5">Caption Text</label>
                            <input
                              type="text"
                              value={editForm.text}
                              onChange={(e) =>
                                setEditForm((prev) => ({ ...prev, text: e.target.value }))
                              }
                              className="w-full rounded-lg border border-surface-border bg-slate-900 px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500"
                            />
                          </div>

                          <div className="grid grid-cols-4 gap-2">
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">Start (s)</label>
                              <input
                                type="number"
                                step="0.05"
                                min="0"
                                value={editForm.start}
                                onChange={(e) =>
                                  setEditForm((prev) => ({
                                    ...prev,
                                    start: parseFloat(e.target.value) || 0,
                                  }))
                                }
                                className="w-full rounded-lg border border-surface-border bg-slate-900 px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">End (s)</label>
                              <input
                                type="number"
                                step="0.05"
                                min="0"
                                value={editForm.end}
                                onChange={(e) =>
                                  setEditForm((prev) => ({
                                    ...prev,
                                    end: parseFloat(e.target.value) || 0,
                                  }))
                                }
                                className="w-full rounded-lg border border-surface-border bg-slate-900 px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-cyan-500"
                              />
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">Style</label>
                              <select
                                value={editForm.style}
                                onChange={(e) =>
                                  setEditForm((prev) => ({ ...prev, style: e.target.value }))
                                }
                                className="w-full rounded-lg border border-surface-border bg-slate-900 px-2 py-1 text-xs text-white focus:outline-none focus:border-cyan-500 capitalize"
                              >
                                <option value="default">Default</option>
                                <option value="bold">Bold</option>
                                <option value="highlight">Highlight</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-[10px] text-slate-400 block mb-0.5">Position</label>
                              <select
                                value={editForm.position}
                                onChange={(e) =>
                                  setEditForm((prev) => ({ ...prev, position: e.target.value }))
                                }
                                className="w-full rounded-lg border border-surface-border bg-slate-900 px-2 py-1 text-xs text-white focus:outline-none focus:border-cyan-500 capitalize"
                              >
                                <option value="bottom">Bottom</option>
                                <option value="center">Center</option>
                                <option value="top">Top</option>
                              </select>
                            </div>
                          </div>

                          {editForm.error && (
                            <p className="text-[10px] text-rose-400 font-medium">
                              {editForm.error}
                            </p>
                          )}

                          <div className="flex items-center justify-end gap-2 pt-1">
                            <button
                              onClick={() => setEditingSegmentId(null)}
                              className="rounded-lg px-2.5 py-1 text-xs font-medium text-slate-400 hover:text-white"
                            >
                              Cancel
                            </button>
                            <button
                              onClick={() => handleSaveSegment(seg.id)}
                              disabled={editForm.saving}
                              className="rounded-lg bg-cyan-600 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-500 disabled:opacity-50 transition-colors"
                            >
                              {editForm.saving ? 'Saving...' : 'Save Segment'}
                            </button>
                          </div>
                        </div>
                      ) : (
                        <p className="pt-2 text-sm text-slate-100 font-medium">
                          "{seg.text}"
                        </p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* 9:16 Shorts Visual Caption Preview */}
            <div className="lg:col-span-5 space-y-3 sticky top-6">
              <div className="flex items-center justify-between pb-1">
                <h3 className="text-base font-semibold text-white">9:16 Shorts Visual Preview</h3>
                <span className="text-xs text-slate-400">Position & Style Simulation</span>
              </div>

              {/* Phone Frame */}
              <div className="mx-auto w-full max-w-[320px] aspect-[9/16] rounded-3xl border-4 border-slate-700 bg-slate-950 p-4 shadow-2xl relative flex flex-col justify-between overflow-hidden">
                {/* Simulated Screen Content Background */}
                <div className="absolute inset-0 bg-gradient-to-b from-slate-900 via-slate-950 to-black z-0 opacity-80" />

                {/* Top Overlay / Header Indicator */}
                <div className="relative z-10 flex items-center justify-between text-slate-500 text-[10px]">
                  <span>Shorts Preview</span>
                  {activeSegment && (
                    <span className="font-mono">
                      #{activeSegment.sequence} of {track.segments.length}
                    </span>
                  )}
                </div>

                {/* Caption Placement based on position */}
                <div className="relative z-10 flex-1 flex flex-col justify-between py-6">
                  {/* Top Slot */}
                  <div className="flex justify-center">
                    {activeSegment?.position === 'top' && (
                      <CaptionPill segment={activeSegment} />
                    )}
                  </div>

                  {/* Center Slot */}
                  <div className="flex justify-center">
                    {activeSegment?.position === 'center' && (
                      <CaptionPill segment={activeSegment} />
                    )}
                  </div>

                  {/* Bottom Slot */}
                  <div className="flex justify-center">
                    {(activeSegment?.position === 'bottom' || !activeSegment?.position) && (
                      <CaptionPill segment={activeSegment} />
                    )}
                  </div>
                </div>

                {/* Phone Bottom Controls */}
                <div className="relative z-10 pt-3 border-t border-slate-800 flex items-center justify-between">
                  <button
                    onClick={() =>
                      setSelectedSegmentIndex((prev) => Math.max(0, prev - 1))
                    }
                    disabled={selectedSegmentIndex === 0}
                    className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30"
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </button>

                  <div className="text-center">
                    <p className="text-[11px] font-mono text-emerald-400">
                      {activeSegment ? `${formatSeconds(activeSegment.start_time)} → ${formatSeconds(activeSegment.end_time)}` : '00:00'}
                    </p>
                    <span className="text-[9px] text-slate-400 capitalize">
                      {activeSegment ? `${activeSegment.style} • ${activeSegment.position}` : ''}
                    </span>
                  </div>

                  <button
                    onClick={() =>
                      setSelectedSegmentIndex((prev) =>
                        Math.min(track.segments.length - 1, prev + 1)
                      )
                    }
                    disabled={selectedSegmentIndex >= track.segments.length - 1}
                    className="rounded-lg p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SRT Modal */}
      {srtModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-xl rounded-2xl border border-surface-border bg-surface p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div>
                <h3 className="text-base font-semibold text-white">SubRip (.SRT) Export</h3>
                <p className="text-xs text-slate-400">
                  Standard subtitle data ready for video rendering pipelines.
                </p>
              </div>
              <button
                onClick={() => setSrtModalOpen(false)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto">
              <pre className="rounded-xl border border-surface-border bg-slate-950 p-4 text-xs font-mono text-slate-200 whitespace-pre-wrap leading-relaxed">
                {srtContent}
              </pre>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-surface-border">
              <span className="text-xs text-slate-400">
                {track?.total_segments} caption lines
              </span>
              <div className="flex items-center gap-3">
                <button
                  onClick={handleCopySrt}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border bg-surface px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800 transition-colors"
                >
                  <Copy className="h-3.5 w-3.5" />
                  <span>{copyingSrt ? 'Copied!' : 'Copy to Clipboard'}</span>
                </button>

                {track && (
                  <a
                    href={getCaptionSrtDownloadUrl(track.id)}
                    download={`captions_${track.id}.srt`}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    <span>Download .SRT</span>
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CaptionPill({ segment }: { segment?: CaptionSegment }) {
  if (!segment) return null;

  if (segment.style === 'bold') {
    return (
      <div className="rounded-xl bg-black/85 px-3.5 py-1.5 text-center shadow-lg border border-white/20">
        <span className="text-sm font-black uppercase tracking-wide text-white drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
          {segment.text}
        </span>
      </div>
    );
  }

  if (segment.style === 'highlight') {
    return (
      <div className="rounded-xl bg-yellow-400 px-3.5 py-1.5 text-center shadow-lg border border-yellow-300">
        <span className="text-sm font-extrabold text-black tracking-tight">
          {segment.text}
        </span>
      </div>
    );
  }

  // Default
  return (
    <div className="rounded-xl bg-black/75 px-3 py-1.5 text-center shadow-md border border-white/10 max-w-[90%]">
      <span className="text-xs font-bold text-white drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]">
        {segment.text}
      </span>
    </div>
  );
}
