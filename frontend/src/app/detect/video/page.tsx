"use client";

import { AlertCircle } from "lucide-react";
import Link from "next/link";
import { AnalysisLoader } from "@/components/detection/AnalysisLoader";
import { ResultCard } from "@/components/detection/ResultCard";
import { VideoUpload } from "@/components/detection/VideoUpload";
import { useVideoDetection } from "@/hooks/useVideoDetection";

export default function VideoDetectionPage() {
  const {
    status: uploadStatus,
    result: uploadResult,
    error: uploadError,
    analyze: analyzeUpload,
    reset: resetUpload,
  } = useVideoDetection();

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
          Upload a short video clip for analysis. For URL-based analysis, use the dedicated URL
          Detection flow.
        </p>
      </div>

      <div className="space-y-6">
        <VideoUpload onAnalyze={analyzeUpload} isLoading={uploadStatus === "loading"} />
        <div className="rounded-xl border border-[#2a2a2a] bg-[#121212] p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <p className="text-sm text-gray-300">Need to analyze a public video or social URL?</p>
          <Link
            href="/detect/url"
            className="inline-flex items-center justify-center px-4 py-2 rounded-lg border border-blue-500/30 text-blue-300 hover:text-white hover:border-blue-400/60 transition-colors text-sm font-medium"
          >
            Analyze by URL
          </Link>
        </div>
      </div>

      <div className="mt-8" aria-live="polite" aria-atomic="true">
        {uploadStatus === "loading" && <AnalysisLoader />}

        {uploadStatus === "error" && uploadError && (
          <div
            role="alert"
            className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3"
          >
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" aria-hidden="true" />
            <p className="text-sm text-red-300">{uploadError}</p>
          </div>
        )}

        {uploadStatus === "success" && uploadResult && (
          <div className="space-y-4">
            <ResultCard result={uploadResult} />
            <button
              onClick={resetUpload}
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
