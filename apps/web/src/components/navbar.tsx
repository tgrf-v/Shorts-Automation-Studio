import React from 'react';
import { Layers, Activity } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-surface-border bg-background/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center space-x-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600/20 text-blue-400 border border-blue-500/30">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <span className="font-semibold tracking-tight text-white">Shorts Automation Studio</span>
            <span className="ml-2 rounded-full border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-xs text-blue-400">
              Milestone 1
            </span>
          </div>
        </div>
        <div className="flex items-center space-x-2 text-xs text-slate-400">
          <Activity className="h-4 w-4 text-emerald-400 animate-pulse" />
          <span>Core Services Ready</span>
        </div>
      </div>
    </header>
  );
};
