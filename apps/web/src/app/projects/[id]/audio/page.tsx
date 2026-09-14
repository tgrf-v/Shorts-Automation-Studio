'use client';

import React, { useEffect, useState, use, useCallback, useRef } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Music,
  Volume2,
  VolumeX,
  Play,
  Pause,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ChevronDown,
  Loader2,
  Plus,
  Trash2,
  Sparkles,
  Sliders,
  Repeat,
  Headphones,
  Check,
  Upload,
  FileAudio,
  Radio,
  Zap,
  Subtitles,
  Clapperboard,
} from 'lucide-react';
import { getProject } from '@/lib/api/projects';
import { getActiveProductionTimeline } from '@/lib/api/timeline';
import {
  uploadAudioAsset,
  listAudioAssets,
  deleteAudioAsset,
  getAudioStreamUrl,
  generateAudioTimeline,
  getActiveAudioTimeline,
  getAudioTimelineVersions,
  getAudioTimeline,
  activateAudioTimeline,
  addAudioLayer,
  updateAudioLayer,
  deleteAudioLayer,
  getSceneSFXSuggestions,
} from '@/lib/api/audio';
import {
  Project,
  ProductionTimeline,
  AudioAsset,
  AudioTimeline,
  AudioTimelineSummary,
  AudioLayer,
  AudioType,
  SceneSFXSuggestionsResponse,
} from '@/lib/api/types';

interface AudioPageProps {
  params: Promise<{ id: string }>;
}

export default function AudioTimelinePage({ params }: AudioPageProps) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  // State
  const [project, setProject] = useState<Project | null>(null);
  const [prodTimeline, setProdTimeline] = useState<ProductionTimeline | null>(null);
  const [timeline, setTimeline] = useState<AudioTimeline | null>(null);
  const [versions, setVersions] = useState<AudioTimelineSummary[]>([]);
  const [assets, setAssets] = useState<AudioAsset[]>([]);
  const [assetTab, setAssetTab] = useState<AudioType>('bgm');

  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Selected Layer for editing
  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(null);
  const [layerEditState, setLayerEditState] = useState<{
    name: string;
    start_time: number;
    end_time: number;
    volume: number;
    fade_in: number;
    fade_out: number;
    loop: boolean;
    enabled: boolean;
    ducking_enabled: boolean;
    ducking_level: number;
    notes: string;
    saving: boolean;
  } | null>(null);

  // Suggestions state
  const [sfxSuggestions, setSfxSuggestions] = useState<SceneSFXSuggestionsResponse[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);

  // Preview Player State
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const previewTimerRef = useRef<NodeJS.Timeout | null>(null);
  const audioPreviewRef = useRef<HTMLAudioElement | null>(null);
  const [activePreviewAssetId, setActivePreviewAssetId] = useState<string | null>(null);

  // File Upload Ref
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Fetch all initial data
  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [projData, ptData, activeAudioTl, audioVersions, assetList] = await Promise.all([
        getProject(projectId),
        getActiveProductionTimeline(projectId).catch(() => null),
        getActiveAudioTimeline(projectId).catch(() => null),
        getAudioTimelineVersions(projectId).catch(() => []),
        listAudioAssets(projectId).catch(() => []),
      ]);

      setProject(projData);
      setProdTimeline(ptData);
      setTimeline(activeAudioTl);
      setVersions(audioVersions);
      setAssets(assetList);

      if (activeAudioTl && activeAudioTl.layers.length > 0 && !selectedLayerId) {
        setSelectedLayerId(activeAudioTl.layers[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audio workspace.');
    } finally {
      setLoading(false);
    }
  }, [projectId, selectedLayerId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Sync selected layer into edit state
  useEffect(() => {
    if (!timeline || !selectedLayerId) {
      setLayerEditState(null);
      return;
    }
    const layer = timeline.layers.find((l) => l.id === selectedLayerId);
    if (layer) {
      setLayerEditState({
        name: layer.name,
        start_time: layer.start_time,
        end_time: layer.end_time,
        volume: layer.volume,
        fade_in: layer.fade_in,
        fade_out: layer.fade_out,
        loop: layer.loop,
        enabled: layer.enabled,
        ducking_enabled: layer.ducking_enabled,
        ducking_level: layer.ducking_level,
        notes: layer.notes || '',
        saving: false,
      });
    }
  }, [timeline, selectedLayerId]);

  // Load SFX Suggestions when production timeline is available
  const loadSuggestions = async () => {
    if (!prodTimeline || prodTimeline.items.length === 0) return;
    setLoadingSuggestions(true);
    try {
      const results: SceneSFXSuggestionsResponse[] = [];
      for (const item of prodTimeline.items) {
        if (item.scene_id) {
          const res = await getSceneSFXSuggestions(item.scene_id);
          results.push(res);
        }
      }
      setSfxSuggestions(results);
    } catch (err) {
      console.error('Failed to load SFX suggestions:', err);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  // Generate / Regenerate Audio Timeline
  const handleGenerateTimeline = async () => {
    setGenerating(true);
    setError(null);
    setActionSuccess(null);
    try {
      const bgmAsset = assets.find((a) => a.type === 'bgm');
      const newTl = await generateAudioTimeline(projectId, {
        bgm_asset_id: bgmAsset ? bgmAsset.id : null,
        ducking_enabled: true,
        ducking_level: -6.0,
      });
      setTimeline(newTl);
      if (newTl.layers.length > 0) {
        setSelectedLayerId(newTl.layers[0].id);
      }
      const vList = await getAudioTimelineVersions(projectId);
      setVersions(vList);
      setActionSuccess(`Audio Timeline v${newTl.version} generated successfully!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate audio timeline.');
    } finally {
      setGenerating(false);
    }
  };

  // Switch Version
  const handleSelectVersion = async (versionId: string) => {
    try {
      setLoading(true);
      const tl = await getAudioTimeline(versionId);
      setTimeline(tl);
      if (tl.layers.length > 0) {
        setSelectedLayerId(tl.layers[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch version.');
    } finally {
      setLoading(false);
    }
  };

  // Activate Version
  const handleActivate = async () => {
    if (!timeline) return;
    try {
      const activated = await activateAudioTimeline(timeline.id);
      setTimeline(activated);
      const vList = await getAudioTimelineVersions(projectId);
      setVersions(vList);
      setActionSuccess(`Audio Timeline v${activated.version} is now active!`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate version.');
    }
  };

  // File Upload for Audio Assets
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      const newAsset = await uploadAudioAsset(projectId, file, assetTab);
      setAssets((prev) => [newAsset, ...prev]);
      setActionSuccess(`Uploaded "${newAsset.name}" to ${assetTab.toUpperCase()} library.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Delete Asset
  const handleDeleteAsset = async (assetId: string) => {
    if (!confirm('Are you sure you want to delete this audio asset?')) return;
    try {
      await deleteAudioAsset(assetId);
      setAssets((prev) => prev.filter((a) => a.id !== assetId));
      setActionSuccess('Asset deleted.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete asset.');
    }
  };

  // Add Asset to Timeline
  const handleAddAssetToTimeline = async (asset: AudioAsset, customStart?: number) => {
    if (!timeline) {
      setError('Please generate or select an audio timeline first.');
      return;
    }

    try {
      const start = customStart !== undefined ? customStart : 0;
      const newLayer = await addAudioLayer(
        projectId,
        {
          audio_asset_id: asset.id,
          type: asset.type,
          name: asset.name,
          start_time: start,
          volume: asset.type === 'bgm' ? -18.0 : -6.0,
          fade_in: asset.type === 'bgm' ? 1.0 : 0.0,
          fade_out: asset.type === 'bgm' ? 2.0 : 0.1,
          loop: asset.type === 'bgm',
          enabled: true,
          ducking_enabled: asset.type === 'bgm',
          ducking_level: -6.0,
        },
        timeline.id
      );

      const refreshed = await getAudioTimeline(timeline.id);
      setTimeline(refreshed);
      setSelectedLayerId(newLayer.id);
      setActionSuccess(`Added "${asset.name}" to ${asset.type.toUpperCase()} track.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add layer.');
    }
  };

  // Save Layer Edit Changes
  const handleSaveLayerEdit = async () => {
    if (!selectedLayerId || !layerEditState || !timeline) return;

    setLayerEditState((prev) => (prev ? { ...prev, saving: true } : null));
    try {
      const updated = await updateAudioLayer(selectedLayerId, {
        name: layerEditState.name,
        start_time: Number(layerEditState.start_time),
        end_time: Number(layerEditState.end_time),
        volume: Number(layerEditState.volume),
        fade_in: Number(layerEditState.fade_in),
        fade_out: Number(layerEditState.fade_out),
        loop: layerEditState.loop,
        enabled: layerEditState.enabled,
        ducking_enabled: layerEditState.ducking_enabled,
        ducking_level: Number(layerEditState.ducking_level),
        notes: layerEditState.notes,
      });

      const refreshed = await getAudioTimeline(timeline.id);
      setTimeline(refreshed);
      setLayerEditState((prev) => (prev ? { ...prev, saving: false } : null));
      setActionSuccess(`Saved changes for layer "${updated.name}".`);
    } catch (err) {
      setLayerEditState((prev) => (prev ? { ...prev, saving: false } : null));
      setError(err instanceof Error ? err.message : 'Failed to update layer.');
    }
  };

  // Delete Layer
  const handleDeleteLayer = async (layerId: string) => {
    if (!confirm('Are you sure you want to remove this audio layer?')) return;
    try {
      await deleteAudioLayer(layerId);
      if (timeline) {
        const refreshed = await getAudioTimeline(timeline.id);
        setTimeline(refreshed);
        if (selectedLayerId === layerId) {
          setSelectedLayerId(refreshed.layers[0]?.id || null);
        }
      }
      setActionSuccess('Layer removed from timeline.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove layer.');
    }
  };

  // Apply SFX Suggestion
  const handleApplySuggestion = async (keyword: string, position: number) => {
    if (!timeline) {
      setError('Please generate or select an audio timeline first.');
      return;
    }

    // Find first SFX asset or default
    const sfxAsset = assets.find((a) => a.type === 'sfx');
    if (!sfxAsset) {
      setError('No SFX asset available in library. Please upload an SFX audio file first.');
      return;
    }

    try {
      await handleAddAssetToTimeline(sfxAsset, position);
      setActionSuccess(`Applied SFX cue "${keyword}" at ${position}s.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to apply suggestion.');
    }
  };

  // Audio Preview helpers
  const handlePlayAssetPreview = (assetId: string) => {
    if (activePreviewAssetId === assetId) {
      if (audioPreviewRef.current) {
        audioPreviewRef.current.pause();
      }
      setActivePreviewAssetId(null);
    } else {
      setActivePreviewAssetId(assetId);
      if (audioPreviewRef.current) {
        audioPreviewRef.current.src = getAudioStreamUrl(assetId);
        audioPreviewRef.current.play().catch(() => {});
      }
    }
  };

  const handleTogglePlayTimeline = () => {
    if (isPlaying) {
      setIsPlaying(false);
      if (previewTimerRef.current) clearInterval(previewTimerRef.current);
    } else {
      setIsPlaying(true);
      const totalDur = timeline?.total_duration || 30;
      previewTimerRef.current = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= totalDur) {
            setIsPlaying(false);
            if (previewTimerRef.current) clearInterval(previewTimerRef.current);
            return 0;
          }
          return Math.min(totalDur, Math.round((prev + 0.2) * 10) / 10);
        });
      }, 200);
    }
  };

  const formatSeconds = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = (sec % 60).toFixed(2);
    return `${m.toString().padStart(2, '0')}:${parseFloat(s) < 10 ? '0' : ''}${s}`;
  };

  const totalDuration = timeline?.total_duration || prodTimeline?.duration || 30;

  if (loading && !project) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center p-8">
        <div className="flex flex-col items-center space-y-3 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
          <span className="text-sm">Loading BGM & SFX Timeline workspace...</span>
        </div>
      </div>
    );
  }

  const bgmLayers = timeline?.layers.filter((l) => l.type === 'bgm') || [];
  const sfxLayers = timeline?.layers.filter((l) => l.type === 'sfx') || [];
  const filteredAssets = assets.filter((a) => a.type === assetTab);

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Hidden Audio Element for Preview */}
      <audio
        ref={audioPreviewRef}
        onEnded={() => setActivePreviewAssetId(null)}
        className="hidden"
      />

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
                BGM & SFX Timeline
              </h1>
              <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-2.5 py-0.5 text-xs text-purple-400">
                Milestone 9
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Project: <span className="text-slate-200 font-medium">{project?.name}</span> • Multi-track audio mix & sound effects
            </p>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Navigation Links */}
          <Link
            href={`/projects/${projectId}/timeline`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-semibold text-emerald-300 hover:bg-emerald-500/20 transition-colors"
          >
            <Clapperboard className="h-3.5 w-3.5" />
            <span>Timeline (M7)</span>
          </Link>

          <Link
            href={`/projects/${projectId}/captions`}
            className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors"
          >
            <Subtitles className="h-3.5 w-3.5" />
            <span>Captions (M8)</span>
          </Link>

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
                    Audio v{v.version} {v.is_active ? '(Active)' : ''} — {v.bgm_layers_count} BGM, {v.sfx_layers_count} SFX
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
              className="inline-flex items-center gap-1.5 rounded-xl border border-purple-500/30 bg-purple-500/10 px-3 py-2 text-xs font-semibold text-purple-300 hover:bg-purple-500/20 transition-colors"
            >
              <Check className="h-3.5 w-3.5" />
              <span>Set as Active</span>
            </button>
          )}

          {/* Generate Button */}
          <button
            onClick={handleGenerateTimeline}
            disabled={generating}
            className="inline-flex items-center gap-2 rounded-xl bg-purple-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-purple-600/20 hover:bg-purple-500 disabled:opacity-50 transition-colors"
          >
            {generating ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Generating...</span>
              </>
            ) : (
              <>
                <Sparkles className="h-3.5 w-3.5" />
                <span>{timeline ? 'Regenerate Audio' : 'Generate Audio'}</span>
              </>
            )}
          </button>

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
        <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3.5">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-amber-500/20 text-amber-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-amber-300">
                Audio Timeline Outdated (Stale)
              </h3>
              <p className="text-xs text-amber-200/80 mt-0.5">
                The active production timeline has changed. Regenerate to sync audio duration and scenes.
              </p>
              {timeline.stale_reasons && timeline.stale_reasons.length > 0 && (
                <ul className="mt-2 text-xs text-amber-300/70 list-disc list-inside">
                  {timeline.stale_reasons.map((r, i) => (
                    <li key={i}>{r}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
          <button
            onClick={handleGenerateTimeline}
            disabled={generating}
            className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-amber-500 px-4 py-2 text-xs font-semibold text-black hover:bg-amber-400 transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Sync & Regenerate</span>
          </button>
        </div>
      )}

      {/* Metrics Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="rounded-2xl border border-surface-border bg-surface p-4">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-medium mb-1">
            <Clock className="h-4 w-4 text-purple-400" />
            <span>Total Duration</span>
          </div>
          <p className="text-xl font-bold text-white tracking-tight">
            {totalDuration.toFixed(2)}s
          </p>
        </div>

        <div className="rounded-2xl border border-surface-border bg-surface p-4">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-medium mb-1">
            <Music className="h-4 w-4 text-emerald-400" />
            <span>BGM Track</span>
          </div>
          <p className="text-xl font-bold text-white tracking-tight">
            {bgmLayers.length > 0 ? `${bgmLayers[0].volume} dB` : 'None'}
          </p>
        </div>

        <div className="rounded-2xl border border-surface-border bg-surface p-4">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-medium mb-1">
            <Zap className="h-4 w-4 text-amber-400" />
            <span>SFX Cues</span>
          </div>
          <p className="text-xl font-bold text-white tracking-tight">
            {sfxLayers.length} {sfxLayers.length === 1 ? 'cue' : 'cues'}
          </p>
        </div>

        <div className="rounded-2xl border border-surface-border bg-surface p-4">
          <div className="flex items-center gap-2 text-slate-400 text-xs font-medium mb-1">
            <Volume2 className="h-4 w-4 text-blue-400" />
            <span>Auto Ducking</span>
          </div>
          <p className="text-xl font-bold text-white tracking-tight">
            {timeline?.ducking_enabled ? `${timeline.ducking_level} dB` : 'Disabled'}
          </p>
        </div>
      </div>

      {/* Section: Multi-track Timeline Visualizer */}
      <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Layers className="h-4 w-4 text-purple-400" />
              <span>Multi-track Audio Timeline</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Visual overview of Narration (M5), Background Music, and Sound Effect cues
            </p>
          </div>

          {/* Scrubber & Player Controls */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleTogglePlayTimeline}
              className="inline-flex items-center gap-2 rounded-xl border border-surface-border bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 transition-colors"
            >
              {isPlaying ? <Pause className="h-3.5 w-3.5 text-amber-400" /> : <Play className="h-3.5 w-3.5 text-emerald-400" />}
              <span>{isPlaying ? 'Pause' : 'Play Timeline'}</span>
            </button>
            <span className="font-mono text-xs text-purple-300">
              {formatSeconds(currentTime)} / {formatSeconds(totalDuration)}
            </span>
          </div>
        </div>

        {/* Timeline Visualization Box */}
        <div className="rounded-xl border border-surface-border bg-slate-950 p-4 space-y-4 select-none relative overflow-x-auto">
          {/* Time Ruler */}
          <div className="h-6 border-b border-slate-800 flex justify-between text-[10px] text-slate-500 font-mono">
            <span>0.0s</span>
            <span>{(totalDuration * 0.25).toFixed(1)}s</span>
            <span>{(totalDuration * 0.5).toFixed(1)}s</span>
            <span>{(totalDuration * 0.75).toFixed(1)}s</span>
            <span>{totalDuration.toFixed(1)}s</span>
          </div>

          {/* Current Time Playhead */}
          <div
            className="absolute top-4 bottom-4 w-0.5 bg-rose-500 pointer-events-none z-10 transition-all duration-100"
            style={{ left: `${(currentTime / Math.max(1, totalDuration)) * 100}%` }}
          >
            <div className="h-2 w-2 -ml-[3px] rounded-full bg-rose-500 shadow-sm" />
          </div>

          {/* Track 1: Narration (Priority 1) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
              <span className="flex items-center gap-1.5 text-blue-400">
                <Volume2 className="h-3 w-3" />
                <span>Track 1: Narration / TTS (Priority 1)</span>
              </span>
              <span className="text-[10px] text-slate-500">0.0 dB (Unity)</span>
            </div>
            <div className="h-8 rounded-lg bg-slate-900 border border-slate-800 relative overflow-hidden flex">
              {prodTimeline?.items && prodTimeline.items.length > 0 ? (
                prodTimeline.items.map((item) => {
                  const leftPct = (item.start_time / Math.max(1, totalDuration)) * 100;
                  const widthPct = ((item.end_time - item.start_time) / Math.max(1, totalDuration)) * 100;
                  return (
                    <div
                      key={item.id}
                      className="absolute top-1 bottom-1 rounded bg-blue-600/30 border border-blue-500/40 text-[10px] text-blue-200 px-1.5 flex items-center overflow-hidden whitespace-nowrap"
                      style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                      title={`Scene ${item.sequence}: ${item.script_text}`}
                    >
                      <span className="truncate">Scene {item.sequence}: {item.script_text}</span>
                    </div>
                  );
                })
              ) : (
                <div className="w-full flex items-center justify-center text-[10px] text-slate-500">
                  No narration audio timeline found.
                </div>
              )}
            </div>
          </div>

          {/* Track 2: BGM (Priority 3) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <Music className="h-3 w-3" />
                <span>Track 2: Background Music (Priority 3)</span>
              </span>
              <span className="text-[10px] text-slate-500">
                {bgmLayers.length > 0 ? `${bgmLayers[0].volume} dB • Ducked by Narration` : 'No BGM layer'}
              </span>
            </div>
            <div className="h-8 rounded-lg bg-slate-900 border border-slate-800 relative overflow-hidden">
              {bgmLayers.map((bgm) => {
                const leftPct = (bgm.start_time / Math.max(1, totalDuration)) * 100;
                const widthPct = ((bgm.end_time - bgm.start_time) / Math.max(1, totalDuration)) * 100;
                const isSelected = selectedLayerId === bgm.id;
                return (
                  <div
                    key={bgm.id}
                    onClick={() => setSelectedLayerId(bgm.id)}
                    className={`absolute top-1 bottom-1 rounded cursor-pointer transition-all flex items-center justify-between px-2 text-[10px] ${
                      isSelected
                        ? 'bg-emerald-500/40 border-2 border-emerald-400 text-emerald-100 shadow-md shadow-emerald-500/20'
                        : 'bg-emerald-600/20 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-600/30'
                    }`}
                    style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                  >
                    <span className="font-medium truncate">{bgm.name}</span>
                    <span className="flex items-center gap-1 text-[9px] opacity-80">
                      {bgm.loop && <Repeat className="h-2.5 w-2.5" />}
                      <span>{bgm.volume} dB</span>
                    </span>
                  </div>
                );
              })}
              {bgmLayers.length === 0 && (
                <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-500">
                  Click &ldquo;Add to Timeline&rdquo; on any BGM asset in the library to add music.
                </div>
              )}
            </div>
          </div>

          {/* Track 3: SFX (Priority 2) */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-medium">
              <span className="flex items-center gap-1.5 text-amber-400">
                <Zap className="h-3 w-3" />
                <span>Track 3: Sound Effects (Priority 2)</span>
              </span>
              <span className="text-[10px] text-slate-500">
                {sfxLayers.length} {sfxLayers.length === 1 ? 'cue' : 'cues'} placed
              </span>
            </div>
            <div className="h-9 rounded-lg bg-slate-900 border border-slate-800 relative overflow-hidden">
              {sfxLayers.map((sfx) => {
                const leftPct = (sfx.start_time / Math.max(1, totalDuration)) * 100;
                const dur = Math.max(0.6, sfx.end_time - sfx.start_time);
                const widthPct = Math.max(3, (dur / Math.max(1, totalDuration)) * 100);
                const isSelected = selectedLayerId === sfx.id;
                return (
                  <div
                    key={sfx.id}
                    onClick={() => setSelectedLayerId(sfx.id)}
                    className={`absolute top-1 bottom-1 rounded cursor-pointer transition-all flex items-center px-1.5 text-[10px] ${
                      isSelected
                        ? 'bg-amber-500/50 border-2 border-amber-400 text-amber-100 shadow-md shadow-amber-500/20 z-10'
                        : 'bg-amber-600/30 border border-amber-500/40 text-amber-300 hover:bg-amber-600/40'
                    }`}
                    style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                    title={`${sfx.name} at ${sfx.start_time}s (${sfx.volume} dB)`}
                  >
                    <span className="truncate font-medium">{sfx.name}</span>
                  </div>
                );
              })}
              {sfxLayers.length === 0 && (
                <div className="w-full h-full flex items-center justify-center text-[10px] text-slate-500">
                  No SFX cues yet. Use &ldquo;SFX Suggestions&rdquo; or add from the library below.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Layer Inspector & Asset Library */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Selected Layer Inspector (5 Cols) */}
        <div className="lg:col-span-5 rounded-2xl border border-surface-border bg-surface p-6 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-surface-border">
            <h2 className="text-base font-semibold text-white flex items-center gap-2">
              <Sliders className="h-4 w-4 text-purple-400" />
              <span>Layer Inspector</span>
            </h2>
            {selectedLayerId && (
              <button
                onClick={() => handleDeleteLayer(selectedLayerId)}
                className="text-rose-400 hover:text-rose-300 p-1 rounded-lg hover:bg-rose-500/10 transition-colors"
                title="Remove layer"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>

          {layerEditState ? (
            <div className="space-y-4">
              {/* Layer Name */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Layer Name
                </label>
                <input
                  type="text"
                  value={layerEditState.name}
                  onChange={(e) =>
                    setLayerEditState((prev) => (prev ? { ...prev, name: e.target.value } : null))
                  }
                  className="w-full rounded-xl border border-surface-border bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
                />
              </div>

              {/* Start & End Timestamps */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Start Time (s)
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    value={layerEditState.start_time}
                    onChange={(e) =>
                      setLayerEditState((prev) =>
                        prev ? { ...prev, start_time: parseFloat(e.target.value) || 0 } : null
                      )
                    }
                    className="w-full rounded-xl border border-surface-border bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    End Time (s)
                  </label>
                  <input
                    type="number"
                    step="0.05"
                    min="0"
                    value={layerEditState.end_time}
                    onChange={(e) =>
                      setLayerEditState((prev) =>
                        prev ? { ...prev, end_time: parseFloat(e.target.value) || 0 } : null
                      )
                    }
                    className="w-full rounded-xl border border-surface-border bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              {/* Volume Slider (dB) */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs font-medium">
                  <span className="text-slate-400">Volume Level</span>
                  <span className="text-purple-300 font-mono">{layerEditState.volume} dB</span>
                </div>
                <input
                  type="range"
                  min="-48"
                  max="6"
                  step="1"
                  value={layerEditState.volume}
                  onChange={(e) =>
                    setLayerEditState((prev) =>
                      prev ? { ...prev, volume: parseFloat(e.target.value) } : null
                    )
                  }
                  className="w-full accent-purple-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-500 font-mono">
                  <span>-48 dB (Very quiet)</span>
                  <span>-18 dB (BGM)</span>
                  <span>-6 dB (SFX)</span>
                  <span>0 dB (Max unity)</span>
                </div>
              </div>

              {/* Fades */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Fade In (s)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={layerEditState.fade_in}
                    onChange={(e) =>
                      setLayerEditState((prev) =>
                        prev ? { ...prev, fade_in: parseFloat(e.target.value) || 0 } : null
                      )
                    }
                    className="w-full rounded-xl border border-surface-border bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">
                    Fade Out (s)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={layerEditState.fade_out}
                    onChange={(e) =>
                      setLayerEditState((prev) =>
                        prev ? { ...prev, fade_out: parseFloat(e.target.value) || 0 } : null
                      )
                    }
                    className="w-full rounded-xl border border-surface-border bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              {/* Toggles: Loop & Ducking */}
              <div className="grid grid-cols-2 gap-3 pt-2">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={layerEditState.loop}
                    onChange={(e) =>
                      setLayerEditState((prev) =>
                        prev ? { ...prev, loop: e.target.checked } : null
                      )
                    }
                    className="rounded border-slate-700 bg-slate-900 text-purple-600 focus:ring-purple-500"
                  />
                  <span>Loop Audio</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={layerEditState.ducking_enabled}
                    onChange={(e) =>
                      setLayerEditState((prev) =>
                        prev ? { ...prev, ducking_enabled: e.target.checked } : null
                      )
                    }
                    className="rounded border-slate-700 bg-slate-900 text-purple-600 focus:ring-purple-500"
                  />
                  <span>Auto-ducking</span>
                </label>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1">
                  Notes
                </label>
                <input
                  type="text"
                  placeholder="e.g. Ambient swell during scene reveal"
                  value={layerEditState.notes}
                  onChange={(e) =>
                    setLayerEditState((prev) => (prev ? { ...prev, notes: e.target.value } : null))
                  }
                  className="w-full rounded-xl border border-surface-border bg-slate-900 px-3 py-2 text-xs text-slate-200 focus:border-purple-500 focus:outline-none"
                />
              </div>

              {/* Save Button */}
              <button
                onClick={handleSaveLayerEdit}
                disabled={layerEditState.saving}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-purple-600 py-2.5 text-xs font-semibold text-white shadow-md hover:bg-purple-500 disabled:opacity-50 transition-colors"
              >
                {layerEditState.saving ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Saving...</span>
                  </>
                ) : (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    <span>Save Layer Settings</span>
                  </>
                )}
              </button>
            </div>
          ) : (
            <div className="py-12 text-center text-xs text-slate-500">
              Select an audio layer from the timeline above to edit volume, timestamps, and fade settings.
            </div>
          )}
        </div>

        {/* Right Column: Audio Asset Library & SFX Suggestions (7 Cols) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Asset Library Container */}
          <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
              <div>
                <h2 className="text-base font-semibold text-white flex items-center gap-2">
                  <FileAudio className="h-4 w-4 text-purple-400" />
                  <span>Audio Asset Library</span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Upload audio files and assign them as BGM beds or SFX cues
                </p>
              </div>

              {/* Upload Input */}
              <div>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept="audio/*,.mp3,.wav,.ogg,.m4a"
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="inline-flex items-center gap-2 rounded-xl bg-slate-800 border border-surface-border px-3.5 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition-colors"
                >
                  {uploading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-400" />
                  ) : (
                    <Upload className="h-3.5 w-3.5 text-purple-400" />
                  )}
                  <span>Upload {assetTab.toUpperCase()}</span>
                </button>
              </div>
            </div>

            {/* Asset Library Tabs: BGM vs SFX */}
            <div className="flex space-x-2 border-b border-surface-border/50 pb-2">
              <button
                onClick={() => setAssetTab('bgm')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  assetTab === 'bgm'
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Music className="h-3.5 w-3.5" />
                <span>Background Music ({assets.filter((a) => a.type === 'bgm').length})</span>
              </button>

              <button
                onClick={() => setAssetTab('sfx')}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  assetTab === 'sfx'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Zap className="h-3.5 w-3.5" />
                <span>Sound Effects ({assets.filter((a) => a.type === 'sfx').length})</span>
              </button>
            </div>

            {/* Assets List */}
            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {filteredAssets.length > 0 ? (
                filteredAssets.map((asset) => (
                  <div
                    key={asset.id}
                    className="rounded-xl border border-surface-border/80 bg-slate-900/60 p-3 flex items-center justify-between gap-3 hover:border-slate-700 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <button
                        onClick={() => handlePlayAssetPreview(asset.id)}
                        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border transition-colors ${
                          activePreviewAssetId === asset.id
                            ? 'bg-purple-600 border-purple-500 text-white'
                            : 'bg-slate-800 border-surface-border text-slate-300 hover:bg-slate-700'
                        }`}
                      >
                        {activePreviewAssetId === asset.id ? (
                          <Pause className="h-3.5 w-3.5" />
                        ) : (
                          <Play className="h-3.5 w-3.5 ml-0.5" />
                        )}
                      </button>

                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-200 truncate">
                          {asset.name}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {asset.duration.toFixed(1)}s • {asset.format.toUpperCase()} • {asset.channels === 1 ? 'Mono' : 'Stereo'}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleAddAssetToTimeline(asset)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-purple-500/30 bg-purple-500/10 px-2.5 py-1 text-xs font-medium text-purple-300 hover:bg-purple-500/20 transition-colors"
                      >
                        <Plus className="h-3.5 w-3.5" />
                        <span>Add to Track</span>
                      </button>
                      <button
                        onClick={() => handleDeleteAsset(asset.id)}
                        className="text-slate-500 hover:text-rose-400 p-1 transition-colors"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-xs text-slate-500">
                  No {assetTab.toUpperCase()} assets found. Click &ldquo;Upload {assetTab.toUpperCase()}&rdquo; to add your own files.
                </div>
              )}
            </div>
          </div>

          {/* Section: Rule-Based SFX Suggestions */}
          <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div>
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-amber-400" />
                  <span>Rule-Based SFX Suggestions</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Contextual recommendations based on Indonesian narration keywords
                </p>
              </div>

              {sfxSuggestions.length === 0 && (
                <button
                  onClick={loadSuggestions}
                  disabled={loadingSuggestions}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs font-semibold text-amber-300 hover:bg-amber-500/20 transition-colors"
                >
                  {loadingSuggestions ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Sparkles className="h-3.5 w-3.5" />
                  )}
                  <span>Scan Suggestions</span>
                </button>
              )}
            </div>

            {sfxSuggestions.length > 0 ? (
              <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
                {sfxSuggestions.map((item) =>
                  item.suggestions.map((sug, sIdx) => (
                    <div
                      key={`${item.scene_id}-${sIdx}`}
                      className="rounded-xl border border-surface-border/60 bg-slate-900/40 p-3 flex items-start justify-between gap-3 text-xs"
                    >
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] font-medium text-amber-300 uppercase">
                            {sug.category}
                          </span>
                          <span className="font-semibold text-slate-200">
                            &ldquo;{sug.keyword}&rdquo;
                          </span>
                          <span className="text-[10px] text-slate-400 font-mono">
                            @ {sug.recommended_position}s
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1">
                          {sug.reason}
                        </p>
                      </div>

                      <button
                        onClick={() => handleApplySuggestion(sug.keyword, sug.recommended_position)}
                        className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-[11px] font-medium text-amber-300 hover:bg-amber-500/20 transition-colors"
                      >
                        <Plus className="h-3 w-3" />
                        <span>Apply Cue</span>
                      </button>
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div className="text-center py-6 text-xs text-slate-500">
                Click &ldquo;Scan Suggestions&rdquo; to analyze narration keywords (e.g. &ldquo;ledakan&rdquo;, &ldquo;kaget&rdquo;, &ldquo;menemukan&rdquo;) for automatic SFX cues.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
