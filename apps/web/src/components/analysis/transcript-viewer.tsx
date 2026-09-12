'use client';

import React from 'react';
import { Transcript } from '@/lib/api/types';
import { FileText, Clock, Globe, Cpu } from 'lucide-react';

interface TranscriptViewerProps {
  transcript: Transcript;
  onSeek?: (timestamp: number) => void;
}

export function TranscriptViewer({ transcript, onSeek }: TranscriptViewerProps) {
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = (seconds % 60).toFixed(2);
    return `${mins.toString().padStart(2, '0')}:${secs.padStart(5, '0')}`;
  };

  return (
    <div className="rounded-2xl border border-surface-border bg-surface/40 p-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400">
            <FileText className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">Extracted Transcript</h3>
            <p className="text-xs text-slate-400">
              High-precision word & sentence alignment for Indonesian adaptation
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 border border-surface-border">
            <Globe className="h-3 w-3 text-slate-400" />
            <span className="uppercase">{transcript.language}</span>
          </span>
          <span className="inline-flex items-center gap-1 rounded-md bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300 border border-surface-border">
            <Cpu className="h-3 w-3 text-slate-400" />
            <span>{transcript.provider}</span>
          </span>
        </div>
      </div>

      {/* Timestamped Segment Stream */}
      <div className="space-y-2.5 max-h-[380px] overflow-y-auto pr-2">
        {transcript.segments && transcript.segments.length > 0 ? (
          transcript.segments.map((seg, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 rounded-xl border border-surface-border/60 bg-surface/70 p-3 hover:border-blue-500/40 hover:bg-surface transition-colors group"
            >
              <button
                type="button"
                onClick={() => onSeek && onSeek(seg.start)}
                className="inline-flex items-center gap-1 rounded-md bg-blue-500/10 border border-blue-500/20 px-2 py-1 text-[11px] font-mono text-blue-400 hover:bg-blue-500 hover:text-white transition-colors shrink-0"
                title="Seek reference video to this timestamp"
              >
                <Clock className="h-3 w-3" />
                <span>{formatTime(seg.start)}</span>
              </button>
              <p className="text-xs leading-relaxed text-slate-300 group-hover:text-white transition-colors">
                {seg.text}
              </p>
            </div>
          ))
        ) : (
          <p className="text-xs text-slate-400 py-4 italic">No spoken dialogue detected in reference audio.</p>
        )}
      </div>
    </div>
  );
}
