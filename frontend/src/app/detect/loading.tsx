import { Loader2 } from "lucide-react";

export default function DetectLoading() {
  return (
    <div
      role="status"
      aria-label="Loading detection page"
      className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
    >
      {/* Header skeleton */}
      <div className="mb-8">
        <div className="h-8 w-48 rounded-lg bg-gray-800 animate-pulse" />
        <div className="h-4 w-72 rounded bg-gray-800 animate-pulse mt-3" />
      </div>

      {/* Input area skeleton */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
        <div className="h-40 rounded-lg bg-gray-800/50 animate-pulse flex items-center justify-center">
          <Loader2
            className="h-6 w-6 text-gray-600 animate-spin"
            aria-hidden="true"
          />
        </div>
        <div className="mt-4 flex justify-end">
          <div className="h-10 w-28 rounded-lg bg-gray-800 animate-pulse" />
        </div>
      </div>
    </div>
  );
}
