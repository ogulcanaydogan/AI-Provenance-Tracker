"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, Image as ImageIcon } from "lucide-react";

interface ImageUploadProps {
  onAnalyze: (file: File) => void;
  isLoading: boolean;
}

export function ImageUpload({ onAnalyze, isLoading }: ImageUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const selected = acceptedFiles[0];
    if (selected) {
      setFile(selected);
      const reader = new FileReader();
      reader.onload = () => setPreview(reader.result as string);
      reader.readAsDataURL(selected);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "image/jpeg": [".jpg", ".jpeg"],
      "image/png": [".png"],
      "image/webp": [".webp"],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
    disabled: isLoading,
  });

  function clear() {
    setFile(null);
    setPreview(null);
  }

  return (
    <div className="space-y-4">
      {!preview ? (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
            isDragActive
              ? "border-blue-500 bg-blue-500/5"
              : "border-gray-700 hover:border-gray-500 bg-gray-900"
          }`}
        >
          <input {...getInputProps()} />
          <Upload className="h-10 w-10 text-gray-500 mx-auto mb-4" />
          <p className="text-gray-300 font-medium">
            {isDragActive ? "Drop image here..." : "Drag & drop an image, or click to upload"}
          </p>
          <p className="text-sm text-gray-500 mt-2">
            Supports JPEG, PNG, WebP (max 10 MB)
          </p>
        </div>
      ) : (
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
          <div className="flex items-start gap-4">
            <div className="relative w-32 h-32 rounded-lg overflow-hidden flex-shrink-0 bg-gray-800">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={preview}
                alt="Upload preview"
                className="w-full h-full object-cover"
              />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <ImageIcon className="h-4 w-4 text-gray-400" />
                <span className="text-sm text-gray-200 truncate">{file?.name}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {file && (file.size / 1024 / 1024).toFixed(2)} MB
              </p>
              <button
                onClick={clear}
                disabled={isLoading}
                className="mt-3 text-xs text-gray-400 hover:text-gray-200 flex items-center gap-1 transition-colors"
              >
                <X className="h-3 w-3" />
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
          {isLoading ? "Analyzing..." : "Analyze Image"}
        </button>
      )}
    </div>
  );
}
