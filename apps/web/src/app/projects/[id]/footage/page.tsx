'use client';

import React, { useEffect, useState, use, useCallback } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Search,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  Layers,
  Loader2,
  RefreshCw,
  Film,
  Check,
  Globe,
  Sliders,
  Play,
  FileText,
  Volume2,
  Clapperboard,
  Copy,
  Download,
  Upload,
  Link2,
  Plus,
  Compass,
} from 'lucide-react';
import { getProject } from '@/lib/api/projects';
import { getProjectAnalysis } from '@/lib/api/analysis';
import { getKeyframeImageUrl } from '@/lib/api/client';
import {
  searchFootageForScene,
  getFootageSearch,
  listSceneFootageCandidates,
  selectFootageCandidate,
  selectCandidateForRange,
  uploadCustomFootage,
  getSceneFootageSelection,
  getProjectFootageSummary,
} from '@/lib/api/footage';
import {
  Project,
  Scene,
  FootageSearch,
  FootageCandidate,
  SceneFootageSummaryItem,
  SceneFootageSelection,
} from '@/lib/api/types';

interface FootagePageProps {
  params: Promise<{ id: string }>;
}

export default function VisualFootageSearchPage({ params }: FootagePageProps) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  // Core Data
  const [project, setProject] = useState<Project | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [summaryItems, setSummaryItems] = useState<SceneFootageSummaryItem[]>([]);
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null);

  // Candidates & Search State
  const [candidates, setCandidates] = useState<FootageCandidate[]>([]);
  const [activeSelection, setActiveSelection] = useState<SceneFootageSelection | null>(null);
  const [activeSearch, setActiveSearch] = useState<FootageSearch | null>(null);

  // Discovery Mode: 'search' | 'custom'
  const [activeTab, setActiveTab] = useState<'search' | 'custom'>('search');

  // Custom Footage State
  const [customFile, setCustomFile] = useState<File | null>(null);
  const [customUrl, setCustomUrl] = useState<string>('');
  const [customTitle, setCustomTitle] = useState<string>('');
  const [customRangeEnabled, setCustomRangeEnabled] = useState<boolean>(false);
  const [customEndSeq, setCustomEndSeq] = useState<number>(1);
  const [uploadingCustom, setUploadingCustom] = useState<boolean>(false);

  // Candidate Card Range Selection Popover
  const [rangeCandidateId, setRangeCandidateId] = useState<string | null>(null);
  const [rangeEndSeq, setRangeEndSeq] = useState<number>(1);
  const [applyingRange, setApplyingRange] = useState<boolean>(false);

  // Form State
  const [searchProvider, setSearchProvider] = useState<string>('youtube');
  const [customQuery, setCustomQuery] = useState<string>('');
  const [platformFilter, setPlatformFilter] = useState<string>('all');

  // UI States
  const [loading, setLoading] = useState<boolean>(true);
  const [searching, setSearching] = useState<boolean>(false);
  const [selectingId, setSelectingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // 1. Initial Load
  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [projData, analysisData, summaryData] = await Promise.all([
        getProject(projectId),
        getProjectAnalysis(projectId),
        getProjectFootageSummary(projectId),
      ]);

      setProject(projData);
      const sceneList = analysisData.scenes || [];
      setScenes(sceneList);
      setSummaryItems(summaryData);

      if (sceneList.length > 0 && !selectedScene) {
        setSelectedScene(sceneList[0]);
      }
    } catch (err) {
      console.error('Failed to load visual footage workspace:', err);
      setError(err instanceof Error ? err.message : 'Failed to load visual footage workspace.');
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedScene]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 2. Load candidates when selectedScene changes
  const loadSceneCandidates = useCallback(async (sceneId: string) => {
    try {
      const [candList, sel] = await Promise.all([
        listSceneFootageCandidates(sceneId),
        getSceneFootageSelection(sceneId),
      ]);
      setCandidates(candList);
      setActiveSelection(sel);
    } catch (err) {
      console.error('Failed to load scene candidates:', err);
    }
  }, []);

  useEffect(() => {
    if (selectedScene) {
      loadSceneCandidates(selectedScene.id);
      setCustomQuery('');
      setCustomEndSeq(Math.min(selectedScene.sequence + 4, scenes.length || selectedScene.sequence));
      setRangeEndSeq(Math.min(selectedScene.sequence + 4, scenes.length || selectedScene.sequence));
    }
  }, [selectedScene, scenes.length, loadSceneCandidates]);

  // 3. Search Job Polling Loop
  useEffect(() => {
    if (!activeSearch || activeSearch.status === 'completed' || activeSearch.status === 'failed') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await getFootageSearch(activeSearch.search_id);
        setActiveSearch(updated);

        if (updated.status === 'completed') {
          setSearching(false);
          setSuccessMsg(`Discovered ${updated.total_results} candidate footage videos!`);
          if (selectedScene) {
            await loadSceneCandidates(selectedScene.id);
            const summary = await getProjectFootageSummary(projectId);
            setSummaryItems(summary);
          }
          setTimeout(() => setSuccessMsg(null), 5000);
        } else if (updated.status === 'failed') {
          setSearching(false);
          setError(updated.error || 'Footage search failed.');
        }
      } catch (err) {
        console.error('Search polling error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeSearch, selectedScene, projectId, loadSceneCandidates]);

  // Handler: Trigger Footage Search
  const handleSearch = async () => {
    if (!selectedScene) return;

    setSearching(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const searchRes = await searchFootageForScene(selectedScene.id, {
        query: customQuery.trim() || undefined,
        provider: searchProvider,
        max_results: 20,
      });
      setActiveSearch(searchRes);
    } catch (err) {
      setSearching(false);
      setError(err instanceof Error ? err.message : 'Failed to start footage search.');
    }
  };

  // Handler: Select Candidate
  const handleSelectCandidate = async (candidateId: string) => {
    setSelectingId(candidateId);
    try {
      const sel = await selectFootageCandidate(candidateId);
      setActiveSelection(sel);
      setSuccessMsg('Candidate footage selected for this scene!');
      if (selectedScene) {
        await loadSceneCandidates(selectedScene.id);
        const summary = await getProjectFootageSummary(projectId);
        setSummaryItems(summary);
      }
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to select candidate footage.');
    } finally {
      setSelectingId(null);
    }
  };

  // Handler: Copy Keyframe to Clipboard (for Google Lens)
  const handleCopyKeyframe = async (keyframeId: string) => {
    try {
      const url = getKeyframeImageUrl(keyframeId);
      const res = await fetch(url);
      const blob = await res.blob();
      await navigator.clipboard.write([
        new ClipboardItem({ [blob.type]: blob })
      ]);
      setSuccessMsg("Keyframe copied to clipboard! Open Google Lens (lens.google.com) and press Ctrl+V to reverse-search TikTok/Instagram.");
      setTimeout(() => setSuccessMsg(null), 6000);
    } catch {
      await navigator.clipboard.writeText(getKeyframeImageUrl(keyframeId));
      setSuccessMsg("Keyframe image URL copied! You can paste it into reverse image search.");
      setTimeout(() => setSuccessMsg(null), 4000);
    }
  };

  // Handler: Upload Custom Footage or submit TikTok / Instagram Link
  const handleCustomFootageSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedScene) return;
    if (!customFile && !customUrl.trim()) {
      setError("Please choose a video file (.mp4/.mov) to upload or paste a video URL (TikTok/IG).");
      return;
    }

    setUploadingCustom(true);
    setError(null);
    setSuccessMsg(null);

    try {
      const formData = new FormData();
      if (customFile) {
        formData.append("file", customFile);
      }
      if (customUrl.trim()) {
        formData.append("video_url", customUrl.trim());
      }
      if (customTitle.trim()) {
        formData.append("title", customTitle.trim());
      }
      if (customRangeEnabled && customEndSeq > selectedScene.sequence) {
        formData.append("start_sequence", String(selectedScene.sequence));
        formData.append("end_sequence", String(customEndSeq));
      }

      await uploadCustomFootage(selectedScene.id, formData);
      setCustomFile(null);
      setCustomUrl('');
      setCustomTitle('');
      setSuccessMsg(
        customRangeEnabled && customEndSeq > selectedScene.sequence
          ? `Custom footage assigned continuously across Scenes #${selectedScene.sequence} to #${customEndSeq}!`
          : `Custom footage attached to Scene #${selectedScene.sequence}!`
      );

      await loadSceneCandidates(selectedScene.id);
      const summary = await getProjectFootageSummary(projectId);
      setSummaryItems(summary);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to upload or process custom footage.");
    } finally {
      setUploadingCustom(false);
    }
  };

  // Handler: Assign candidate footage to a continuous range of scenes
  const handleRangeSelect = async (candidateId: string, endSeq: number) => {
    if (!selectedScene) return;
    setApplyingRange(true);
    setError(null);
    try {
      await selectCandidateForRange(candidateId, selectedScene.sequence, endSeq, projectId);
      setSuccessMsg(`Footage assigned continuously across Scenes #${selectedScene.sequence} to #${endSeq}!`);
      setRangeCandidateId(null);
      await loadSceneCandidates(selectedScene.id);
      const summary = await getProjectFootageSummary(projectId);
      setSummaryItems(summary);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign footage to range.");
    } finally {
      setApplyingRange(false);
    }
  };

  // Filter candidates by platform
  const filteredCandidates = candidates.filter((c) => {
    if (platformFilter === 'all') return true;
    return c.source_platform.toLowerCase() === platformFilter.toLowerCase();
  });

  const selectedCount = summaryItems.filter((s) => s.has_selection).length;
  const totalScenes = scenes.length;

  if (loading && !project) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center p-8">
        <div className="flex flex-col items-center space-y-3 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin text-amber-500" />
          <span className="text-sm">Loading Visual Footage Search workspace...</span>
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
                Visual Footage Discovery
              </h1>
              <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 text-xs text-amber-400">
                Milestone 6
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Project: <span className="text-slate-200 font-medium">{project?.name}</span> • Match internet footage to reference scenes
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}/tts`}
            className="inline-flex items-center gap-2 rounded-xl border border-surface-border bg-surface px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <Volume2 className="h-3.5 w-3.5 text-purple-400" />
            <span>TTS Narration</span>
          </Link>

          <Link
            href={`/projects/${projectId}/timeline`}
            className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20 hover:text-emerald-200 transition-colors"
          >
            <Clapperboard className="h-3.5 w-3.5 text-emerald-400" />
            <span>Timeline (M7)</span>
          </Link>

          <button
            onClick={fetchData}
            className="inline-flex items-center gap-2 rounded-xl border border-surface-border bg-surface px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Overview Progress Banner */}
      <div className="rounded-2xl border border-surface-border bg-surface p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <Film className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Footage Selection Progress</h3>
            <p className="text-xs text-slate-400">
              {selectedCount} of {totalScenes} scenes currently have selected candidate footage
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 w-full sm:w-64">
          <div className="h-2.5 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
            <div
              className="h-full bg-gradient-to-r from-amber-500 to-emerald-500 rounded-full transition-all duration-300"
              style={{ width: `${totalScenes > 0 ? (selectedCount / totalScenes) * 100 : 0}%` }}
            />
          </div>
          <span className="text-xs font-bold text-white font-mono shrink-0">
            {totalScenes > 0 ? Math.round((selectedCount / totalScenes) * 100) : 0}%
          </span>
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

      {successMsg && (
        <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 flex items-start gap-3 text-emerald-400">
          <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-medium">Success</p>
            <p className="text-xs text-emerald-300/80 mt-0.5">{successMsg}</p>
          </div>
        </div>
      )}

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Scene Selector (4 cols) */}
        <div className="lg:col-span-4 rounded-2xl border border-surface-border bg-surface p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-surface-border/50">
            <h2 className="text-sm font-semibold text-white flex items-center gap-2">
              <Layers className="h-4 w-4 text-amber-400" />
              <span>Reference Scenes ({scenes.length})</span>
            </h2>
          </div>

          <div className="space-y-3 max-h-[75vh] overflow-y-auto pr-1">
            {scenes.map((sc) => {
              const isSelected = selectedScene?.id === sc.id;
              const summaryItem = summaryItems.find((s) => s.scene_id === sc.id);
              const hasSelection = summaryItem?.has_selection;

              return (
                <div
                  key={sc.id}
                  onClick={() => setSelectedScene(sc)}
                  className={`rounded-xl p-3.5 border transition-all cursor-pointer ${
                    isSelected
                      ? 'border-amber-500 bg-amber-500/10 shadow-lg shadow-amber-500/10'
                      : 'border-surface-border bg-slate-900/40 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between text-xs pb-1.5 border-b border-surface-border/30">
                    <div className="flex items-center gap-2 font-semibold text-white">
                      <span className="flex h-5 w-5 items-center justify-center rounded-md bg-amber-500/20 text-amber-300 text-[11px]">
                        {sc.sequence}
                      </span>
                      <span>Scene #{sc.sequence}</span>
                    </div>

                    <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
                      <span>{sc.start_time.toFixed(1)}s - {sc.end_time.toFixed(1)}s</span>
                      {hasSelection ? (
                        <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-400">
                          <Check className="h-3 w-3" />
                          <span>Matched</span>
                        </span>
                      ) : (
                        <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                          {summaryItem?.total_candidates || 0} candidates
                        </span>
                      )}
                    </div>
                  </div>

                  <p className="mt-2 text-xs text-slate-300 line-clamp-2 italic leading-relaxed">
                    {sc.description || 'No visual description available.'}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Search & Candidate Results (8 cols) */}
        <div className="lg:col-span-8 space-y-6">
          {/* 1. Google Lens & Selected Scene Keyframe Preview */}
          {selectedScene && (
            <div className="rounded-2xl border border-surface-border bg-surface p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
              <div className="flex items-center gap-4 min-w-0">
                {selectedScene.keyframes && selectedScene.keyframes.length > 0 ? (
                  <div className="relative h-16 w-28 shrink-0 rounded-xl overflow-hidden border border-slate-700 bg-slate-900 shadow-md">
                    <img
                      src={getKeyframeImageUrl(selectedScene.keyframes[0].id)}
                      alt={`Scene ${selectedScene.sequence} keyframe`}
                      className="h-full w-full object-cover"
                    />
                    <span className="absolute bottom-1 right-1 rounded bg-black/80 px-1 text-[9px] font-mono text-white">
                      {selectedScene.keyframes[0].timestamp.toFixed(1)}s
                    </span>
                  </div>
                ) : (
                  <div className="h-16 w-28 shrink-0 rounded-xl border border-slate-800 bg-slate-900 flex items-center justify-center text-slate-500">
                    <Film className="h-6 w-6" />
                  </div>
                )}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <h4 className="text-sm font-semibold text-white">Scene #{selectedScene.sequence} Keyframe</h4>
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-[10px] font-mono text-slate-300">
                      {selectedScene.duration.toFixed(1)}s
                    </span>
                  </div>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-1">
                    {selectedScene.description || 'Reference scene visual cut'}
                  </p>
                </div>
              </div>

              {/* Google Lens & Image Reverse Search Actions */}
              {selectedScene.keyframes && selectedScene.keyframes.length > 0 && (
                <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                  <button
                    type="button"
                    onClick={() => handleCopyKeyframe(selectedScene.keyframes[0].id)}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-surface-border bg-slate-900 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 hover:text-white transition-colors"
                    title="Copy keyframe image to clipboard for Google Lens (Ctrl+V)"
                  >
                    <Copy className="h-3.5 w-3.5 text-blue-400" />
                    <span>Copy Keyframe</span>
                  </button>

                  <a
                    href="https://lens.google.com"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-xl border border-blue-500/30 bg-blue-500/10 px-3 py-2 text-xs font-semibold text-blue-400 hover:bg-blue-500 hover:text-white transition-all shadow-sm"
                    title="Open Google Lens in a new tab"
                  >
                    <Compass className="h-3.5 w-3.5" />
                    <span>Open Google Lens</span>
                    <ExternalLink className="h-3 w-3 opacity-70" />
                  </a>

                  <a
                    href={getKeyframeImageUrl(selectedScene.keyframes[0].id)}
                    download={`scene_${selectedScene.sequence}_keyframe.jpg`}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-surface-border bg-slate-900 px-2.5 py-2 text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                    title="Download Keyframe JPG"
                  >
                    <Download className="h-3.5 w-3.5" />
                  </a>
                </div>
              )}
            </div>
          )}

          {/* 2. Mode Switcher Tabs */}
          <div className="flex items-center gap-2 border-b border-surface-border pb-3">
            <button
              onClick={() => setActiveTab('search')}
              className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${
                activeTab === 'search'
                  ? 'bg-amber-600 text-white shadow-md shadow-amber-600/20'
                  : 'border border-surface-border bg-surface text-slate-400 hover:text-white'
              }`}
            >
              <Search className="h-3.5 w-3.5" />
              <span>Search Web / YouTube</span>
            </button>

            <button
              onClick={() => setActiveTab('custom')}
              className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-xs font-semibold transition-all ${
                activeTab === 'custom'
                  ? 'bg-amber-600 text-white shadow-md shadow-amber-600/20'
                  : 'border border-surface-border bg-surface text-slate-400 hover:text-white'
              }`}
            >
              <Upload className="h-3.5 w-3.5" />
              <span>Upload Video / Paste Link (TikTok & IG)</span>
              <span className="rounded bg-amber-500/20 text-amber-300 text-[10px] px-1.5 py-0.5 ml-0.5 font-normal">
                Direct
              </span>
            </button>
          </div>

          {/* 3A. Tab 1: Auto Search Controls */}
          {activeTab === 'search' && selectedScene && (
            <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-surface-border/50">
                <div>
                  <h3 className="text-base font-semibold text-white flex items-center gap-2">
                    <span>Scene #{selectedScene.sequence} Footage Discovery</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Target duration: <span className="text-slate-200">{selectedScene.duration.toFixed(1)}s</span> • {selectedScene.description ? selectedScene.description.slice(0, 70) + '...' : ''}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <select
                    value={searchProvider}
                    onChange={(e) => setSearchProvider(e.target.value)}
                    disabled={searching}
                    className="rounded-xl border border-surface-border bg-slate-900 px-3 py-2 text-xs text-white focus:outline-none focus:border-amber-500"
                  >
                    <option value="youtube">YouTube Video Search</option>
                    <option value="web">Web Video Search</option>
                    <option value="mock">Mock Search (Offline / Dev)</option>
                  </select>
                </div>
              </div>

              {/* Query Input & Search Button */}
              <div className="flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    value={customQuery}
                    onChange={(e) => setCustomQuery(e.target.value)}
                    placeholder="Enter custom visual search query or leave empty to auto-generate from scene..."
                    disabled={searching}
                    className="w-full rounded-xl border border-surface-border bg-slate-900 pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                  />
                </div>

                <button
                  onClick={handleSearch}
                  disabled={searching}
                  className="inline-flex items-center justify-center gap-2 rounded-xl bg-amber-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-amber-600/20 hover:bg-amber-500 disabled:opacity-50 transition-all shrink-0"
                >
                  {searching ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Searching...</span>
                    </>
                  ) : (
                    <>
                      <Search className="h-4 w-4" />
                      <span>Search Footage</span>
                    </>
                  )}
                </button>
              </div>

              {/* Live Search Progress */}
              {searching && activeSearch && (
                <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 space-y-3">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-amber-300 font-medium flex items-center gap-2">
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-400" />
                      {activeSearch.current_step}
                    </span>
                    <span className="text-amber-400 font-semibold">{activeSearch.progress}%</span>
                  </div>
                  <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-amber-500 to-yellow-400 transition-all duration-300 rounded-full"
                      style={{ width: `${activeSearch.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* 3B. Tab 2: Custom Footage Form (Upload MP4 / Paste TikTok/IG Link) */}
          {activeTab === 'custom' && selectedScene && (
            <form onSubmit={handleCustomFootageSubmit} className="rounded-2xl border border-surface-border bg-surface p-6 space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-surface-border/50">
                <div>
                  <h3 className="text-base font-semibold text-white flex items-center gap-2">
                    <span>Attach Custom Footage for Scene #{selectedScene.sequence}</span>
                  </h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Upload a downloaded MP4 video from TikTok/Instagram or paste a direct video link.
                  </p>
                </div>
              </div>

              {/* Video File Upload */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">
                  Option A: Upload Video File (.mp4, .mov, .webm)
                </label>
                <div className="flex items-center gap-3">
                  <label className="flex-1 cursor-pointer flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-700 bg-slate-900/50 p-4 hover:border-amber-500 transition-colors">
                    <Upload className="h-6 w-6 text-slate-400 mb-1" />
                    <span className="text-xs font-medium text-slate-200">
                      {customFile ? customFile.name : 'Click or drag video file here'}
                    </span>
                    <span className="text-[10px] text-slate-500 mt-0.5">
                      {customFile ? `${(customFile.size / (1024 * 1024)).toFixed(1)} MB` : 'MP4, MOV, WebM up to 200MB'}
                    </span>
                    <input
                      type="file"
                      accept="video/*,.mp4,.mov,.webm"
                      className="hidden"
                      onChange={(e) => {
                        if (e.target.files && e.target.files[0]) {
                          setCustomFile(e.target.files[0]);
                        }
                      }}
                    />
                  </label>
                  {customFile && (
                    <button
                      type="button"
                      onClick={() => setCustomFile(null)}
                      className="text-xs text-rose-400 hover:underline shrink-0"
                    >
                      Clear File
                    </button>
                  )}
                </div>
              </div>

              {/* Video URL Input */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">
                  Option B: Or Paste Video URL (TikTok / Instagram Reels / YouTube Shorts)
                </label>
                <div className="relative">
                  <Link2 className="absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
                  <input
                    type="url"
                    value={customUrl}
                    onChange={(e) => setCustomUrl(e.target.value)}
                    placeholder="e.g. https://www.tiktok.com/@... or https://www.instagram.com/reel/..."
                    className="w-full rounded-xl border border-surface-border bg-slate-900 pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                  />
                </div>
              </div>

              {/* Optional Title */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 block">
                  Clip Title / Note (Optional)
                </label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  placeholder="e.g. Grinding stone demonstration B-roll"
                  className="w-full rounded-xl border border-surface-border bg-slate-900 px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-amber-500"
                />
              </div>

              {/* Scene Range Assignment Option */}
              <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 space-y-3">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    id="rangeEnabled"
                    checked={customRangeEnabled}
                    onChange={(e) => setCustomRangeEnabled(e.target.checked)}
                    className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-amber-600 focus:ring-amber-500"
                  />
                  <label htmlFor="rangeEnabled" className="text-xs font-semibold text-white cursor-pointer select-none">
                    Assign this footage across multiple scenes (Continuous B-roll)
                  </label>
                </div>

                {customRangeEnabled && (
                  <div className="pl-7 space-y-2">
                    <div className="flex items-center gap-2 text-xs text-slate-300">
                      <span>Apply continuously from</span>
                      <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-amber-400 font-bold">
                        Scene #{selectedScene.sequence}
                      </span>
                      <span>through</span>
                      <select
                        value={customEndSeq}
                        onChange={(e) => setCustomEndSeq(Number(e.target.value))}
                        className="rounded-lg border border-surface-border bg-slate-900 px-2.5 py-1 text-xs text-white font-mono"
                      >
                        {scenes
                          .filter((s) => s.sequence >= selectedScene.sequence)
                          .map((s) => (
                            <option key={s.id} value={s.sequence}>
                              Scene #{s.sequence} ({s.duration.toFixed(1)}s)
                            </option>
                          ))}
                      </select>
                    </div>
                    <p className="text-[11px] text-slate-400 italic">
                      ✨ Continuous Trimming enabled: The footage will automatically play across Scenes #{selectedScene.sequence} to #{customEndSeq} seamlessly without restarting!
                    </p>
                  </div>
                )}
              </div>

              {/* Submit Button */}
              <div className="flex justify-end pt-2">
                <button
                  type="submit"
                  disabled={uploadingCustom || (!customFile && !customUrl.trim())}
                  className="inline-flex items-center gap-2 rounded-xl bg-amber-600 px-6 py-2.5 text-xs font-semibold text-white shadow-lg shadow-amber-600/20 hover:bg-amber-500 disabled:opacity-50 transition-all"
                >
                  {uploadingCustom ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Processing Footage...</span>
                    </>
                  ) : (
                    <>
                      <Upload className="h-4 w-4" />
                      <span>
                        {customRangeEnabled && customEndSeq > selectedScene.sequence
                          ? `Attach to Scenes #${selectedScene.sequence} – #${customEndSeq}`
                          : `Attach to Scene #${selectedScene.sequence}`}
                      </span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}

          {/* Platform Filter Tabs & Candidate Count */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2">
              {['all', 'youtube', 'pexels', 'web'].map((p) => (
                <button
                  key={p}
                  onClick={() => setPlatformFilter(p)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-medium capitalize transition-colors ${
                    platformFilter === p
                      ? 'bg-amber-600 text-white'
                      : 'bg-surface border border-surface-border text-slate-400 hover:text-white'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>

            <span className="text-xs text-slate-400">
              Showing {filteredCandidates.length} candidate(s)
            </span>
          </div>

          {/* Candidate Cards Grid */}
          {filteredCandidates.length === 0 ? (
            <div className="rounded-2xl border border-surface-border bg-surface p-12 text-center">
              <Film className="h-10 w-10 text-slate-600 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-white">No Candidate Footage Yet</h3>
              <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                Click <strong>Search Footage</strong> above to discover video candidates from the web and rank them by visual similarity.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {filteredCandidates.map((cand) => {
                const isSelected = activeSelection?.candidate_id === cand.id;
                const isSelectingThis = selectingId === cand.id;

                // Match badge styling
                const isExact = cand.match_type.toLowerCase().includes('exact');
                const isHigh = cand.match_type.toLowerCase().includes('high');

                return (
                  <div
                    key={cand.id}
                    className={`rounded-2xl border transition-all flex flex-col overflow-hidden ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-500/5 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500'
                        : 'border-surface-border bg-surface hover:border-slate-700'
                    }`}
                  >
                    {/* Thumbnail Image */}
                    <div className="relative aspect-video w-full bg-slate-900 overflow-hidden">
                      {cand.thumbnail_url ? (
                        <img
                          src={cand.thumbnail_url}
                          alt={cand.title}
                          className="h-full w-full object-cover"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center text-slate-600">
                          <Film className="h-8 w-8" />
                        </div>
                      )}

                      {/* Duration Tag */}
                      {cand.duration && (
                        <span className="absolute bottom-2 right-2 rounded bg-black/80 px-1.5 py-0.5 text-[10px] font-mono text-white">
                          {cand.duration.toFixed(0)}s
                        </span>
                      )}

                      {/* Platform Tag */}
                      <span className="absolute top-2 left-2 rounded-md bg-black/75 px-2 py-0.5 text-[10px] font-semibold text-white uppercase tracking-wider">
                        {cand.source_platform}
                      </span>

                      {/* Match Badge */}
                      <span
                        className={`absolute top-2 right-2 rounded-md px-2 py-0.5 text-[10px] font-semibold ${
                          isExact
                            ? 'bg-emerald-500 text-black font-bold'
                            : isHigh
                            ? 'bg-blue-500 text-white'
                            : 'bg-purple-500/90 text-white'
                        }`}
                      >
                        {cand.match_type}
                      </span>
                    </div>

                    {/* Candidate Details */}
                    <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                      <div>
                        <h4 className="text-xs font-semibold text-white line-clamp-2 leading-snug">
                          {cand.title}
                        </h4>
                        {cand.creator && (
                          <p className="text-[11px] text-slate-400 mt-1">
                            By: <span className="text-slate-300">{cand.creator}</span>
                          </p>
                        )}
                      </div>

                      {/* Similarity Scores */}
                      <div className="grid grid-cols-2 gap-2 pt-2 border-t border-surface-border/50 text-center text-xs">
                        <div className="bg-slate-900/50 rounded-lg p-2 border border-slate-800">
                          <span className="text-[10px] text-slate-400 block">Visual Match</span>
                          <span className="text-xs font-bold text-amber-400 font-mono mt-0.5 block">
                            {Math.round(cand.visual_score * 100)}%
                          </span>
                        </div>
                        <div className="bg-slate-900/50 rounded-lg p-2 border border-slate-800">
                          <span className="text-[10px] text-slate-400 block">Overall Score</span>
                          <span className="text-xs font-bold text-emerald-400 font-mono mt-0.5 block">
                            {Math.round(cand.final_score * 100)}%
                          </span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="pt-2 flex items-center justify-between gap-2">
                        <a
                          href={cand.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs text-slate-300 hover:text-white px-2.5 py-1.5 rounded-lg border border-surface-border hover:bg-slate-800 transition-colors"
                        >
                          <ExternalLink className="h-3.5 w-3.5 text-amber-400" />
                          <span>Source</span>
                        </a>

                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              if (rangeCandidateId === cand.id) {
                                setRangeCandidateId(null);
                              } else {
                                setRangeCandidateId(cand.id);
                                if (selectedScene) {
                                  setRangeEndSeq(Math.min(selectedScene.sequence + 4, scenes.length || selectedScene.sequence));
                                }
                              }
                            }}
                            className={`inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg border transition-colors ${
                              rangeCandidateId === cand.id
                                ? 'bg-amber-500/20 text-amber-400 border-amber-500/50'
                                : 'bg-surface border-surface-border text-slate-300 hover:text-white hover:border-slate-600'
                            }`}
                            title="Assign this footage across multiple continuous scenes"
                          >
                            <Layers className="h-3.5 w-3.5 text-amber-400" />
                            <span>Range...</span>
                          </button>

                          <button
                            onClick={() => handleSelectCandidate(cand.id)}
                            disabled={isSelected || isSelectingThis}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                              isSelected
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 cursor-default'
                                : 'bg-amber-600 hover:bg-amber-500 text-white shadow-md shadow-amber-600/20'
                            }`}
                          >
                            {isSelectingThis ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : isSelected ? (
                              <>
                                <Check className="h-3.5 w-3.5" />
                                <span>Selected</span>
                              </>
                            ) : (
                              <span>Select</span>
                            )}
                          </button>
                        </div>
                      </div>

                      {/* Range Selection Inline Panel */}
                      {rangeCandidateId === cand.id && selectedScene && (
                        <div className="mt-3 p-3 rounded-xl bg-slate-900/90 border border-amber-500/40 space-y-2.5 animate-in fade-in duration-200">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold text-amber-400 flex items-center gap-1.5">
                              <Layers className="h-3.5 w-3.5" />
                              Apply to Continuous Scenes
                            </span>
                            <button
                              type="button"
                              onClick={() => setRangeCandidateId(null)}
                              className="text-[11px] text-slate-400 hover:text-white"
                            >
                              Cancel
                            </button>
                          </div>
                          <p className="text-[11px] text-slate-400 leading-tight">
                            Span this continuous footage across consecutive scenes (e.g. Scenes #{selectedScene.sequence} to #{rangeEndSeq}). Trims will flow seamlessly without restarting.
                          </p>
                          <div className="flex flex-wrap items-center gap-2 pt-1">
                            <span className="text-xs text-slate-300 font-mono">
                              Scene #{selectedScene.sequence} to #
                            </span>
                            <select
                              value={rangeEndSeq}
                              onChange={(e) => setRangeEndSeq(Number(e.target.value))}
                              className="bg-surface border border-surface-border rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-amber-500 font-mono"
                            >
                              {scenes
                                .filter((s) => s.sequence >= selectedScene.sequence)
                                .map((s) => (
                                  <option key={s.id} value={s.sequence}>
                                    Scene #{s.sequence} ({s.end_time.toFixed(1)}s)
                                  </option>
                                ))}
                            </select>
                            <button
                              type="button"
                              onClick={() => handleRangeSelect(cand.id, rangeEndSeq)}
                              disabled={applyingRange}
                              className="ml-auto inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold bg-amber-600 hover:bg-amber-500 text-white disabled:opacity-50 transition-all shadow-md shadow-amber-600/20"
                            >
                              {applyingRange ? (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                              ) : (
                                <Check className="h-3.5 w-3.5" />
                              )}
                              <span>Apply Range</span>
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
