'use client';

import React, { useState, useRef } from 'react';
import { UploadCloud, FileVideo, AlertCircle, Loader2 } from 'lucide-react';
import { uploadReferenceVideo } from '@/lib/api/projects';
import { MediaAsset } from '@/lib/api/types';

interface ReferenceUploaderProps {
  projectId: string;
  onUploadSuccess: (asset: MediaAsset) => void;
}

export const ReferenceUploader: React.FC<ReferenceUploaderProps> = ({
  projectId,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState<number>(0);
  const [uploading, setUploading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const asset = await uploadReferenceVideo(projectId, file, (percent) => {
        setProgress(percent);
      });
      setFile(null);
      onUploadSuccess(asset);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Upload failed. Please try again.';
      setError(msg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="rounded-xl border border-dashed border-slate-700 bg-surface/40 p-8 text-center transition-all hover:border-slate-600">
      <input
        ref={inputRef}
        type="file"
        accept=".mp4,.mov,.webm"
        className="hidden"
        onChange={handleFileChange}
        disabled={uploading}
      />

      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-slate-800 bg-slate-900/80 text-blue-400">
        <UploadCloud className="h-7 w-7" />
      </div>

      <h3 className="mt-4 text-base font-semibold text-white">Upload Reference Video</h3>
      <p className="mt-1 text-xs text-slate-400 max-w-sm mx-auto">
        Select an English reference Shorts video to initiate analysis and script adaptation.
      </p>
      <div className="mt-2 text-[11px] text-slate-400">
        Allowed formats: <code className="text-slate-300">.mp4, .mov, .webm</code> (Max 500MB)
      </div>

      {error && (
        <div className="mt-4 mx-auto max-w-md flex items-center gap-2 rounded-lg border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-400 text-left">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {file && (
        <div className="mt-5 mx-auto max-w-md rounded-lg border border-slate-800 bg-slate-900/70 p-3.5 flex items-center justify-between text-left">
          <div className="flex items-center space-x-3 truncate">
            <FileVideo className="h-5 w-5 text-blue-400 shrink-0" />
            <div className="truncate">
              <span className="block text-xs font-medium text-slate-200 truncate">{file.name}</span>
              <span className="text-[11px] text-slate-400">
                {(file.size / (1024 * 1024)).toFixed(2)} MB
              </span>
            </div>
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-medium text-white shadow-sm hover:bg-blue-500 disabled:opacity-50 transition-colors shrink-0"
          >
            {uploading ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>{progress}%</span>
              </>
            ) : (
              <span>Upload Video</span>
            )}
          </button>
        </div>
      )}

      {uploading && (
        <div className="mt-4 mx-auto max-w-md">
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
            <div
              className="h-full bg-blue-500 transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="mt-1.5 block text-[11px] text-slate-400">
            Processing & extracting technical metadata... ({progress}%)
          </span>
        </div>
      )}

      {!file && !uploading && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-5 inline-flex items-center gap-2 rounded-lg border border-surface-border bg-slate-800/80 px-4 py-2 text-xs font-medium text-slate-200 hover:bg-slate-700 transition-colors"
        >
          <FileVideo className="h-4 w-4 text-blue-400" />
          <span>Select Video File</span>
        </button>
      )}
    </div>
  );
};
