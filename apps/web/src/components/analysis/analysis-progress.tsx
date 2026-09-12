'use client';

import React from 'react';
import { AnalysisJob } from '@/lib/api/types';
import {
  Loader2,
  Mic,
  Film,
  Camera,
  Sparkles,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';

interface AnalysisProgressProps {
  job: AnalysisJob;
}

const STEP_LABELS: Record<string, { label: string; icon: React.ElementType }> = {
  initializing: { label: 'Initializing analysis environment...', icon: Loader2 },
  extracting_audio: { label: 'Extracting 16kHz PCM audio stream...', icon: Mic },
  transcribing: { label: 'Transcribing speech with timestamp alignment...', icon: Mic },
  detecting_scenes: { label: 'Detecting visual scene cut boundaries...', icon: Film },
  extracting_keyframes: { label: 'Extracting keyframes & computing quality scores...', icon: Camera },
  describing_scenes: { label: 'Generating visual scene descriptions...', icon: Sparkles },
  finalizing: { label: 'Finalizing and persisting analysis records...', icon: CheckCircle2 },
};

export function AnalysisProgress({ job }: AnalysisProgressProps) {
  const currentConfig = STEP_LABELS[job.current_step] || {
    label: `Processing step: ${job.current_step}...`,
    icon: Loader2,
  };
  const StepIcon = currentConfig.icon;

  return (
    <div className="rounded-2xl border border-blue-500/20 bg-blue-950/20 p-6 shadow-sm">
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <StepIcon className="h-5 w-5 animate-spin" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Analyzing Reference Video</h3>
              <p className="text-xs text-slate-400">{currentConfig.label}</p>
            </div>
          </div>

          <div className="text-right">
            <span className="text-lg font-bold text-blue-400">{job.progress}%</span>
            <p className="text-[10px] text-slate-400 uppercase tracking-wider">Completed</p>
          </div>
        </div>

        {/* Progress Bar Track */}
        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-gradient-to-r from-blue-600 to-indigo-500 transition-all duration-500 ease-out"
            style={{ width: `${Math.max(job.progress, 5)}%` }}
          />
        </div>

        {/* Pipeline Step Indicators */}
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 pt-2 border-t border-surface-border/50 text-[11px]">
          {[
            { key: 'extracting_audio', name: 'Audio' },
            { key: 'transcribing', name: 'Transcript' },
            { key: 'detecting_scenes', name: 'Scenes' },
            { key: 'extracting_keyframes', name: 'Keyframes' },
            { key: 'describing_scenes', name: 'Vision' },
            { key: 'finalizing', name: 'Saved' },
          ].map((item) => (
            <div
              key={item.key}
              className="flex items-center gap-1.5 rounded-lg bg-surface/60 px-2.5 py-1.5 border border-surface-border"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-blue-500" />
              <span className="text-slate-300 truncate">{item.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
