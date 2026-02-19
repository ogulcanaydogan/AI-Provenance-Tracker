"use client";

import { AlertCircle } from "lucide-react";
import { AnalysisLoader } from "@/components/detection/AnalysisLoader";
import { ResultCard } from "@/components/detection/ResultCard";
import { VideoUpload } from "@/components/detection/VideoUpload";
import { useVideoDetection } from "@/hooks/useVideoDetection";

export default function VideoDetectionPage() {
  const { status, result, error, analyze, reset } = useVideoDetection();

  return (
    <main
      className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
      aria-labelledby="video-detection-heading"
    >
      <div className="mb-8">
        <div className="flex items-center gap-3">
          <h1 id="video-detection-heading" className="text-3xl font-bold text-white">
            Video Detection
          </h1>
          <span className="px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20">
            Beta
          </span>
        </div>
        <p className="text-gray-400 mt-2">
          Upload a short video clip to analyze whether it appears human-captured or AI-generated.
        </p>
      </div>

      <VideoUpload onAnalyze={analyze} isLoading={status === "loading"} />

      <div className="mt-8" aria-live="polite" aria-atomic="true">
        {status === "loading" && <AnalysisLoader />}

        {status === "error" && error && (
          <div
            role="alert"
            className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3"
          >
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" aria-hidden="true" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        {status === "success" && result && (
          <div className="space-y-4">
            <ResultCard result={result} />
            <button
              onClick={reset}
              className="text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              Analyze another video
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
