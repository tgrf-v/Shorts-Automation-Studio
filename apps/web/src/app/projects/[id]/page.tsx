'use client';

import React, { useEffect, useState, use } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getProject, deleteProject } from '@/lib/api/projects';
import { Project, MediaAsset } from '@/lib/api/types';
import { ReferenceUploader } from '@/components/projects/reference-uploader';
import { ReferencePreview } from '@/components/projects/reference-preview';
import { AnalysisWorkspace } from '@/components/analysis/analysis-workspace';
import {
  ArrowLeft,
  Loader2,
  Trash2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';

interface ProjectPageProps {
  params: Promise<{ id: string }>;
}

export default function ProjectPage({ params }: ProjectPageProps) {
  const resolvedParams = use(params);
  const projectId = resolvedParams.id;
  const router = useRouter();

  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProject = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProject(projectId);
      setProject(data);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to load project details.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProject();
  }, [projectId]);

  const handleUploadSuccess = (newAsset: MediaAsset) => {
    setProject((prev) =>
      prev
        ? {
            ...prev,
            status: 'ready',
            reference_asset_id: newAsset.id,
            reference_asset: newAsset,
          }
        : null
    );
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this project and all its media?')) return;
    try {
      await deleteProject(projectId);
      router.push('/');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete project.');
    }
  };

  if (loading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-7xl items-center justify-center p-8">
        <div className="flex flex-col items-center space-y-3 text-slate-400">
          <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
          <span className="text-sm">Loading project workspace...</span>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <div className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <AlertCircle className="h-6 w-6" />
        </div>
        <h2 className="mt-4 text-lg font-semibold text-white">Failed to load project</h2>
        <p className="mt-1 text-xs text-slate-400">{error || 'Project not found.'}</p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-lg border border-surface-border bg-surface px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to Dashboard</span>
          </Link>
          <button
            onClick={fetchProject}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-500"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Retry</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between pb-6 border-b border-surface-border">
        <div className="flex items-center space-x-4">
          <Link
            href="/"
            className="flex h-9 w-9 items-center justify-center rounded-lg border border-surface-border bg-surface text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-tight text-white sm:text-2xl">
                {project.name}
              </h1>
              <span className="rounded-full border border-blue-500/30 bg-blue-500/10 px-2.5 py-0.5 text-xs text-blue-400 capitalize">
                {project.status}
              </span>
            </div>
            <span className="text-xs text-slate-400">ID: {project.id}</span>
          </div>
        </div>

        <button
          onClick={handleDelete}
          className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-1.5 text-xs font-medium text-rose-400 hover:bg-rose-500 hover:text-white transition-colors self-start sm:self-auto"
        >
          <Trash2 className="h-3.5 w-3.5" />
          <span>Delete Project</span>
        </button>
      </div>

      {/* Reference Video Section */}
      <div className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-white">Reference Video</h2>
          <p className="text-xs text-slate-400">
            Source video used as structural and timing reference for Indonesian script adaptation.
          </p>
        </div>

        {project.reference_asset ? (
          <ReferencePreview asset={project.reference_asset} />
        ) : (
          <ReferenceUploader projectId={project.id} onUploadSuccess={handleUploadSuccess} />
        )}
      </div>

      {/* Analysis Workspace (Milestone 3) */}
      <AnalysisWorkspace
        projectId={project.id}
        hasReference={Boolean(project.reference_asset_id)}
        onStatusChange={fetchProject}
      />
    </div>
  );
}
