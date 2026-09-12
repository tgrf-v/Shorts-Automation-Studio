import React from 'react';
import { ArrowRight, Code2, Terminal, ShieldCheck, Video } from 'lucide-react';
import { SystemStatusGrid } from '@/components/system-status-grid';

export default function HomePage() {
  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-10">
      {/* Hero Section */}
      <section className="relative overflow-hidden rounded-2xl border border-surface-border bg-gradient-to-b from-surface/80 to-background/90 p-8 sm:p-10 backdrop-blur-md">
        <div className="max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400">
            <Video className="h-3.5 w-3.5" />
            <span>Automated Shorts Production Engine</span>
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Shorts Automation Studio
          </h1>
          <p className="text-sm leading-relaxed text-slate-300 sm:text-base">
            Turn viral reference Shorts into structured Indonesian drafts automatically: transcription,
            script adaptation, voice generation, scene segmentation, and video composition.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <div className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white shadow-sm">
              <span>Skeleton Ready</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </div>
            <div className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border bg-surface/50 px-3 py-2 text-xs font-mono text-slate-300">
              <Terminal className="h-3.5 w-3.5 text-blue-400" />
              <span>docker compose up --build</span>
            </div>
          </div>
        </div>
      </section>

      {/* Services Grid */}
      <section>
        <SystemStatusGrid />
      </section>

      {/* Architecture Highlights */}
      <section className="rounded-xl border border-surface-border bg-surface/30 p-6 backdrop-blur-sm">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Monorepo Architecture
        </h3>
        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-3 text-xs text-slate-300">
          <div className="flex items-start gap-3 rounded-lg border border-slate-800/60 bg-slate-900/40 p-3.5">
            <Code2 className="h-4 w-4 text-blue-400 shrink-0 mt-0.5" />
            <div>
              <strong className="block text-slate-200">Layered FastAPI Backend</strong>
              <span>Clean separation of routes, services, schemas, repositories, and providers.</span>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-lg border border-slate-800/60 bg-slate-900/40 p-3.5">
            <Terminal className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
            <div>
              <strong className="block text-slate-200">FFmpeg Worker Pipelines</strong>
              <span>Dedicated worker environment for heavy video transcoding, scene splitting, and audio mixing.</span>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-lg border border-slate-800/60 bg-slate-900/40 p-3.5">
            <ShieldCheck className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong className="block text-slate-200">Human-In-The-Loop Control</strong>
              <span>Automates repetitive workflow while retaining creator control over script, scenes, and footage.</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
