"use client";

import { useState, useCallback } from "react";
import ResultCard from "./ResultCard";

interface ImageAnalysis {
  frequency_anomaly: number;
  artifact_score: number;
  metadata_flags: string[];
  compression_analysis: string | null;
}

interface DetectionResult {
  is_ai_generated: boolean;
  confidence: number;
  model_prediction: string | null;
  analysis: ImageAnalysis;
  explanation: string;
  filename: string;
  dimensions: [number, number];
  processing_time_ms: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ImageDetector() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFile = (selectedFile: File) => {
    const allowedTypes = ["image/png", "image/jpeg", "image/webp"];
    if (!allowedTypes.includes(selectedFile.type)) {
      setError("Please upload a PNG, JPEG, or WebP image");
      return;
    }

    if (selectedFile.size > 10 * 1024 * 1024) {
      setError("Image must be less than 10MB");
      return;
    }

    setFile(selectedFile);
    setError(null);
    setResult(null);

    const reader = new FileReader();
    reader.onload = (e) => {
      setPreview(e.target?.result as string);
    };
    reader.readAsDataURL(selectedFile);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFile(droppedFile);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!file) {
      setError("Please select an image to analyze");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/api/v1/detect/image`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Detection failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label className="block text-sm font-medium mb-2">
            Upload an image to analyze
          </label>

          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
              isDragging
                ? "border-blue-500 bg-blue-500/10"
                : "border-[#262626] hover:border-gray-600"
            }`}
          >
            {preview ? (
              <div className="relative">
                <img
                  src={preview}
                  alt="Preview"
                  className="max-h-64 mx-auto rounded-lg"
                />
                <button
                  type="button"
                  onClick={handleClear}
                  className="absolute top-2 right-2 p-1 bg-black/50 rounded-full hover:bg-black/70"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div>
                <div className="text-4xl mb-3">🖼️</div>
                <p className="text-gray-400 mb-2">
                  Drag and drop an image here, or click to select
                </p>
                <p className="text-gray-600 text-sm">
                  Supports PNG, JPEG, WebP (max 10MB)
                </p>
              </div>
            )}

            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => {
                const selectedFile = e.target.files?.[0];
                if (selectedFile) handleFile(selectedFile);
              }}
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />
          </div>

          {file && (
            <p className="text-xs text-gray-500 mt-2">
              Selected: {file.name} ({(file.size / 1024).toFixed(1)} KB)
            </p>
          )}
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isLoading || !file}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <span className="animate-spin">⏳</span>
                Analyzing...
              </>
            ) : (
              <>
                <span>🔍</span>
                Analyze Image
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="px-6 py-3 bg-[#262626] text-gray-400 rounded-lg hover:bg-[#333] transition-colors"
          >
            Clear
          </button>
        </div>
      </form>

      {result && (
        <ResultCard
          type="image"
          isAiGenerated={result.is_ai_generated}
          confidence={result.confidence}
          modelPrediction={result.model_prediction}
          explanation={result.explanation}
          processingTime={result.processing_time_ms}
          analysis={result.analysis}
          dimensions={result.dimensions}
        />
      )}
    </div>
  );
}
