"use client";

import { useState, useRef, useEffect } from 'react';

interface UploadCardProps {
  onFileSelect: (file: File | null) => void;
  onQueryChange?: (query: string) => void;
}

export default function UploadCard({ onFileSelect, onQueryChange }: UploadCardProps) {
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [fileSize, setFileSize] = useState<string | null>(null);
  const [query, setQuery] = useState<string>("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Clean up the object URL whenever the file changes or component unmounts to prevent memory leaks
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const formatBytes = (bytes: number, decimals = 1) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  };

  const validateFile = async (file: File): Promise<boolean> => {
    setError(null);

    if (!file.type.startsWith('image/') && !file.type.startsWith('video/')) {
      setError('Only images and videos are allowed');
      return false;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError('File size must be smaller than 10MB');
      return false;
    }

    if (file.type.startsWith('video/')) {
      return new Promise((resolve) => {
        const video = document.createElement('video');
        video.preload = 'metadata';
        video.src = URL.createObjectURL(file);
        
        video.onloadedmetadata = () => {
          URL.revokeObjectURL(video.src);
          if (video.duration > 20) {
            setError('Videos must be 20 seconds or shorter');
            resolve(false);
          } else {
            resolve(true);
          }
        };
        
        video.onerror = () => {
          setError('Invalid video file');
          resolve(false);
        };
      });
    }

    return true;
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const isValid = await validateFile(file);
    if (!isValid) {
      e.target.value = '';
      return;
    }

    // Revoke old preview URL if replacing a file
    if (previewUrl) URL.revokeObjectURL(previewUrl);

    setSelectedFile(file);
    setFileSize(formatBytes(file.size));
    setPreviewUrl(URL.createObjectURL(file));
    
    // Pass raw file up to parent component
    onFileSelect(file);
    
    e.target.value = '';
  };

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    if (onQueryChange) onQueryChange(value);
  };

  const removeSelectedFile = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setSelectedFile(null);
    setFileSize(null);
    setPreviewUrl(null);
    setError(null);
    onFileSelect(null);
  };

  const isVideo = selectedFile?.type.startsWith('video/');

  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-100/50">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Upload Media</h3>
          <p className="text-sm text-slate-500">Select a file to investigate</p>
        </div>
        <div className="rounded-lg bg-slate-50 border border-slate-100 p-2">
          <svg className="h-6 w-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
        </div>
      </div>

      <div className="mt-6">
        {!selectedFile ? (
          /* Empty / Selection Dropzone State */
          <div className="group relative rounded-xl border-2 border-dashed border-slate-200 bg-slate-50/30 p-8 text-center transition-colors hover:border-slate-400/50 hover:bg-slate-50/70">
            <input
              type="file"
              ref={fileInputRef}
              className="absolute inset-0 z-50 h-full w-full cursor-pointer opacity-0"
              accept="image/*,video/*"
              onChange={handleFileChange}
            />
            <div className="space-y-4">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white shadow-sm border border-slate-100">
                <svg className="h-5 w-5 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4" />
                </svg>
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-slate-700">Click to browse or drop file here</p>
                <p className="text-xs text-slate-400">Images or Videos up to 20s (Max 10MB)</p>
              </div>
            </div>
          </div>
        ) : (
          /* File Selected & Preview State */
          <div className="space-y-4">
            {/* Live Interactive Media Preview Window */}
            <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-slate-50 flex items-center justify-center aspect-video w-full group/preview">
              {previewUrl && (
                isVideo ? (
                  <video 
                    src={previewUrl} 
                    className="w-full h-full object-cover" 
                    controls 
                    playsInline
                  />
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img 
                    src={previewUrl} 
                    alt="Preview" 
                    className="w-full h-full object-cover"
                  />
                )
              )}
            </div>

            {/* Info Row & Clear Action Button */}
            <div className="rounded-xl border border-slate-100 bg-slate-50/50 p-3 flex items-center justify-between">
              <div className="flex items-center gap-3 max-w-[80%]">
                <div className="truncate">
                  <p className="text-sm font-medium text-slate-800 truncate">{selectedFile.name}</p>
                  <p className="text-xs text-slate-400">{fileSize} • {selectedFile.type.split('/')[0].toUpperCase()}</p>
                </div>
              </div>

              <button 
                onClick={removeSelectedFile}
                className="text-slate-400 hover:text-red-500 transition-colors p-1"
                type="button"
                title="Remove file"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-4v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Optional Query Text Input */}
        <div className="mt-4">
          <label htmlFor="query-input" className="block text-xs font-medium text-slate-500 mb-1.5">
            What claim are you investigating? <span className="text-slate-400">(optional)</span>
          </label>
          <input
            id="query-input"
            type="text"
            value={query}
            onChange={handleQueryChange}
            placeholder="e.g. Is this image showing a real protest?"
            className="w-full rounded-lg border border-slate-200 bg-slate-50/50 px-3 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-400 transition-all"
          />
        </div>

        {error && (
          <div className="mt-3 rounded-lg bg-red-50 border border-red-100 p-3 text-center">
            <p className="text-xs font-medium text-red-600">{error}</p>
          </div>
        )}
      </div>
    </div>
  );
}