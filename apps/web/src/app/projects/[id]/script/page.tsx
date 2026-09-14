'use client';

import React, { useEffect, useState, use, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  Sparkles,
  RefreshCw,
  Save,
  CheckCircle2,
  AlertTriangle,
  Clock,
  FileText,
  Layers,
  ChevronDown,
  Loader2,
  AlertCircle,
  ExternalLink,
} from 'lucide-react';
import { getProject } from '@/lib/api/projects';
import { getProjectAnalysis } from '@/lib/api/analysis';
import {
  getProjectScripts,
  getScript,
  generateScript,
  getScriptJob,
  updateScript,
  activateScript,
} from '@/lib/api/scripts';
import {
  Project,
  ProjectAnalysisResponse,
  Script,
  ScriptSummary,
  ScriptJob,
  ScriptSegment,
} from '@/lib/api/types';

interface ScriptPageProps {
  params: Promise<{ id: string }>;
}

export default function ScriptAdaptationPage({ params }: ScriptPageProps) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const router = useRouter();

  // Core Data
  const [project, setProject] = useState<Project | null>(null);
  const [analysis, setAnalysis] = useState<ProjectAnalysisResponse | null>(null);
  const [scripts, setScripts] = useState<ScriptSummary[]>([]);
  const [currentScript, setCurrentScript] = useState<Script | null>(null);

  // Loading & Action States
  const [initialLoading, setInitialLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);
  const [activating, setActivating] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // Generator Dialog / Options State
  const [isGenerateModalOpen, setIsGenerateModalOpen] = useState<boolean>(false);
  const [generateProvider, setGenerateProvider] = useState<string>('gemini');
  const [generateInstructions, setGenerateInstructions] = useState<string>('');
  const [isTriggering, setIsTriggering] = useState<boolean>(false);

  // Active Job Polling
  const [activeJob, setActiveJob] = useState<ScriptJob | null>(null);

  // Form Edit State for Current Script
  const [editedTitle, setEditedTitle] = useState<string>('');
  const [editedContent, setEditedContent] = useState<string>('');
  const [editedSegments, setEditedSegments] = useState<ScriptSegment[]>([]);

  // Fetch all project info & scripts
  const loadInitialData = useCallback(async () => {
    setInitialLoading(true);
    setError(null);
    try {
      const [projData, analysisData, scriptsData] = await Promise.all([
        getProject(projectId),
        getProjectAnalysis(projectId),
        getProjectScripts(projectId),
      ]);

      setProject(projData);
      setAnalysis(analysisData);
      setScripts(scriptsData);

      // Select active script or most recent version
      if (scriptsData.length > 0) {
        const activeOrRecent = scriptsData.find((s) => s.is_active) || scriptsData[0];
        const scriptDetail = await getScript(activeOrRecent.id);
        setCurrentScript(scriptDetail);
        setEditedTitle(scriptDetail.title);
        setEditedContent(scriptDetail.content);
        setEditedSegments(scriptDetail.segments || []);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load script workspace.';
      setError(msg);
    } finally {
      setInitialLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Polling loop for active script generation job
  useEffect(() => {
    if (!activeJob) return;

    const interval = setInterval(async () => {
      try {
        const updatedJob = await getScriptJob(activeJob.id);
        setActiveJob(updatedJob);

        if (updatedJob.status === 'completed') {
          clearInterval(interval);
          setActiveJob(null);
          // Reload scripts list & select the generated script
          const updatedList = await getProjectScripts(projectId);
          setScripts(updatedList);
          const newScript = await getScript(updatedJob.script_id);
          setCurrentScript(newScript);
          setEditedTitle(newScript.title);
          setEditedContent(newScript.content);
          setEditedSegments(newScript.segments || []);
        } else if (updatedJob.status === 'failed') {
          clearInterval(interval);
          setActiveJob(null);
          setError(updatedJob.error || 'Script generation failed.');
          const updatedList = await getProjectScripts(projectId);
          setScripts(updatedList);
        }
      } catch (pollErr) {
        console.warn('Script job polling error:', pollErr);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [activeJob, projectId]);

  // Switch displayed version
  const handleSelectVersion = async (scriptId: string) => {
    try {
      const detail = await getScript(scriptId);
      setCurrentScript(detail);
      setEditedTitle(detail.title);
      setEditedContent(detail.content);
      setEditedSegments(detail.segments || []);
      setSaveSuccess(false);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to load script version.');
    }
  };

  // Trigger script generation
  const handleTriggerGenerate = async () => {
    setIsTriggering(true);
    setError(null);
    try {
      const res = await generateScript(projectId, {
        provider: generateProvider,
        instructions: generateInstructions.trim() || undefined,
      });

      setIsGenerateModalOpen(false);
      setGenerateInstructions('');

      // Set active job for polling
      const job = await getScriptJob(res.job_id);
      setActiveJob(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start script generation.');
    } finally {
      setIsTriggering(false);
    }
  };

  // Manual save changes (PATCH)
  const handleSaveChanges = async () => {
    if (!currentScript) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await updateScript(currentScript.id, {
        title: editedTitle,
        content: editedContent,
        segments: editedSegments,
      });
      setCurrentScript(updated);
      setEditedTitle(updated.title);
      setEditedContent(updated.content);
      setEditedSegments(updated.segments || []);

      // Update in versions list
      setScripts((prev) =>
        prev.map((s) => (s.id === updated.id ? { ...s, title: updated.title, word_count: updated.word_count, estimated_duration: updated.estimated_duration } : s))
      );

      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save script changes.');
    } finally {
      setSaving(false);
    }
  };

  // Set as Active
  const handleActivateVersion = async () => {
    if (!currentScript || currentScript.is_active) return;
    setActivating(true);
    try {
      const activated = await activateScript(currentScript.id);
      setCurrentScript(activated);
      setScripts((prev) =>
        prev.map((s) => ({
          ...s,
          is_active: s.id === activated.id,
        }))
      );
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to activate script version.');
    } finally {
      setActivating(false);
    }
  };

  // Live Segment Text Editing
  const handleSegmentChange = (index: number, newText: string) => {
    setEditedSegments((prev) => {
      const copy = [...prev];
      copy[index] = { ...copy[index], adapted_text: newText };
      return copy;
    });

    // Also update full content to stay in sync
    setTimeout(() => {
      setEditedContent((prev) => {
        const words = editedSegments.map((s, i) => (i === index ? newText : s.adapted_text));
        return words.join(' ');
      });
    }, 0);
  };

  // Computed Real-time Metrics
  const liveWordCount = editedContent.trim() ? editedContent.trim().split(/\s+/).length : 0;
  const liveEstimatedDuration = Math.round((liveWordCount / 150) * 60 * 10) / 10;
  const sourceDuration = currentScript?.source_duration || (analysis?.scenes?.length ? analysis.scenes[analysis.scenes.length - 1].end_time : 0);
  const durationDiff = sourceDuration > 0 ? Math.round(((liveEstimatedDuration - sourceDuration) / sourceDuration) * 1000) / 10 : 0;
  const isWithinTolerance = sourceDuration > 0 ? liveEstimatedDuration / sourceDuration >= 0.85 && liveEstimatedDuration / sourceDuration <= 1.15 : true;

  if (initialLoading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center p-8">
        <div className="flex flex-col items-center space-y-3 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <span className="text-sm">Loading Script Adaptation Workspace...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Top Header */}
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
                Script Adaptation
              </h1>
              <span className="rounded-full border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-0.5 text-xs text-indigo-400 font-medium">
                Bahasa Indonesia
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Project: <span className="text-slate-200">{project?.name}</span>
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => setIsGenerateModalOpen(true)}
            disabled={isTriggering || Boolean(activeJob)}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-xs font-semibold text-white shadow-md shadow-blue-600/20 hover:bg-blue-500 transition-all disabled:opacity-50"
          >
            <Sparkles className="h-4 w-4" />
            <span>{scripts.length === 0 ? 'Generate Script' : 'Regenerate New Version'}</span>
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-rose-500/20 bg-rose-500/10 p-4 text-rose-400 text-xs">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            className="rounded bg-rose-500/20 px-2.5 py-1 text-[11px] font-medium hover:bg-rose-500/30"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Background Processing Progress Bar */}
      {activeJob && (
        <div className="rounded-2xl border border-blue-500/30 bg-blue-500/10 p-6 space-y-4 backdrop-blur-md">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-blue-400" />
              <div>
                <h4 className="text-sm font-semibold text-white">Generating Indonesian Script...</h4>
                <p className="text-xs text-blue-300">{activeJob.current_step}</p>
              </div>
            </div>
            <span className="text-xs font-mono font-bold text-blue-400">{activeJob.progress}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-blue-950">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-500"
              style={{ width: `${Math.max(5, activeJob.progress)}%` }}
            />
          </div>
        </div>
      )}

      {/* Empty State when no script exists */}
      {!activeJob && scripts.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-700 bg-surface/30 p-12 text-center space-y-4">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <FileText className="h-6 w-6" />
          </div>
          <div className="space-y-1 max-w-md mx-auto">
            <h3 className="text-base font-semibold text-white">No Indonesian Script Generated Yet</h3>
            <p className="text-xs text-slate-400">
              Transform the reference video transcript into natural, high-retention Indonesian narration
              aligned with the detected scenes.
            </p>
          </div>
          <button
            onClick={() => setIsGenerateModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2.5 text-xs font-semibold text-white hover:bg-blue-500 transition-colors shadow-lg shadow-blue-600/20"
          >
            <Sparkles className="h-4 w-4" />
            <span>Generate First Indonesian Script</span>
          </button>
        </div>
      )}

      {/* Main Workspace (When Script Exists) */}
      {currentScript && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Column: Reference Source Info */}
          <div className="lg:col-span-4 space-y-6">
            <div className="rounded-2xl border border-surface-border bg-surface/50 p-5 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
                  <Layers className="h-4 w-4 text-blue-400" />
                  <span>Reference Source Context</span>
                </div>
                <span className="rounded bg-slate-800 px-2 py-0.5 text-[11px] text-slate-400">
                  {analysis?.scenes?.length || 0} Scenes
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="rounded-xl border border-surface-border/60 bg-surface/30 p-3 space-y-1">
                  <span className="text-[11px] text-slate-400">Source Duration</span>
                  <p className="font-mono font-bold text-white">
                    {sourceDuration ? `${sourceDuration.toFixed(1)}s` : 'N/A'}
                  </p>
                </div>
                <div className="rounded-xl border border-surface-border/60 bg-surface/30 p-3 space-y-1">
                  <span className="text-[11px] text-slate-400">Target WPM</span>
                  <p className="font-mono font-bold text-white">150 WPM</p>
                </div>
              </div>

              {/* Transcript Accordion / Box */}
              <div className="space-y-2 pt-2">
                <span className="text-xs font-semibold text-slate-300">Original Transcript</span>
                <div className="max-h-[360px] overflow-y-auto rounded-xl border border-surface-border/50 bg-black/40 p-3.5 space-y-3 font-mono text-xs leading-relaxed text-slate-300 scrollbar-thin">
                  {analysis?.transcript?.segments && analysis.transcript.segments.length > 0 ? (
                    analysis.transcript.segments.map((seg, idx) => (
                      <div key={idx} className="space-y-0.5">
                        <span className="text-[10px] text-blue-400">
                          [{seg.start.toFixed(1)}s - {seg.end.toFixed(1)}s]
                        </span>
                        <p className="text-slate-300">{seg.text}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-slate-400 text-xs italic">
                      {analysis?.transcript?.content || 'No transcript available.'}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* Versions List Card */}
            <div className="rounded-2xl border border-surface-border bg-surface/50 p-5 space-y-3">
              <span className="text-xs font-semibold text-slate-300">Script Versions</span>
              <div className="space-y-2">
                {scripts.map((v) => (
                  <button
                    key={v.id}
                    onClick={() => handleSelectVersion(v.id)}
                    className={`w-full flex items-center justify-between p-3 rounded-xl border text-left text-xs transition-all ${
                      v.id === currentScript.id
                        ? 'border-blue-500 bg-blue-500/10 text-white'
                        : 'border-surface-border bg-surface/30 text-slate-400 hover:border-slate-700 hover:text-white'
                    }`}
                  >
                    <div className="space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold">Version {v.version}</span>
                        {v.is_active && (
                          <span className="rounded bg-emerald-500/20 text-emerald-400 px-1.5 py-0.5 text-[10px] font-medium border border-emerald-500/30">
                            Active
                          </span>
                        )}
                        {v.is_manually_edited && (
                          <span className="rounded bg-amber-500/20 text-amber-400 px-1.5 py-0.5 text-[10px] font-medium border border-amber-500/30">
                            Edited
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 truncate max-w-[200px]">{v.title}</p>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400">~{v.estimated_duration.toFixed(0)}s</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Right Column: Indonesian Script Editor */}
          <div className="lg:col-span-8 space-y-6">
            {/* Top Toolbar / Metrics */}
            <div className="rounded-2xl border border-surface-border bg-surface/60 p-5 space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-surface-border">
                <div className="flex items-center gap-3">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white">
                    v{currentScript.version}
                  </span>
                  <div>
                    <h3 className="text-sm font-bold text-white">Indonesian Script Editor</h3>
                    <span className="text-[11px] text-slate-400">
                      Provider: <span className="text-slate-300 capitalize">{currentScript.generation_provider}</span>
                      {currentScript.generation_model && (
                        <span className="text-slate-400 ml-1.5 font-mono">({currentScript.generation_model})</span>
                      )}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {!currentScript.is_active && (
                    <button
                      onClick={handleActivateVersion}
                      disabled={activating}
                      className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs font-medium text-emerald-400 hover:bg-emerald-500 hover:text-white transition-colors disabled:opacity-50"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>{activating ? 'Activating...' : 'Set as Active'}</span>
                    </button>
                  )}
                  <button
                    onClick={handleSaveChanges}
                    disabled={saving}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50"
                  >
                    <Save className="h-3.5 w-3.5" />
                    <span>{saving ? 'Saving...' : saveSuccess ? 'Saved!' : 'Save Changes'}</span>
                  </button>
                </div>
              </div>

              {/* Real-time Duration Analysis Bar */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="rounded-xl border border-surface-border bg-surface/40 p-3">
                  <span className="text-[11px] text-slate-400">Word Count</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">{liveWordCount} words</p>
                </div>

                <div className="rounded-xl border border-surface-border bg-surface/40 p-3">
                  <span className="text-[11px] text-slate-400">Estimated Duration</span>
                  <p className="text-sm font-bold font-mono text-white mt-0.5">~{liveEstimatedDuration}s</p>
                </div>

                <div className="rounded-xl border border-surface-border bg-surface/40 p-3">
                  <span className="text-[11px] text-slate-400">Source Duration</span>
                  <p className="text-sm font-bold font-mono text-slate-300 mt-0.5">{sourceDuration ? `${sourceDuration.toFixed(1)}s` : 'N/A'}</p>
                </div>

                <div className={`rounded-xl border p-3 ${
                  isWithinTolerance
                    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
                    : 'border-amber-500/30 bg-amber-500/10 text-amber-400'
                }`}>
                  <div className="flex items-center justify-between">
                    <span className="text-[11px]">Diff vs Source</span>
                    {!isWithinTolerance && <AlertTriangle className="h-3 w-3" />}
                  </div>
                  <p className="text-sm font-bold font-mono mt-0.5">
                    {durationDiff > 0 ? `+${durationDiff}%` : `${durationDiff}%`}
                  </p>
                </div>
              </div>

              {/* Warning Banner if significantly off */}
              {!isWithinTolerance && (
                <div className="flex items-center gap-2 rounded-xl border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-400">
                  <AlertTriangle className="h-4 w-4 shrink-0" />
                  <span>
                    Script narration duration is {durationDiff > 0 ? 'longer' : 'shorter'} than the recommended 85%-115% ratio. Consider adjusting text length.
                  </span>
                </div>
              )}

              {/* Editable Title */}
              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-semibold text-slate-300">Shorts Title (Indonesian)</label>
                <input
                  type="text"
                  value={editedTitle}
                  onChange={(e) => setEditedTitle(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-black/40 px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  placeholder="Enter video title..."
                />
              </div>

              {/* Editable Full Script */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-300">Full Combined Script</label>
                <textarea
                  rows={4}
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-black/40 p-3.5 text-xs text-white leading-relaxed placeholder-slate-500 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y"
                  placeholder="Full Indonesian narration..."
                />
              </div>
            </div>

            {/* Scene-Aligned Breakdown Cards */}
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2">
                <div>
                  <h4 className="text-sm font-semibold text-white">Scene-Aligned Script Breakdown</h4>
                  <p className="text-xs text-slate-400">
                    Each segment maps directly to a detected video scene for downstream TTS and footage timing
                  </p>
                </div>
                <span className="text-xs text-slate-400 font-mono">
                  {editedSegments.length} Segments
                </span>
              </div>

              <div className="space-y-3">
                {editedSegments.map((seg, idx) => (
                  <div
                    key={seg.scene_id || idx}
                    className="rounded-2xl border border-surface-border bg-surface/50 p-4 space-y-3 hover:border-slate-700 transition-colors"
                  >
                    {/* Scene Timing & Metadata Header */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2.5 border-b border-surface-border/50 text-xs">
                      <div className="flex items-center gap-2.5">
                        <span className="flex h-6 w-6 items-center justify-center rounded-md bg-blue-600 text-[11px] font-bold text-white">
                          #{seg.sequence}
                        </span>
                        <div className="flex items-center gap-1.5 font-mono text-slate-300">
                          <Clock className="h-3 w-3 text-blue-400" />
                          <span>
                            {seg.start_time.toFixed(1)}s &rarr; {seg.end_time.toFixed(1)}s
                          </span>
                          <span className="text-[11px] text-slate-500">({seg.duration.toFixed(1)}s)</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 text-[11px] text-slate-400">
                        <span>~{Math.round((seg.adapted_text.split(/\s+/).filter(Boolean).length / 150) * 60 * 10) / 10}s spoken</span>
                      </div>
                    </div>

                    {/* Original Dialogue & Visual context */}
                    {(seg.source_text || seg.visual_description) && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] bg-black/30 rounded-xl p-2.5 border border-surface-border/40">
                        {seg.source_text && (
                          <div>
                            <span className="text-slate-500 font-semibold">Original: </span>
                            <span className="text-slate-300 italic">&ldquo;{seg.source_text}&rdquo;</span>
                          </div>
                        )}
                        {seg.visual_description && (
                          <div>
                            <span className="text-slate-500 font-semibold">Visual: </span>
                            <span className="text-slate-400">{seg.visual_description}</span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Editable Adapted Narration for this scene */}
                    <div className="space-y-1">
                      <label className="text-[11px] font-medium text-slate-400">Adapted Narration (Bahasa Indonesia)</label>
                      <textarea
                        rows={2}
                        value={seg.adapted_text}
                        onChange={(e) => handleSegmentChange(idx, e.target.value)}
                        className="w-full rounded-xl border border-surface-border bg-black/50 p-2.5 text-xs text-white placeholder-slate-600 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 resize-y"
                        placeholder="Adapted narration for this scene..."
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Generate / Regenerate Modal */}
      {isGenerateModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg rounded-2xl border border-surface-border bg-surface p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-surface-border">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
                  <Sparkles className="h-4 w-4" />
                </div>
                <h3 className="text-base font-bold text-white">Generate Indonesian Script</h3>
              </div>
              <button
                onClick={() => setIsGenerateModalOpen(false)}
                className="text-slate-400 hover:text-white text-xs"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="space-y-1.5">
                <label className="font-semibold text-slate-300">AI Provider</label>
                <select
                  value={generateProvider}
                  onChange={(e) => setGenerateProvider(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-black/40 px-3.5 py-2.5 text-xs text-white focus:border-blue-500 focus:outline-none"
                >
                  <option value="gemini">Google Gemini (Default)</option>
                  <option value="openai">OpenAI GPT-4o-mini</option>
                  <option value="mock">Mock Provider (Deterministic Offline)</option>
                </select>
                <p className="text-[11px] text-slate-500">
                  If API credentials are not set, it will automatically fallback to the Mock provider.
                </p>
              </div>

              <div className="space-y-1.5">
                <label className="font-semibold text-slate-300">Custom Style / Tone Instructions (Optional)</label>
                <textarea
                  rows={3}
                  value={generateInstructions}
                  onChange={(e) => setGenerateInstructions(e.target.value)}
                  className="w-full rounded-xl border border-surface-border bg-black/40 p-3 text-xs text-white placeholder-slate-500 focus:border-blue-500 focus:outline-none resize-none"
                  placeholder="e.g. Lebih santai dan humoris, fokuskan hook pada kalimat pertama..."
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button
                onClick={() => setIsGenerateModalOpen(false)}
                className="rounded-xl border border-surface-border bg-surface/50 px-4 py-2 text-xs text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleTriggerGenerate}
                disabled={isTriggering}
                className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-5 py-2 text-xs font-semibold text-white hover:bg-blue-500 transition-colors disabled:opacity-50"
              >
                <Sparkles className="h-3.5 w-3.5" />
                <span>{isTriggering ? 'Queuing...' : 'Start Generation'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
