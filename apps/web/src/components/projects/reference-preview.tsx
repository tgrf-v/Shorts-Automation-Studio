import React from 'react';
import { MediaAsset } from '@/lib/api/types';
import { getAssetStreamUrl } from '@/lib/api/client';
import { Clock, Maximize2, Activity, Cpu, HardDrive, FileCheck } from 'lucide-react';

interface ReferencePreviewProps {
  asset: MediaAsset;
}

export const ReferencePreview: React.FC<ReferencePreviewProps> = ({ asset }) => {
  const streamUrl = getAssetStreamUrl(asset.id);

  const formattedSize = (asset.size / (1024 * 1024)).toFixed(2);
  const formattedDuration = asset.duration ? `${asset.duration}s` : 'Probed on analyze';
  const resolution = asset.width && asset.height ? `${asset.width} × ${asset.height}` : 'Probed on analyze';
  const fps = asset.fps ? `${asset.fps} FPS` : 'N/A';
  const codec = asset.codec || 'Auto-detect';

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 rounded-xl border border-surface-border bg-surface/40 p-6 backdrop-blur-sm">
      {/* Video Player Column */}
      <div className="lg:col-span-7 flex flex-col justify-center items-center rounded-lg bg-black/80 border border-slate-800 p-2 overflow-hidden shadow-inner">
        <video
          id="reference-video-player"
          controls
          preload="metadata"
          className="max-h-[480px] w-full rounded object-contain"
          src={streamUrl}
        >
          Your browser does not support HTML5 video preview.
        </video>
      </div>

      {/* Metadata Column */}
      <div className="lg:col-span-5 flex flex-col justify-between space-y-4">
        <div>
          <div className="flex items-center gap-2 pb-3 border-b border-surface-border">
            <FileCheck className="h-4 w-4 text-emerald-400" />
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-300">
              Reference Video Verified
            </span>
          </div>

          <div className="mt-4 space-y-3 text-xs">
            <div className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
              <span className="flex items-center gap-2 text-slate-400">
                <Clock className="h-3.5 w-3.5 text-blue-400" />
                <span>Duration</span>
              </span>
              <span className="font-mono font-medium text-slate-200">{formattedDuration}</span>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
              <span className="flex items-center gap-2 text-slate-400">
                <Maximize2 className="h-3.5 w-3.5 text-blue-400" />
                <span>Resolution</span>
              </span>
              <span className="font-mono font-medium text-slate-200">{resolution}</span>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
              <span className="flex items-center gap-2 text-slate-400">
                <Activity className="h-3.5 w-3.5 text-blue-400" />
                <span>Framerate</span>
              </span>
              <span className="font-mono font-medium text-slate-200">{fps}</span>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
              <span className="flex items-center gap-2 text-slate-400">
                <Cpu className="h-3.5 w-3.5 text-blue-400" />
                <span>Video Codec</span>
              </span>
              <span className="font-mono font-medium text-slate-200 uppercase">{codec}</span>
            </div>

            <div className="flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/40 p-2.5">
              <span className="flex items-center gap-2 text-slate-400">
                <HardDrive className="h-3.5 w-3.5 text-blue-400" />
                <span>File Size</span>
              </span>
              <span className="font-mono font-medium text-slate-200">{formattedSize} MB</span>
            </div>
          </div>
        </div>

        <div className="rounded-lg border border-slate-800 bg-slate-900/30 p-3 text-[11px] text-slate-400 leading-relaxed">
          <span className="font-medium text-slate-300">File:</span> {asset.filename}
        </div>
      </div>
    </div>
  );
};
