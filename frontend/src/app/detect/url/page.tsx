"use client";

import { AnalysisLoader } from "@/components/detection/AnalysisLoader";
import { ResultCard } from "@/components/detection/ResultCard";
import { URLDetector } from "@/components/detection/URLDetector";
import { useUrlDetection } from "@/hooks/useUrlDetection";

export default function UrlDetectionPage() {
  const { status, result, error, analyze, reset } = useUrlDetection();

  return (
    <main
      className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
      aria-labelledby="url-detection-heading"
    >
      <div className="mb-8">
        <h1 id="url-detection-heading" className="text-3xl font-bold text-white">
          URL Detection
        </h1>
        <p className="text-gray-400 mt-2">
          Analyze text, image, or video from a public URL. For social platforms, use a public post
          link so OG media can be resolved.
        </p>
      </div>

      <URLDetector onAnalyze={analyze} isLoading={status === "loading"} error={error} />

      <div className="mt-8" aria-live="polite" aria-atomic="true">
        {status === "loading" && <AnalysisLoader />}

        {status === "success" && result && (
          <div className="space-y-4">
            <ResultCard result={result} />
            <button
              onClick={reset}
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
