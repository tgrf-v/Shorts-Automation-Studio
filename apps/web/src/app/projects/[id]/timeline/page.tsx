'use client';

import React, { useEffect, useState, use, useCallback } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Clapperboard,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ChevronDown,
  Loader2,
  ExternalLink,
  Film,
  Scissors,
  Sparkles,
  Volume2,
  FileText,
  AlertCircle,
  Eye,
  Check,
  X,
  Sliders,
  Subtitles,
  Music,
} from 'lucide-react';
import { getProject } from '@/lib/api/projects';
import {
  generateProductionTimeline,
  getActiveProductionTimeline,
  getProductionTimelineVersions,
  getProductionTimeline,
  activateProductionTimeline,
  updateProductionTimelineItem,
} from '@/lib/api/timeline';
import { listSceneFootageCandidates } from '@/lib/api/footage';
import {
  Project,
  ProductionTimeline,
  ProductionTimelineSummary,
  ProductionTimelineItem,
  FootageCandidate,
} from '@/lib/api/types';

interface TimelinePageProps {
  params: Promise<{ id: string }>;
}

export default function ProductionTimelinePage({ params }: TimelinePageProps) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  const [project, setProject] = useState<Project | null>(null);
  const [timeline, setTimeline] = useState<ProductionTimeline | null>(null);
  const [versions, setVersions] = useState<ProductionTimelineSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Item Trim & Transition editing state: itemId -> { start, end, transition, notes, saving }
  const [itemEdits, setItemEdits] = useState<
    Record<
      string,
      {
        start: number;
        end: number;
        transition: string;
        notes: string;
        saving?: boolean;
        error?: string | null;
      }
    >
  >({});

  // Footage Replacement Modal state: { sceneId, itemId, candidates, loading }
  const [replacementModal, setReplacementModal] = useState<{
    sceneId: string;
    itemId: string;
    candidates: FootageCandidate[];
    loading: boolean;
  } | null>(null);

  // 1. Initial Load
  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [projData, versData] = await Promise.all([
        getProject(projectId),
        getProductionTimelineVersions(projectId).catch(() => []),
      ]);
      setProject(projData);
      setVersions(versData);

      const activeTl = await getActiveProductionTimeline(projectId);
      setTimeline(activeTl);

      // Initialize item edit inputs
      if (activeTl?.items) {
        const edits: typeof itemEdits = {};
        for (const it of activeTl.items) {
          edits[it.id] = {
            start: it.footage_start_time,
            end: it.footage_end_time,
            transition: it.transition || 'cut',
            notes: it.notes || '',
          };
        }
        setItemEdits(edits);
      }
    } catch (err) {
      console.error('Failed to load production timeline:', err);
      setError(err instanceof Error ? err.message : 'Failed to load production timeline.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 2. Generate New Timeline Version
  const handleGenerate = async () => {
    try {
      setGenerating(true);
      setError(null);
      setActionSuccess(null);

      const newTl = await generateProductionTimeline(projectId);
      setTimeline(newTl);

      // Refresh versions
      const vers = await getProductionTimelineVersions(projectId);
      setVersions(vers);

      // Reset edit inputs
      const edits: typeof itemEdits = {};
      for (const it of newTl.items) {
        edits[it.id] = {
          start: it.footage_start_time,
          end: it.footage_end_time,
          transition: it.transition || 'cut',
          notes: it.notes || '',
        };
      }
      setItemEdits(edits);

      setActionSuccess(`Production Timeline v${newTl.version} generated successfully!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate timeline.');
    } finally {
      setGenerating(false);
    }
  };

  // 3. Switch Version
  const handleSelectVersion = async (versionId: string) => {
    try {
      setLoading(true);
      const fullTl = await getProductionTimeline(versionId);
      setTimeline(fullTl);

      const edits: typeof itemEdits = {};
      for (const it of fullTl.items) {
        edits[it.id] = {
          start: it.footage_start_time,
          end: it.footage_end_time,
          transition: it.transition || 'cut',
          notes: it.notes || '',
        };
      }
      setItemEdits(edits);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load timeline version.');
    } finally {
      setLoading(false);
    }
  };

  // 4. Activate Version
  const handleActivate = async () => {
    if (!timeline) return;
    try {
      setLoading(true);
      const active = await activateProductionTimeline(timeline.id);
      setTimeline(active);
      const vers = await getProductionTimelineVersions(projectId);
      setVersions(vers);
      setActionSuccess(`Timeline v${timeline.version} is now active!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate timeline.');
    } finally {
      setLoading(false);
    }
  };

  // 5. Open Candidate Replacement Modal
  const handleOpenReplacement = async (sceneId: string, itemId: string) => {
    try {
      setReplacementModal({ sceneId, itemId, candidates: [], loading: true });
      const cands = await listSceneFootageCandidates(sceneId);
      setReplacementModal({ sceneId, itemId, candidates: cands, loading: false });
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to load footage candidates for scene.');
      setReplacementModal(null);
    }
  };

  // 6. Select Replacement Candidate
  const handleSelectReplacementCandidate = async (candidateId: string) => {
    if (!replacementModal) return;
    const { itemId } = replacementModal;
    try {
      const updatedTl = await updateProductionTimelineItem(itemId, {
        footage_candidate_id: candidateId,
      });
      setTimeline(updatedTl);

      // Update edit state
      const it = updatedTl.items.find((x) => x.id === itemId);
      if (it) {
        setItemEdits((prev) => ({
          ...prev,
          [itemId]: {
            ...prev[itemId],
            start: it.footage_start_time,
            end: it.footage_end_time,
          },
        }));
      }

      setReplacementModal(null);
      setActionSuccess('Footage candidate updated successfully!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to replace candidate footage.');
    }
  };

  // 7. Save Item Trim & Transition
  const handleSaveItemEdit = async (itemId: string) => {
    const edit = itemEdits[itemId];
    if (!edit) return;

    setItemEdits((prev) => ({
      ...prev,
      [itemId]: { ...prev[itemId], saving: true, error: null },
    }));

    try {
      const updatedTl = await updateProductionTimelineItem(itemId, {
        footage_start_time: Number(edit.start),
        footage_end_time: Number(edit.end),
        transition: edit.transition,
        notes: edit.notes,
      });
      setTimeline(updatedTl);

      setItemEdits((prev) => ({
        ...prev,
        [itemId]: { ...prev[itemId], saving: false, error: null },
      }));
      setActionSuccess('Item trim and transition saved.');
    } catch (err) {
      setItemEdits((prev) => ({
        ...prev,
        [itemId]: {
          ...prev[itemId],
          saving: false,
          error: err instanceof Error ? err.message : 'Failed to update item.',
        },
      }));
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = (sec % 60).toFixed(2);
    return `${m.toString().padStart(2, '0')}:${parseFloat(s) < 10 ? '0' : ''}${s}`;
  };

  if (loading && !project) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center p-8">
        <div className="flex flex-col items-center space-y-3 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
          <span className="text-sm">Loading Production Timeline workspace...</span>
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
                Production Timeline
              </h1>
              <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs text-emerald-400">
                Milestone 7
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Project: <span className="text-slate-200 font-medium">{project?.name}</span> • Shot plan linking script, narration audio & footage
            </p>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Version Switcher */}
          {versions.length > 0 && (
            <div className="relative">
              <select
                value={timeline?.id || ''}
                onChange={(e) => handleSelectVersion(e.target.value)}
                className="appearance-none rounded-xl border border-surface-border bg-surface pl-3 pr-8 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 cursor-pointer focus:outline-none"
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    Timeline v{v.version} {v.is_active ? '(Active)' : ''} — {v.scenes_with_footage}/{v.total_scenes} footage
                  </option>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-400" />
            </div>
          )}

          {/* Activate Button */}
          {timeline && !timeline.is_active && (
            <button
              onClick={handleActivate}
              className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 transition-colors"
            >
              <Check className="h-3.5 w-3.5" />
              <span>Set as Active</span>
            </button>
          )}

          {/* Generate / Regenerate Button */}
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-emerald-600/20 hover:bg-emerald-500 disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Generating Timeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" />
                <span>{timeline ? 'Regenerate Timeline' : 'Generate Timeline'}</span>
              </>
            )}
          </button>

          <Link
            href={`/projects/${projectId}/captions`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors"
          >
            <Subtitles className="h-3.5 w-3.5" />
            <span>Captions (M8)</span>
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
      {timeline?.is_stale && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-amber-300">Timeline is outdated</h4>
              <p className="text-xs text-amber-300/80 mt-0.5">
                {timeline.stale_reasons && timeline.stale_reasons.length > 0
                  ? timeline.stale_reasons.join(' • ')
                  : 'Active script, narration audio, or footage selections have changed.'}
              </p>
            </div>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="shrink-0 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-500 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Regenerate Timeline</span>
          </button>
        </div>
      )}

      {/* Empty State */}
      {!timeline && (
        <div className="rounded-2xl border border-dashed border-surface-border bg-surface/30 p-12 text-center space-y-4">
          <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Clapperboard className="h-7 w-7" />
          </div>
          <div className="max-w-md mx-auto">
            <h3 className="text-base font-semibold text-white">No Production Timeline Yet</h3>
            <p className="text-xs text-slate-400 mt-1">
              Connect your Reference Scenes, Indonesian Script (M4), TTS Narration Audio (M5), and Selected Footage (M6) into a production shot plan.
            </p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-xs font-semibold text-white shadow-md shadow-emerald-600/20 hover:bg-emerald-500 transition-colors"
          >
            {generating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Generating Timeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-4 w-4" />
                <span>Generate Production Timeline v1</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Timeline Workspace Content */}
      {timeline && (
        <div className="space-y-8">
          {/* Summary Metric Cards */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-5">
            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Total Duration</span>
                <Clock className="h-4 w-4 text-emerald-400" />
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                {timeline.duration}s
              </p>
              <span className="text-[11px] text-slate-400">
                {formatSeconds(timeline.duration)} total length
              </span>
            </div>

            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Scenes</span>
                <Layers className="h-4 w-4 text-blue-400" />
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                {timeline.total_scenes}
              </p>
              <span className="text-[11px] text-slate-400">Shot sequence blocks</span>
            </div>

            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Footage Coverage</span>
                <Film className="h-4 w-4 text-amber-400" />
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                {timeline.scenes_with_footage} / {timeline.total_scenes}
              </p>
              <span className="text-[11px] text-slate-400">
                {timeline.scenes_missing_footage > 0 ? (
                  <span className="text-rose-400 font-medium">{timeline.scenes_missing_footage} missing</span>
                ) : (
                  <span className="text-emerald-400 font-medium">100% covered</span>
                )}
              </span>
            </div>

            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Avg Similarity</span>
                <Sparkles className="h-4 w-4 text-purple-400" />
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                {timeline.average_similarity !== null && timeline.average_similarity !== undefined
                  ? `${Math.round(timeline.average_similarity * 100)}%`
                  : 'N/A'}
              </p>
              <span className="text-[11px] text-slate-400">Visual match score</span>
            </div>

            <div className="rounded-xl border border-surface-border bg-surface p-4">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-xs font-medium">Version</span>
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400 border border-emerald-500/20">
                  {timeline.is_active ? 'Active' : 'Draft'}
                </span>
              </div>
              <p className="mt-2 text-2xl font-bold tracking-tight text-white">
                v{timeline.version}
              </p>
              <span className="text-[11px] text-slate-400 capitalize">
                Status: {timeline.status}
              </span>
            </div>
          </div>

          {/* Shot Plan Cards */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white">Production Shot Plan</h3>
                <p className="text-xs text-slate-400">
                  Exact timings from TTS narration with linked footage, trim offsets, and transitions.
                </p>
              </div>
              <span className="text-xs text-slate-400">
                {timeline.items.length} shots planned
              </span>
            </div>

            <div className="space-y-4">
              {timeline.items.map((item) => {
                const edit = itemEdits[item.id] || {
                  start: item.footage_start_time,
                  end: item.footage_end_time,
                  transition: item.transition,
                  notes: item.notes || '',
                };
                const cand = item.candidate;
                const scene = item.scene;

                return (
                  <div
                    key={item.id}
                    className="rounded-2xl border border-surface-border bg-surface/60 p-5 space-y-4 hover:border-surface-border/80 transition-all"
                  >
                    {/* Item Top Bar */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-surface-border/50 pb-3">
                      <div className="flex items-center gap-3">
                        <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-slate-800 text-xs font-bold text-white">
                          #{item.sequence}
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-semibold text-emerald-400">
                            {formatSeconds(item.start_time)} → {formatSeconds(item.end_time)}
                          </span>
                          <span className="text-xs text-slate-400">
                            ({item.duration.toFixed(2)}s narration)
                          </span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 flex-wrap">
                        {/* Status Badges */}
                        {!item.footage_candidate_id ? (
                          <span className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-2.5 py-1 text-[11px] font-semibold text-rose-400 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            <span>Missing Footage</span>
                          </span>
                        ) : item.insufficient_footage_duration ? (
                          <span className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-[11px] font-semibold text-amber-400 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            <span>Footage shorter than narration</span>
                          </span>
                        ) : item.duration_unknown ? (
                          <span className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-2.5 py-1 text-[11px] font-semibold text-blue-400">
                            Duration Unknown
                          </span>
                        ) : (
                          <span className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[11px] font-semibold text-emerald-400 flex items-center gap-1">
                            <Check className="h-3 w-3" />
                            <span>Footage Assigned</span>
                          </span>
                        )}

                        <span className="rounded-lg border border-surface-border bg-slate-800/80 px-2.5 py-1 text-[11px] text-slate-300 capitalize">
                          Transition: {item.transition}
                        </span>
                      </div>
                    </div>

                    {/* Main Content Grid: Preview | Narration | Controls */}
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
                      {/* Visual Previews (4 cols) */}
                      <div className="lg:col-span-4 grid grid-cols-2 gap-3">
                        {/* Reference Keyframe */}
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                            Reference Keyframe
                          </span>
                          <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-slate-900 border border-surface-border">
                            {scene?.primary_keyframe_url ? (
                              <img
                                src={scene.primary_keyframe_url}
                                alt={`Scene #${item.sequence}`}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <div className="flex h-full w-full items-center justify-center text-slate-600 text-[10px]">
                                No Keyframe
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Candidate Thumbnail */}
                        <div className="space-y-1.5">
                          <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">
                            Selected Footage
                          </span>
                          <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-slate-900 border border-surface-border">
                            {cand?.thumbnail_url ? (
                              <img
                                src={cand.thumbnail_url}
                                alt={cand.title}
                                className="h-full w-full object-cover"
                              />
                            ) : (
                              <div className="flex flex-col h-full w-full items-center justify-center text-slate-500 text-[10px] p-2 text-center">
                                <Film className="h-5 w-5 mb-1 text-slate-600" />
                                <span>No Footage</span>
                              </div>
                            )}
                            {cand?.duration && (
                              <span className="absolute bottom-1 right-1 rounded bg-black/80 px-1 py-0.5 text-[9px] font-mono text-white">
                                {cand.duration.toFixed(1)}s
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Narration & Footage Metadata (5 cols) */}
                      <div className="lg:col-span-5 space-y-3">
                        {/* Narration script text */}
                        <div className="rounded-xl border border-surface-border/60 bg-slate-900/50 p-3 space-y-1">
                          <span className="text-[10px] font-semibold text-blue-400 uppercase tracking-wider flex items-center gap-1">
                            <Volume2 className="h-3 w-3" />
                            <span>Indonesian Narration</span>
                          </span>
                          <p className="text-xs text-slate-200 leading-relaxed">
                            "{item.script_text}"
                          </p>
                        </div>

                        {/* Selected Candidate Info */}
                        {cand ? (
                          <div className="space-y-1.5">
                            <div className="flex items-start justify-between gap-2">
                              <h5 className="text-xs font-semibold text-white line-clamp-1">
                                {cand.title}
                              </h5>
                              <span className="shrink-0 rounded bg-blue-500/10 px-1.5 py-0.5 text-[10px] font-medium text-blue-400 border border-blue-500/20 capitalize">
                                {cand.source_platform}
                              </span>
                            </div>

                            <div className="flex items-center gap-3 text-[11px] text-slate-400">
                              <span className="text-emerald-400 font-medium">
                                {Math.round(cand.final_score * 100)}% Match
                              </span>
                              <span>•</span>
                              <span className="text-slate-300">{cand.match_type}</span>
                              {cand.source_url && (
                                <>
                                  <span>•</span>
                                  <a
                                    href={cand.source_url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300"
                                  >
                                    <span>Source</span>
                                    <ExternalLink className="h-2.5 w-2.5" />
                                  </a>
                                </>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div className="flex items-center justify-between gap-2 p-2 rounded-xl bg-rose-500/5 border border-rose-500/20">
                            <p className="text-xs text-rose-300">
                              No footage selected for this scene yet.
                            </p>
                            <Link
                              href={`/projects/${projectId}/footage`}
                              className="inline-flex items-center gap-1 rounded-lg bg-rose-600 px-2.5 py-1 text-[11px] font-semibold text-white hover:bg-rose-500 transition-colors shrink-0"
                            >
                              <span>Search Footage</span>
                            </Link>
                          </div>
                        )}

                        {/* Change Footage Button */}
                        <div>
                          <button
                            onClick={() => handleOpenReplacement(item.scene_id, item.id)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border bg-slate-800/80 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                          >
                            <Film className="h-3 w-3 text-amber-400" />
                            <span>{cand ? 'Change Footage' : 'Select Candidate'}</span>
                          </button>
                        </div>
                      </div>

                      {/* Trim & Transition Inline Controls (3 cols) */}
                      <div className="lg:col-span-3 rounded-xl border border-surface-border/80 bg-slate-900/60 p-3 space-y-3">
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1">
                            <Scissors className="h-3 w-3 text-emerald-400" />
                            <span>Manual Trim & Cut</span>
                          </span>
                          {edit.saving && <Loader2 className="h-3 w-3 animate-spin text-emerald-400" />}
                        </div>

                        {/* Footage Start & End */}
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5">Start (s)</label>
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={edit.start}
                              onChange={(e) =>
                                setItemEdits((prev) => ({
                                  ...prev,
                                  [item.id]: { ...prev[item.id], start: parseFloat(e.target.value) || 0 },
                                }))
                              }
                              className="w-full rounded-lg border border-surface-border bg-surface px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] text-slate-400 block mb-0.5">End (s)</label>
                            <input
                              type="number"
                              step="0.1"
                              min="0"
                              value={edit.end}
                              onChange={(e) =>
                                setItemEdits((prev) => ({
                                  ...prev,
                                  [item.id]: { ...prev[item.id], end: parseFloat(e.target.value) || 0 },
                                }))
                              }
                              className="w-full rounded-lg border border-surface-border bg-surface px-2 py-1 text-xs text-white font-mono focus:outline-none focus:border-emerald-500"
                            />
                          </div>
                        </div>

                        {/* Transition */}
                        <div>
                          <label className="text-[10px] text-slate-400 block mb-0.5">Transition</label>
                          <select
                            value={edit.transition}
                            onChange={(e) =>
                              setItemEdits((prev) => ({
                                ...prev,
                                [item.id]: { ...prev[item.id], transition: e.target.value },
                              }))
                            }
                            className="w-full rounded-lg border border-surface-border bg-surface px-2 py-1 text-xs text-white capitalize focus:outline-none focus:border-emerald-500"
                          >
                            <option value="cut">Cut</option>
                            <option value="fade">Fade</option>
                          </select>
                        </div>

                        {/* Notes */}
                        <div>
                          <label className="text-[10px] text-slate-400 block mb-0.5">Notes</label>
                          <input
                            type="text"
                            placeholder="Optional notes..."
                            value={edit.notes}
                            onChange={(e) =>
                              setItemEdits((prev) => ({
                                ...prev,
                                [item.id]: { ...prev[item.id], notes: e.target.value },
                              }))
                            }
                            className="w-full rounded-lg border border-surface-border bg-surface px-2 py-1 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                          />
                        </div>

                        {edit.error && (
                          <p className="text-[10px] text-rose-400 font-medium">{edit.error}</p>
                        )}

                        <button
                          onClick={() => handleSaveItemEdit(item.id)}
                          disabled={edit.saving}
                          className="w-full rounded-lg bg-emerald-600/90 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 transition-colors disabled:opacity-50"
                        >
                          {edit.saving ? 'Saving...' : 'Save Trim & Cut'}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Candidate Replacement Modal */}
      {replacementModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-2xl rounded-2xl border border-surface-border bg-surface p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-surface-border pb-3">
              <div>
                <h3 className="text-base font-semibold text-white">Select Candidate Footage</h3>
                <p className="text-xs text-slate-400">
                  Pick from candidates discovered in Milestone 6 for this scene.
                </p>
              </div>
              <button
                onClick={() => setReplacementModal(null)}
                className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {replacementModal.loading ? (
                <div className="py-12 text-center text-slate-400 flex flex-col items-center gap-2">
                  <Loader2 className="h-6 w-6 animate-spin text-emerald-500" />
                  <span className="text-xs">Loading candidate pool...</span>
                </div>
              ) : replacementModal.candidates.length === 0 ? (
                <div className="py-8 text-center text-slate-400 space-y-3">
                  <p className="text-xs">No candidate footage found for this scene.</p>
                  <Link
                    href={`/projects/${projectId}/footage`}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-amber-500"
                  >
                    <Film className="h-3.5 w-3.5" />
                    <span>Go to Visual Footage Search (M6)</span>
                  </Link>
                </div>
              ) : (
                replacementModal.candidates.map((cand) => (
                  <div
                    key={cand.id}
                    className="flex items-center justify-between gap-4 p-3 rounded-xl border border-surface-border bg-slate-900/50 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="relative aspect-video w-20 shrink-0 overflow-hidden rounded-lg bg-black border border-surface-border">
                        {cand.thumbnail_url ? (
                          <img src={cand.thumbnail_url} alt={cand.title} className="h-full w-full object-cover" />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-[10px] text-slate-500">
                            No Thumb
                          </div>
                        )}
                      </div>
                      <div className="min-w-0 space-y-0.5">
                        <h5 className="text-xs font-semibold text-white truncate">{cand.title}</h5>
                        <p className="text-[11px] text-slate-400">
                          {cand.source_platform} • {cand.duration ? `${cand.duration.toFixed(1)}s` : 'Unknown'} •{' '}
                          <span className="text-emerald-400 font-medium">
                            {Math.round(cand.final_score * 100)}% score
                          </span>
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => handleSelectReplacementCandidate(cand.id)}
                      className="shrink-0 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-500 transition-colors"
                    >
                      Select
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
