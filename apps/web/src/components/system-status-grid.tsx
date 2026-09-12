'use client';

import React, { useEffect, useState } from 'react';
import {
  Server,
  Database,
  Layers,
  Cpu,
  Film,
  HardDrive,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { StatusCard, ServiceHealth } from './status-card';

interface ApiHealthState {
  status: ServiceHealth;
  appEnv: string;
  version: string;
  loading: boolean;
  error: string | null;
}

export const SystemStatusGrid: React.FC = () => {
  const [apiState, setApiState] = useState<ApiHealthState>({
    status: 'pending',
    appEnv: 'unknown',
    version: '0.1.0',
    loading: true,
    error: null,
  });

  const checkApiHealth = async () => {
    setApiState((prev) => ({ ...prev, loading: true, error: null }));
    try {
      const response = await fetch('/api/health');
      if (!response.ok) {
        throw new Error(`HTTP Error: ${response.status}`);
      }
      const data: { status: string; app_env: string; version: string } = await response.json();
      setApiState({
        status: data.status === 'ok' ? 'healthy' : 'unhealthy',
        appEnv: data.app_env || 'development',
        version: data.version || '0.1.0',
        loading: false,
        error: null,
      });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to connect to API';
      setApiState({
        status: 'unhealthy',
        appEnv: 'development',
        version: '0.1.0',
        loading: false,
        error: errorMessage,
      });
    }
  };

  useEffect(() => {
    checkApiHealth();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-white">System Architecture Services</h2>
          <p className="text-xs text-slate-400">
            Current status of foundational containers and modules in the monorepo skeleton.
          </p>
        </div>
        <button
          onClick={checkApiHealth}
          disabled={apiState.loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border bg-surface px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${apiState.loading ? 'animate-spin' : ''}`} />
          <span>Refresh API</span>
        </button>
      </div>

      {apiState.error && (
        <div className="flex items-center gap-3 rounded-lg border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>
            API endpoint unreachable: {apiState.error}. Ensure the FastAPI server is running locally (e.g., via uvicorn or Docker).
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatusCard
          title="Next.js Web"
          category="Frontend Framework"
          status="healthy"
          description="App Router with TypeScript, Tailwind CSS, and Lucide icons."
          icon={Layers}
          endpointOrInfo="http://localhost:3000"
        />

        <StatusCard
          title="FastAPI"
          category="Core API Gateway"
          status={apiState.loading ? 'pending' : apiState.status}
          description={
            apiState.loading
              ? 'Pinging /health endpoint...'
              : `FastAPI service v${apiState.version} running in ${apiState.appEnv} mode.`
          }
          icon={Server}
          endpointOrInfo="http://localhost:8000/health"
        />

        <StatusCard
          title="PostgreSQL"
          category="Relational Database"
          status="pending"
          description="PostgreSQL 16 container for projects, assets, scenes, and transcript persistence."
          icon={Database}
          endpointOrInfo="localhost:5432 / shorts_automation"
        />

        <StatusCard
          title="Redis"
          category="Cache & Queue"
          status="pending"
          description="In-memory data store for background job queues (video, ai, search) and cache."
          icon={Cpu}
          endpointOrInfo="redis://redis:6379/0"
        />

        <StatusCard
          title="Qdrant"
          category="Vector Database"
          status="pending"
          description="Vector search engine for keyframe image embeddings and similarity ranking."
          icon={HardDrive}
          endpointOrInfo="http://localhost:6333"
        />

        <StatusCard
          title="FFmpeg & Worker"
          category="Media Pipeline"
          status="pending"
          description="Python worker container with FFmpeg and FFprobe installed for audio/video composition."
          icon={Film}
          endpointOrInfo="workers/Dockerfile (FFmpeg 6+)"
        />
      </div>
    </div>
  );
};
