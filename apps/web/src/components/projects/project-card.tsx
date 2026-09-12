import React from 'react';
import Link from 'next/link';
import { Project, ProjectStatus } from '@/lib/api/types';
import {
  Folder,
  ArrowRight,
  Clock,
  Trash2,
  CheckCircle2,
  AlertCircle,
  FileVideo,
} from 'lucide-react';


interface ProjectCardProps {
  project: Project;
  onDelete?: (id: string) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({ project, onDelete }) => {
  const renderStatus = (status: ProjectStatus) => {
    switch (status) {
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400">
            <CheckCircle2 className="h-3 w-3" />
            Ready
          </span>
        );
      case 'analyzing':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-xs text-blue-400">
            <Clock className="h-3 w-3 animate-spin" />
            Analyzing
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-xs text-rose-400">
            <AlertCircle className="h-3 w-3" />
            Failed
          </span>
        );
      case 'draft':
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800/80 px-2 py-0.5 text-xs text-slate-300">
            <Clock className="h-3 w-3" />
            Draft
          </span>
        );
    }
  };

  const formattedDate = new Date(project.created_at).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });

  return (
    <div className="group relative flex flex-col justify-between rounded-xl border border-surface-border bg-surface/50 p-5 backdrop-blur-sm transition-all hover:border-slate-700 hover:bg-surface/80">
      <div>
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-slate-900/60 text-blue-400">
              <Folder className="h-5 w-5" />
            </div>

            <div>
              <h3 className="font-medium text-slate-100 group-hover:text-blue-400 transition-colors">
                {project.name}
              </h3>
              <span className="text-xs text-slate-400 flex items-center gap-1 mt-0.5">
                <Clock className="h-3 w-3" />
                {formattedDate}
              </span>
            </div>
          </div>
          {renderStatus(project.status)}
        </div>

        <div className="mt-4 flex items-center gap-2 text-xs text-slate-400">
          <FileVideo className="h-3.5 w-3.5 text-slate-400" />
          <span>
            {project.reference_asset
              ? `Reference: ${project.reference_asset.filename}`
              : 'No reference video uploaded'}
          </span>
        </div>
      </div>

      <div className="mt-6 flex items-center justify-between border-t border-slate-800/80 pt-4">
        {onDelete && (
          <button
            onClick={() => onDelete(project.id)}
            className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-rose-400 transition-colors"
            title="Delete project"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>Delete</span>
          </button>
        )}
        <Link
          href={`/projects/${project.id}`}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg bg-blue-600/10 border border-blue-500/30 px-3 py-1.5 text-xs font-medium text-blue-400 hover:bg-blue-600 hover:text-white transition-all"
        >
          <span>Open</span>
          <ArrowRight className="h-3.5 w-3.5" />
        </Link>
      </div>
    </div>
  );
};
