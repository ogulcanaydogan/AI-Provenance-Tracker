"use client";

import { AlertCircle } from "lucide-react";
import { AnalysisLoader } from "@/components/detection/AnalysisLoader";
import { ResultCard } from "@/components/detection/ResultCard";
import { URLDetector } from "@/components/detection/URLDetector";
import { VideoUpload } from "@/components/detection/VideoUpload";
import { useUrlDetection } from "@/hooks/useUrlDetection";
import { useVideoDetection } from "@/hooks/useVideoDetection";

export default function VideoDetectionPage() {
  const {
    status: uploadStatus,
    result: uploadResult,
    error: uploadError,
    analyze: analyzeUpload,
    reset: resetUpload,
  } = useVideoDetection();
  const {
    status: urlStatus,
    result: urlResult,
    error: urlError,
    analyze: analyzeUrl,
    reset: resetUrl,
  } = useUrlDetection();

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
          Upload a short video clip or provide a direct/public video URL for analysis.
        </p>
      </div>

      <div className="space-y-6">
        <VideoUpload onAnalyze={analyzeUpload} isLoading={uploadStatus === "loading"} />
        <div className="flex items-center gap-3 text-xs text-gray-500 uppercase tracking-wide">
          <span className="h-px bg-[#2d2d2d] flex-1" />
          or direct URL
          <span className="h-px bg-[#2d2d2d] flex-1" />
        </div>
        <URLDetector
          onAnalyze={analyzeUrl}
          isLoading={urlStatus === "loading"}
          error={urlError}
          examples={[
            "https://cdn.example.com/media/clip.mp4",
            "https://www.instagram.com/reel/ABC123/",
            "https://www.tiktok.com/@sample/video/1234567890",
          ]}
        />
      </div>

      <div className="mt-8" aria-live="polite" aria-atomic="true">
        {(uploadStatus === "loading" || urlStatus === "loading") && <AnalysisLoader />}

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

        {urlStatus === "success" && urlResult && (
          <div className="space-y-4 mt-6">
            <ResultCard result={urlResult} />
            <button
              onClick={resetUrl}
              className="text-sm text-gray-400 hover:text-gray-200 transition-colors"
            >
              Analyze another URL
            </button>
          </div>
        )}
      </div>
    </main>
  );
}
