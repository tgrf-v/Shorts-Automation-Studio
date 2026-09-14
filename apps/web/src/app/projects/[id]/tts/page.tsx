'use client';

import React, { useEffect, useState, use, useCallback } from 'react';
import Link from 'next/link';
import {
  ArrowLeft,
  Volume2,
  Play,
  Pause,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
  Layers,
  ChevronDown,
  Loader2,
  AlertCircle,
  Headphones,
  Check,
  Radio,
  FileText,
  Sliders,
  Film,
  Clapperboard,
  Subtitles,
} from 'lucide-react';
import { getProject } from '@/lib/api/projects';
import { getProjectScripts, getScript } from '@/lib/api/scripts';
import {
  generateTTS,
  getTTSJob,
  getProjectTTSGenerations,
  getTTSGeneration,
  getTTSTimeline,
  activateTTSGeneration,
  getTTSVoices,
  getTTSStreamUrl,
  getSegmentStreamUrl,
} from '@/lib/api/tts';
import {
  Project,
  Script,
  TTSGeneration,
  TTSGenerationSummary,
  TTSJob,
  TTSVoice,
  AudioTimeline,
  AudioSegment,
} from '@/lib/api/types';

interface TTSPageProps {
  params: Promise<{ id: string }>;
}

export default function TTSAudioTimelinePage({ params }: TTSPageProps) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;

  // Core Data
  const [project, setProject] = useState<Project | null>(null);
  const [activeScript, setActiveScript] = useState<Script | null>(null);
  const [generations, setGenerations] = useState<TTSGenerationSummary[]>([]);
  const [selectedGeneration, setSelectedGeneration] = useState<TTSGeneration | null>(null);
  const [timeline, setTimeline] = useState<AudioTimeline | null>(null);
  const [voices, setVoices] = useState<TTSVoice[]>([]);

  // TTS Config Form State
  const [provider, setProvider] = useState<string>('google');
  const [selectedVoice, setSelectedVoice] = useState<string>('id-ID-Standard-A');

  // Generation / Job Polling State
  const [activeJob, setActiveJob] = useState<TTSJob | null>(null);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  // Audio Playback & Interactive Segment
  const [isPlayingFull, setIsPlayingFull] = useState<boolean>(false);
  const [playingSegmentId, setPlayingSegmentId] = useState<string | null>(null);
  const [activeSegmentIndex, setActiveSegmentIndex] = useState<number | null>(null);

  // UI / Action States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // 1. Initial Load
  const fetchData = useCallback(async () => {
    try {
      setError(null);
      const [projData, scriptsData, gensData] = await Promise.all([
        getProject(projectId),
        getProjectScripts(projectId),
        getProjectTTSGenerations(projectId),
      ]);

      setProject(projData);
      setGenerations(gensData);

      // Find active script or latest ready script
      const activeScriptSummary = scriptsData.find((s) => s.is_active) || scriptsData[0];
      if (activeScriptSummary) {
        const fullScript = await getScript(activeScriptSummary.id);
        setActiveScript(fullScript);
      }

      // Find active or latest generation
      const activeGenSummary = gensData.find((g) => g.is_active) || gensData[0];
      if (activeGenSummary) {
        const fullGen = await getTTSGeneration(activeGenSummary.id);
        setSelectedGeneration(fullGen);
        if (fullGen.status === 'completed') {
          const tl = await getTTSTimeline(fullGen.id);
          setTimeline(tl);
        }
      }
    } catch (err) {
      console.error('Failed to load TTS workspace:', err);
      setError(err instanceof Error ? err.message : 'Failed to load TTS workspace.');
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // 2. Fetch voices when provider changes
  useEffect(() => {
    async function loadVoices() {
      try {
        const voiceList = await getTTSVoices(provider);
        setVoices(voiceList);
        if (voiceList.length > 0) {
          // Set default voice based on provider
          if (provider === 'google') {
            const def = voiceList.find((v) => v.id.includes('Standard-A')) || voiceList[0];
            setSelectedVoice(def.id);
          } else if (provider === 'mock') {
            setSelectedVoice(voiceList[0].id);
          } else if (voiceList[0]) {
            setSelectedVoice(voiceList[0].id);
          }
        }
      } catch (err) {
        console.warn('Could not load voice options:', err);
      }
    }
    loadVoices();
  }, [provider]);

  // 3. Job Polling Loop
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'failed') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await getTTSJob(activeJob.id);
        setActiveJob(updated);

        if (updated.status === 'completed') {
          setIsGenerating(false);
          setActionSuccess('Audio narration synthesized and timeline created!');
          // Reload generation and timeline
          const fullGen = await getTTSGeneration(updated.tts_generation_id);
          setSelectedGeneration(fullGen);
          const tl = await getTTSTimeline(fullGen.id);
          setTimeline(tl);
          const gens = await getProjectTTSGenerations(projectId);
          setGenerations(gens);
          setTimeout(() => setActionSuccess(null), 5000);
        } else if (updated.status === 'failed') {
          setIsGenerating(false);
          setError(updated.error || 'TTS generation job failed.');
        }
      } catch (err) {
        console.error('Job polling error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeJob, projectId]);

  // Handler: Start TTS Generation
  const handleGenerate = async () => {
    if (!activeScript) {
      alert('Cannot generate TTS: No active script available.');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setActionSuccess(null);

    try {
      const res = await generateTTS(projectId, {
        script_id: activeScript.id,
        provider,
        voice: selectedVoice,
      });

      const jobData = await getTTSJob(res.job_id);
      setActiveJob(jobData);
    } catch (err) {
      setIsGenerating(false);
      setError(err instanceof Error ? err.message : 'Failed to start TTS generation.');
    }
  };

  // Handler: Select Generation Version
  const handleSelectGeneration = async (genId: string) => {
    try {
      setLoading(true);
      const fullGen = await getTTSGeneration(genId);
      setSelectedGeneration(fullGen);
      if (fullGen.status === 'completed') {
        const tl = await getTTSTimeline(fullGen.id);
        setTimeline(tl);
      } else {
        setTimeline(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch generation.');
    } finally {
      setLoading(false);
    }
  };

  // Handler: Activate Generation
  const handleActivate = async (genId: string) => {
    try {
      await activateTTSGeneration(genId);
      setActionSuccess('Active narration version updated successfully.');
      const gens = await getProjectTTSGenerations(projectId);
      setGenerations(gens);
      if (selectedGeneration?.id === genId) {
        setSelectedGeneration({ ...selectedGeneration, is_active: true });
      }
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to activate generation.');
    }
  };

  if (loading && !project) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center p-8">
        <div className="flex flex-col items-center space-y-3 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin text-purple-500" />
          <span className="text-sm">Loading TTS & Audio Timeline workspace...</span>
        </div>
      </div>
    );
  }

  // Duration calculations
  const sourceDuration = project?.reference_asset?.duration || 0;
  const estimatedDuration = activeScript?.estimated_duration || 0;
  const actualAudioDuration = selectedGeneration?.duration || 0;
  const durationDiff = actualAudioDuration && estimatedDuration ? (actualAudioDuration - estimatedDuration) : null;

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
                TTS & Audio Narration
              </h1>
              <span className="rounded-full border border-purple-500/30 bg-purple-500/10 px-2.5 py-0.5 text-xs text-purple-400">
                Milestone 5
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Project: <span className="text-slate-200 font-medium">{project?.name}</span> • Synthesize narration & build timeline
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Link
            href={`/projects/${projectId}/script`}
            className="inline-flex items-center gap-2 rounded-xl border border-surface-border bg-surface px-3 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <FileText className="h-3.5 w-3.5 text-blue-400" />
            <span>Script Adaptation</span>
          </Link>

          <Link
            href={`/projects/${projectId}/footage`}
            className="inline-flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs font-medium text-amber-300 hover:bg-amber-500/20 hover:text-amber-200 transition-colors"
          >
            <Film className="h-3.5 w-3.5 text-amber-400" />
            <span>Visual Footage (M6)</span>
          </Link>

          <Link
            href={`/projects/${projectId}/timeline`}
            className="inline-flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-300 hover:bg-emerald-500/20 hover:text-emerald-200 transition-colors"
          >
            <Clapperboard className="h-3.5 w-3.5 text-emerald-400" />
            <span>Timeline (M7)</span>
          </Link>

          <Link
            href={`/projects/${projectId}/captions`}
            className="inline-flex items-center gap-2 rounded-xl border border-purple-500/30 bg-purple-500/10 px-3 py-2 text-xs font-medium text-purple-300 hover:bg-purple-500/20 hover:text-purple-200 transition-colors"
          >
            <Subtitles className="h-3.5 w-3.5 text-purple-400" />
            <span>Captions (M8)</span>
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

      {/* Section 1: Active Script Context */}
      <div className="rounded-2xl border border-surface-border bg-surface p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-surface-border/50">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-semibold text-white">
                  {activeScript ? activeScript.title : 'No Active Script'}
                </h2>
                {activeScript && (
                  <span className="rounded-md bg-blue-500/20 px-2 py-0.5 text-[10px] font-semibold text-blue-400 uppercase">
                    v{activeScript.version} (Active)
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-400">
                {activeScript
                  ? `Language: ${activeScript.language.toUpperCase()} • ${activeScript.word_count} words • Estimated duration: ${activeScript.estimated_duration.toFixed(1)}s`
                  : 'Please generate and activate an Indonesian script in Milestone 4 first.'}
              </p>
            </div>
          </div>

          {activeScript && (
            <Link
              href={`/projects/${projectId}/script`}
              className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1 self-start sm:self-auto"
            >
              <span>Edit script</span>
              <ChevronDown className="h-3.5 w-3.5 -rotate-90" />
            </Link>
          )}
        </div>

        {activeScript && (
          <div className="mt-4 bg-slate-900/60 rounded-xl p-4 border border-slate-800/80 text-xs text-slate-300 leading-relaxed max-h-32 overflow-y-auto">
            <p className="whitespace-pre-wrap">{activeScript.content}</p>
          </div>
        )}
      </div>

      {/* Section 2: TTS Configuration & Generate Controls */}
      <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Sliders className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Voice & TTS Settings</h2>
              <p className="text-xs text-slate-400">Select voice engine and speaker voice for narration synthesis</p>
            </div>
          </div>

          <button
            onClick={handleGenerate}
            disabled={isGenerating || !activeScript}
            className="inline-flex items-center gap-2 rounded-xl bg-purple-600 px-5 py-2.5 text-xs font-semibold text-white shadow-lg shadow-purple-600/20 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
          >
            {isGenerating ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Synthesizing Audio...</span>
              </>
            ) : (
              <>
                <Volume2 className="h-4 w-4" />
                <span>Generate Narration</span>
              </>
            )}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Provider Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">TTS Engine Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              disabled={isGenerating}
              className="w-full rounded-xl border border-surface-border bg-slate-900 px-3 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
            >
              <option value="google">Google Cloud Text-to-Speech (Indonesian Standard/WaveNet)</option>
              <option value="elevenlabs">ElevenLabs Multilingual (Ultra-realistic)</option>
              <option value="mock">Mock TTS (Instant / Offline Developer Mode)</option>
            </select>
          </div>

          {/* Voice Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">Speaker Voice</label>
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              disabled={isGenerating}
              className="w-full rounded-xl border border-surface-border bg-slate-900 px-3 py-2.5 text-xs text-white focus:outline-none focus:border-purple-500"
            >
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name} {v.gender ? `(${v.gender})` : ''}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Live Progress Bar when Generating */}
        {isGenerating && activeJob && (
          <div className="rounded-xl border border-purple-500/20 bg-purple-500/5 p-4 space-y-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-purple-300 font-medium flex items-center gap-2">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-purple-400" />
                {activeJob.current_step}
              </span>
              <span className="text-purple-400 font-semibold">{activeJob.progress}%</span>
            </div>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-300 rounded-full"
                style={{ width: `${activeJob.progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Section 3: Narration Preview & Duration Comparison */}
      {selectedGeneration && selectedGeneration.status === 'completed' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Audio Player & Details */}
          <div className="lg:col-span-2 rounded-2xl border border-surface-border bg-surface p-6 space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Headphones className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">Narration Audio Player</h3>
                  <p className="text-xs text-slate-400">
                    Provider: <span className="text-slate-200 capitalize">{selectedGeneration.provider}</span> • Voice: <span className="text-slate-200">{selectedGeneration.voice}</span>
                  </p>
                </div>
              </div>

              {selectedGeneration.is_active ? (
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 text-xs font-semibold text-emerald-400">
                  <Check className="h-3.5 w-3.5" />
                  <span>Active Narration</span>
                </span>
              ) : (
                <button
                  onClick={() => handleActivate(selectedGeneration.id)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-surface-border bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>Set as Active</span>
                </button>
              )}
            </div>

            {/* Audio Element */}
            <div className="bg-slate-900/80 rounded-xl p-4 border border-slate-800">
              <audio
                controls
                className="w-full h-10"
                src={getTTSStreamUrl(selectedGeneration.id)}
                preload="metadata"
              >
                Your browser does not support the audio element.
              </audio>
            </div>

            {/* Technical Specs */}
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-slate-900/40 rounded-xl p-3 border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Duration</span>
                <span className="text-sm font-bold text-white mt-0.5 block">
                  {selectedGeneration.duration ? `${selectedGeneration.duration.toFixed(2)}s` : '—'}
                </span>
              </div>
              <div className="bg-slate-900/40 rounded-xl p-3 border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Sample Rate</span>
                <span className="text-sm font-bold text-white mt-0.5 block">
                  {selectedGeneration.sample_rate ? `${selectedGeneration.sample_rate} Hz` : '44.1 kHz'}
                </span>
              </div>
              <div className="bg-slate-900/40 rounded-xl p-3 border border-slate-800/60">
                <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Format</span>
                <span className="text-sm font-bold text-white mt-0.5 block uppercase">
                  {selectedGeneration.audio_format || 'MP3'}
                </span>
              </div>
            </div>
          </div>

          {/* Duration Validation Card (Section 20) */}
          <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-4">
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-amber-400" />
              <h3 className="text-sm font-semibold text-white">Duration Comparison</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Comparison between the original reference video duration, script estimation, and actual generated narration.
            </p>

            <div className="space-y-3 pt-2">
              <div className="flex justify-between items-center text-xs py-1 border-b border-surface-border/40">
                <span className="text-slate-400">Reference Video:</span>
                <span className="font-semibold text-white">
                  {sourceDuration > 0 ? `${sourceDuration.toFixed(1)}s` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 border-b border-surface-border/40">
                <span className="text-slate-400">Script Estimate:</span>
                <span className="font-semibold text-white">
                  {estimatedDuration > 0 ? `${estimatedDuration.toFixed(1)}s` : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between items-center text-xs py-1 border-b border-surface-border/40">
                <span className="text-slate-400">Actual TTS Narration:</span>
                <span className="font-semibold text-emerald-400">
                  {actualAudioDuration > 0 ? `${actualAudioDuration.toFixed(2)}s` : 'N/A'}
                </span>
              </div>
              {durationDiff !== null && (
                <div className="flex justify-between items-center text-xs py-1 text-amber-300">
                  <span>Difference:</span>
                  <span className="font-medium">
                    {durationDiff > 0 ? `+${durationDiff.toFixed(2)}s` : `${durationDiff.toFixed(2)}s`}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Section 4: Interactive Audio Timeline UI (Section 18 & 19) */}
      {timeline && timeline.segments && timeline.segments.length > 0 && (
        <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                <Layers className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Timestamped Audio Timeline</h3>
                <p className="text-xs text-slate-400">
                  Total timeline: <span className="text-slate-200 font-medium">{timeline.duration.toFixed(2)}s</span> across {timeline.segments.length} scene segments
                </p>
              </div>
            </div>
          </div>

          {/* Timeline Bar visualization */}
          <div className="space-y-2">
            <div className="flex justify-between text-[11px] text-slate-400 font-mono px-1">
              <span>00:00.00</span>
              <span>{timeline.duration.toFixed(2)}s</span>
            </div>

            {/* Segment blocks */}
            <div className="h-14 w-full bg-slate-900 rounded-xl p-1.5 flex gap-1 border border-slate-800 overflow-hidden">
              {timeline.segments.map((seg, idx) => {
                const totalDur = timeline.duration || 1;
                const widthPct = Math.max((seg.duration / totalDur) * 100, 4);
                const isSelected = activeSegmentIndex === idx;

                return (
                  <button
                    key={seg.id}
                    onClick={() => setActiveSegmentIndex(isSelected ? null : idx)}
                    style={{ width: `${widthPct}%` }}
                    className={`h-full rounded-lg transition-all flex flex-col justify-center items-center px-1 text-center relative overflow-hidden group ${
                      isSelected
                        ? 'bg-purple-600 text-white shadow-md shadow-purple-600/30 ring-2 ring-purple-400'
                        : 'bg-slate-800 hover:bg-slate-700 text-slate-300'
                    }`}
                  >
                    <span className="text-[10px] font-bold block truncate w-full">
                      Seg #{seg.sequence}
                    </span>
                    <span className="text-[8px] opacity-75 font-mono block truncate w-full">
                      {seg.duration.toFixed(1)}s
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Detailed Segment Cards / List */}
          <div className="space-y-3 pt-2">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Segment Alignment Breakdown
            </h4>

            <div className="space-y-2.5">
              {timeline.segments.map((seg, idx) => {
                const isSelected = activeSegmentIndex === idx;
                return (
                  <div
                    key={seg.id}
                    onClick={() => setActiveSegmentIndex(idx)}
                    className={`rounded-xl p-4 border transition-all cursor-pointer ${
                      isSelected
                        ? 'border-purple-500/40 bg-purple-500/5'
                        : 'border-surface-border bg-slate-900/40 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-surface-border/40 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="flex h-5 w-5 items-center justify-center rounded-md bg-purple-500/20 text-purple-300 font-bold text-[10px]">
                          {seg.sequence}
                        </span>
                        <span className="font-semibold text-white">Segment #{seg.sequence}</span>
                        {seg.scene_id && (
                          <span className="text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
                            {seg.scene_id}
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
                        <span>
                          {seg.start_time.toFixed(2)}s ──&gt; {seg.end_time.toFixed(2)}s
                        </span>
                        <span className="text-purple-400 font-semibold bg-purple-500/10 px-2 py-0.5 rounded">
                          {seg.duration.toFixed(2)}s
                        </span>
                      </div>
                    </div>

                    <div className="mt-3 flex items-start justify-between gap-4">
                      <p className="text-xs text-slate-300 leading-relaxed italic">
                        &ldquo;{seg.text}&rdquo;
                      </p>

                      {/* Optional Segment Preview Audio */}
                      <audio
                        controls
                        className="h-8 w-44 shrink-0"
                        src={getSegmentStreamUrl(seg.id)}
                        preload="none"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* Section 5: Version History */}
      {generations.length > 0 && (
        <div className="rounded-2xl border border-surface-border bg-surface p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Narration Version History</h3>
            <span className="text-xs text-slate-400">{generations.length} generation(s)</span>
          </div>

          <div className="space-y-2">
            {generations.map((gen) => (
              <div
                key={gen.id}
                onClick={() => handleSelectGeneration(gen.id)}
                className={`flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer text-xs ${
                  selectedGeneration?.id === gen.id
                    ? 'border-purple-500/50 bg-purple-500/10 text-white'
                    : 'border-surface-border bg-slate-900/30 hover:bg-slate-800/50 text-slate-300'
                }`}
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-800 text-purple-400">
                    <Volume2 className="h-3.5 w-3.5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white capitalize">{gen.provider}</span>
                      <span className="text-slate-400">({gen.voice || 'Default'})</span>
                      {gen.is_active && (
                        <span className="rounded bg-emerald-500/20 text-emerald-400 text-[10px] px-1.5 py-0.2 font-semibold">
                          Active
                        </span>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400">
                      {new Date(gen.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="font-mono font-semibold text-slate-200">
                    {gen.duration ? `${gen.duration.toFixed(1)}s` : '—'}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize ${
                      gen.status === 'completed'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : gen.status === 'failed'
                        ? 'bg-rose-500/10 text-rose-400'
                        : 'bg-amber-500/10 text-amber-400'
                    }`}
                  >
                    {gen.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
