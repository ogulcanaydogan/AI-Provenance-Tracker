"use client";

import { Loader2 } from "lucide-react";

export function AnalysisLoader() {
  return (
    <div
      role="status"
      aria-label="Analyzing content"
      className="bg-gray-900 border border-gray-800 rounded-2xl p-12 flex flex-col items-center gap-4"
    >
      <Loader2 className="h-10 w-10 text-blue-500 animate-spin" aria-hidden="true" />
      <div className="text-center">
        <p className="text-white font-medium">Analyzing content...</p>
        <p className="text-sm text-gray-400 mt-1">
          Running detection algorithms. This may take a few seconds.
        </p>
      </div>
    </div>
  );
}
