'use client';

import React, { useState } from 'react';
import { Scene, Keyframe } from '@/lib/api/types';
import { getKeyframeImageUrl } from '@/lib/api/client';
import { KeyframeModal } from '@/components/analysis/keyframe-modal';
import {
  Film,
  Clock,
  Sparkles,
  Maximize2,
  MessageSquare,
  Award
} from 'lucide-react';

interface SceneListProps {
  scenes: Scene[];
  onSeek?: (timestamp: number) => void;
}

export function SceneList({ scenes, onSeek }: SceneListProps) {
  const [selectedKeyframe, setSelectedKeyframe] = useState<Keyframe | null>(null);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${mins.toString().padStart(2, '0')}:${secs.padStart(5, '0')}`;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Film className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Detected Scenes & Keyframes</h3>
            <p className="text-xs text-slate-400">
              Visual scene cuts with multi-angle keyframe captures and visual descriptions
            </p>
          </div>
        </div>
        <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300 border border-surface-border">
          {scenes.length} Scenes
        </span>
      </div>

      <div className="space-y-4">
        {scenes.map((scene) => (
          <div
            key={scene.id}
            className="rounded-2xl border border-surface-border bg-surface/50 p-5 space-y-4 hover:border-surface-border/90 transition-colors"
          >
            {/* Header: Sequence & Timing */}
            <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-surface-border/50">
              <div className="flex items-center gap-3">
                <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-xs font-bold text-white shadow-sm">
                  #{scene.sequence}
                </span>
                <button
                  type="button"
                  onClick={() => onSeek && onSeek(scene.start_time)}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-surface border border-surface-border px-2.5 py-1 text-xs font-mono text-slate-300 hover:border-blue-500/40 hover:text-white transition-colors"
                  title="Seek video to start of this scene"
                >
                  <Clock className="h-3.5 w-3.5 text-blue-400" />
                  <span>
                    {formatTime(scene.start_time)} &rarr; {formatTime(scene.end_time)}
                  </span>
                  <span className="text-[11px] text-slate-500">({scene.duration.toFixed(1)}s)</span>
                </button>
              </div>

              <span className="text-xs text-slate-400">
                {scene.keyframes?.length || 0} keyframes
              </span>
            </div>

            {/* Keyframes Grid */}
            {scene.keyframes && scene.keyframes.length > 0 && (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {scene.keyframes.map((kf) => (
                  <div
                    key={kf.id}
                    onClick={() => setSelectedKeyframe(kf)}
                    className="group relative cursor-pointer overflow-hidden rounded-xl border border-surface-border bg-black aspect-video hover:border-blue-500/50 transition-all"
                  >
                    <img
                      src={getKeyframeImageUrl(kf.id)}
                      alt={`Keyframe at ${kf.timestamp}s`}
                      className="h-full w-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                      <div className="flex items-center gap-1 text-white text-xs font-medium">
                        <Maximize2 className="h-4 w-4" />
                        <span>Enlarge</span>
                      </div>
                    </div>
                    <div className="absolute bottom-1.5 left-1.5 flex items-center gap-1 rounded bg-black/70 backdrop-blur-sm px-1.5 py-0.5 text-[10px] font-mono text-white">
                      <span>{formatTime(kf.timestamp)}</span>
                    </div>
                    <div className="absolute top-1.5 right-1.5 flex items-center gap-1 rounded bg-black/70 backdrop-blur-sm px-1.5 py-0.5 text-[10px] text-emerald-400">
                      <Award className="h-2.5 w-2.5" />
                      <span>{kf.quality_score.toFixed(0)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Visual Description */}
            <div className="rounded-xl border border-surface-border/50 bg-surface/30 p-3.5 space-y-1.5">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400">
                <Sparkles className="h-3.5 w-3.5" />
                <span>Visual Description</span>
              </div>
              <p className="text-xs leading-relaxed text-slate-300">
                {scene.description || 'Analyzing scene visual elements...'}
              </p>
            </div>

            {/* Spoken Dialogue during this Scene */}
            {scene.transcript_segment && scene.transcript_segment.length > 0 && (
              <div className="rounded-xl border border-surface-border/40 bg-surface/20 p-3.5 space-y-1.5">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-400">
                  <MessageSquare className="h-3.5 w-3.5" />
                  <span>Dialogue in this Scene</span>
                </div>
                <div className="space-y-1">
                  {scene.transcript_segment.map((seg, sIdx) => (
                    <p key={sIdx} className="text-xs text-slate-300 italic">
                      &ldquo;{seg.text}&rdquo;
                    </p>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      <KeyframeModal
        keyframe={selectedKeyframe}
        onClose={() => setSelectedKeyframe(null)}
      />
    </div>
  );
}
