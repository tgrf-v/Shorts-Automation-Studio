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
} from 'lucide-react';
import { getProject } from '@/lib/api/projects';
import { getProjectAnalysis } from '@/lib/api/analysis';
import {
  searchFootageForScene,
  getFootageSearch,
  listSceneFootageCandidates,
  selectFootageCandidate,
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
    }
  }, [selectedScene, loadSceneCandidates]);

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
          {/* Search Controls Header */}
          {selectedScene && (
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
                      <div className="pt-2 flex items-center justify-between gap-3">
                        <a
                          href={cand.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs text-slate-300 hover:text-white px-2.5 py-1.5 rounded-lg border border-surface-border hover:bg-slate-800 transition-colors"
                        >
                          <ExternalLink className="h-3.5 w-3.5 text-amber-400" />
                          <span>Open Source</span>
                        </a>

                        <button
                          onClick={() => handleSelectCandidate(cand.id)}
                          disabled={isSelected || isSelectingThis}
                          className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
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
                            <span>Select Footage</span>
                          )}
                        </button>
                      </div>
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
