"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Film, Upload, X } from "lucide-react";

interface VideoUploadProps {
  onAnalyze: (file: File) => void;
  isLoading: boolean;
}

export function VideoUpload({ onAnalyze, isLoading }: VideoUploadProps) {
  const [file, setFile] = useState<File | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const selected = acceptedFiles[0];
    if (selected) {
      setFile(selected);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "video/mp4": [".mp4"],
      "video/webm": [".webm"],
      "video/quicktime": [".mov"],
      "video/x-msvideo": [".avi"],
      "video/x-matroska": [".mkv"],
    },
    maxSize: 150 * 1024 * 1024,
    multiple: false,
    disabled: isLoading,
  });

  function clear() {
    setFile(null);
  }

  return (
    <div className="space-y-4">
      {!file ? (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
            isDragActive
              ? "border-blue-500 bg-blue-500/5"
              : "border-gray-700 hover:border-gray-500 bg-gray-900"
          }`}
        >
          <input {...getInputProps()} aria-label="Upload video file for AI detection" />
          <Upload className="h-10 w-10 text-gray-500 mx-auto mb-4" aria-hidden="true" />
          <p className="text-gray-300 font-medium">
            {isDragActive ? "Drop video here..." : "Drag & drop a video, or click to upload"}
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Supports MP4, WebM, MOV, AVI, MKV &middot; Max 150 MB
          </p>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 rounded-lg bg-gray-800 flex items-center justify-center flex-shrink-0">
              <Film className="h-7 w-7 text-blue-300" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Film className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-200 truncate">{file.name}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {(file.size / 1024 / 1024).toFixed(2)} MB
              </p>
              <button
                onClick={clear}
                disabled={isLoading}
                aria-label="Remove selected video file"
                className="mt-3 text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 transition-colors"
              >
                <X className="h-3 w-3" aria-hidden="true" />
                Remove
              </button>
            </div>
          </div>
        </div>
      )}

      {file && (
        <button
          onClick={() => onAnalyze(file)}
          disabled={isLoading}
          className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium rounded-xl hover:from-blue-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-sm"
        >
          {isLoading ? "Analyzing..." : "Analyze Video"}
        </button>
      )}
    </div>
  );
}

