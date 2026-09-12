import React from 'react';
import { CheckCircle2, AlertTriangle, Clock, LucideIcon } from 'lucide-react';

export type ServiceHealth = 'healthy' | 'unhealthy' | 'pending';

export interface StatusCardProps {
  title: string;
  category: string;
  status: ServiceHealth;
  description: string;
  icon: LucideIcon;
  endpointOrInfo?: string;
}

export const StatusCard: React.FC<StatusCardProps> = ({
  title,
  category,
  status,
  description,
  icon: Icon,
  endpointOrInfo,
}) => {
  const getStatusBadge = () => {
    switch (status) {
      case 'healthy':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400">
            <CheckCircle2 className="h-3 w-3" />
            Healthy
          </span>
        );
      case 'unhealthy':
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-rose-500/30 bg-rose-500/10 px-2 py-0.5 text-xs font-medium text-rose-400">
            <AlertTriangle className="h-3 w-3" />
            Offline
          </span>
        );
      case 'pending':
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-xs font-medium text-amber-400">
            <Clock className="h-3 w-3" />
            Configured
          </span>
        );
    }
  };

  return (
    <div className="group relative rounded-xl border border-surface-border bg-surface/50 p-5 backdrop-blur-sm transition-all duration-200 hover:border-slate-700 hover:bg-surface/80">
      <div className="flex items-start justify-between">
        <div className="flex items-center space-x-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-800 bg-slate-900/60 text-slate-300 group-hover:text-blue-400">
            <Icon className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-medium text-slate-200">{title}</h3>
            <span className="text-xs text-slate-400">{category}</span>
          </div>
        </div>
        {getStatusBadge()}
      </div>
      <p className="mt-4 text-xs leading-relaxed text-slate-400">{description}</p>
      {endpointOrInfo && (
        <div className="mt-3 flex items-center justify-between border-t border-slate-800/80 pt-3 text-[11px] text-slate-400">
          <span>Target / Endpoint:</span>
          <code className="rounded bg-slate-900 px-1.5 py-0.5 font-mono text-slate-300">
            {endpointOrInfo}
          </code>
        </div>
      )}
    </div>
  );
};
