'use client';

import React from 'react';
import { Keyframe } from '@/lib/api/types';
import { getKeyframeImageUrl } from '@/lib/api/client';
import { X, Clock, Award } from 'lucide-react';

interface KeyframeModalProps {
  keyframe: Keyframe | null;
  onClose: () => void;
}

export function KeyframeModal({ keyframe, onClose }: KeyframeModalProps) {
  if (!keyframe) return null;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${mins.toString().padStart(2, '0')}:${secs.padStart(5, '0')}`;
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="relative max-w-3xl w-full rounded-2xl border border-surface-border bg-surface p-6 shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-4 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-md bg-blue-500/10 border border-blue-500/20 px-2.5 py-1 text-xs font-medium text-blue-400">
              <Clock className="h-3.5 w-3.5" />
              {formatTime(keyframe.timestamp)}
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 text-xs font-medium text-emerald-400">
              <Award className="h-3.5 w-3.5" />
              Quality Score: {keyframe.quality_score.toFixed(1)}
            </span>
          </div>

          <button
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-4 overflow-hidden rounded-xl border border-surface-border bg-black flex items-center justify-center">
          <img
            src={getKeyframeImageUrl(keyframe.id)}
            alt={`Keyframe at ${keyframe.timestamp}s`}
            className="max-h-[70vh] w-auto object-contain rounded-lg"
          />
        </div>

        <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
          <span>Keyframe ID: {keyframe.id}</span>
          <span>Relative Storage: {keyframe.image_path}</span>
        </div>
      </div>
    </div>
  );
}
