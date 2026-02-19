export default function HistoryLoading() {
  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <div className="h-8 w-56 rounded-lg bg-gray-800 animate-pulse" />
        <div className="h-4 w-80 rounded bg-gray-800 animate-pulse mt-3" />
      </div>

      {/* Filter bar skeleton */}
      <div className="flex items-center gap-3 mb-6">
        <div className="h-9 w-32 rounded-lg bg-gray-800 animate-pulse" />
        <div className="flex-1" />
        <div className="h-9 w-16 rounded-lg bg-gray-800 animate-pulse" />
        <div className="h-9 w-16 rounded-lg bg-gray-800 animate-pulse" />
      </div>

      {/* List item skeletons */}
      <div className="space-y-3" role="status" aria-label="Loading history">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4"
          >
            <div className="w-8 h-8 rounded-lg bg-gray-800 animate-pulse" />
            <div className="flex-1 space-y-2">
              <div className="h-4 w-24 rounded bg-gray-800 animate-pulse" />
              <div className="h-3 w-36 rounded bg-gray-800 animate-pulse" />
            </div>
            <div className="h-4 w-12 rounded bg-gray-800 animate-pulse" />
          </div>
        ))}
      </div>
    </main>
  );
}
