'use client';

import React, { useEffect, useState } from 'react';
import { Plus, FolderPlus, Loader2, AlertCircle, RefreshCw, Video } from 'lucide-react';
import { getProjects, deleteProject } from '@/lib/api/projects';
import { Project } from '@/lib/api/types';
import { ProjectCard } from '@/components/projects/project-card';
import { CreateProjectModal } from '@/components/projects/create-project-modal';

export default function HomePage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getProjects();
      setProjects(data.projects || []);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch projects.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleProjectCreated = (newProject: Project) => {
    setIsModalOpen(false);
    setProjects((prev) => [newProject, ...prev]);
  };

  const handleDeleteProject = async (id: string) => {
    if (!confirm('Are you sure you want to delete this project and its assets?')) return;
    try {
      await deleteProject(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete project.');
    }
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 space-y-10">
      {/* Header Banner */}
      <section className="relative overflow-hidden rounded-2xl border border-surface-border bg-gradient-to-b from-surface/80 to-background/90 p-8 backdrop-blur-md">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-3 py-1 text-xs font-medium text-blue-400">
              <Video className="h-3.5 w-3.5" />
              <span>Shorts Automation Studio</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">
              Projects Dashboard
            </h1>
            <p className="text-xs text-slate-400 max-w-xl">
              Manage your reference-based Shorts automation projects. Upload reference videos, inspect
              technical metadata, and prepare for Indonesian adaptation.
            </p>
          </div>

          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-xs font-medium text-white shadow-sm hover:bg-blue-500 transition-colors shrink-0 self-start sm:self-auto"
          >
            <Plus className="h-4 w-4" />
            <span>New Project</span>
          </button>
        </div>
      </section>

      {/* Projects Grid Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Recent Projects</h2>
          <button
            onClick={fetchProjects}
            disabled={loading}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex min-h-[240px] items-center justify-center rounded-xl border border-surface-border bg-surface/30 p-8">
            <div className="flex flex-col items-center space-y-2 text-slate-400">
              <Loader2 className="h-6 w-6 animate-spin text-blue-500" />
              <span className="text-xs">Fetching projects...</span>
            </div>
          </div>
        )}

        {/* Error State */}
        {!loading && error && (
          <div className="rounded-xl border border-rose-500/20 bg-rose-500/10 p-6 text-center">
            <AlertCircle className="mx-auto h-6 w-6 text-rose-400" />
            <h3 className="mt-2 text-sm font-semibold text-white">Unable to load projects</h3>
            <p className="mt-1 text-xs text-slate-400">{error}</p>
            <button
              onClick={fetchProjects}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-medium text-white hover:bg-blue-500 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Try Again</span>
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && projects.length === 0 && (
          <div className="rounded-xl border border-dashed border-slate-700 bg-surface/20 p-12 text-center">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-slate-800 bg-slate-900/60 text-slate-400">
              <FolderPlus className="h-6 w-6" />
            </div>
            <h3 className="mt-4 text-sm font-semibold text-white">No projects created yet</h3>
            <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
              Get started by creating your first Shorts automation project and uploading a reference video.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="mt-5 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-xs font-medium text-white hover:bg-blue-500 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Create First Project</span>
            </button>
          </div>
        )}

        {/* Populated State */}
        {!loading && !error && projects.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <ProjectCard
                key={project.id}
                project={project}
                onDelete={handleDeleteProject}
              />
            ))}
          </div>
        )}
      </section>

      {/* Create Modal */}
      <CreateProjectModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleProjectCreated}
      />
    </div>
  );
}
