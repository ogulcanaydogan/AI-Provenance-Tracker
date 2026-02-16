"use client";

import { AudioUpload } from "@/components/detection/AudioUpload";
import { ResultCard } from "@/components/detection/ResultCard";
import { AnalysisLoader } from "@/components/detection/AnalysisLoader";
import { useAudioDetection } from "@/hooks/useAudioDetection";
import { AlertCircle } from "lucide-react";

export default function AudioDetectionPage() {
  const { status, result, error, analyze, reset } = useAudioDetection();

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Audio Detection</h1>
        <p className="text-gray-400 mt-2">
          Upload a WAV file to analyze whether it appears human-recorded or AI-generated.
        </p>
      </div>

      <AudioUpload onAnalyze={analyze} isLoading={status === "loading"} />

      <div className="mt-8">
        {status === "loading" && <AnalysisLoader />}

        {status === "error" && error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
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
              Analyze another audio file
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
