export default function DashboardLoading() {
  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <div className="h-8 w-48 rounded-lg bg-gray-800 animate-pulse" />
        <div className="h-4 w-64 rounded bg-gray-800 animate-pulse mt-3" />
      </div>

      {/* Stats cards skeleton */}
      <div
        className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10"
        role="status"
        aria-label="Loading dashboard"
      >
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3"
          >
            <div className="h-3 w-20 rounded bg-gray-800 animate-pulse" />
            <div className="h-7 w-16 rounded bg-gray-800 animate-pulse" />
          </div>
        ))}
      </div>

      {/* Chart area skeleton */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
        <div className="h-5 w-32 rounded bg-gray-800 animate-pulse mb-6" />
        <div className="h-48 rounded-lg bg-gray-800/50 animate-pulse" />
      </div>

      {/* Breakdown cards skeleton */}
      <div className="grid md:grid-cols-2 gap-6">
        {Array.from({ length: 2 }).map((_, i) => (
          <div
            key={i}
            className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4"
          >
            <div className="h-5 w-28 rounded bg-gray-800 animate-pulse" />
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="flex items-center justify-between">
                  <div className="h-3 w-20 rounded bg-gray-800 animate-pulse" />
                  <div className="h-3 w-12 rounded bg-gray-800 animate-pulse" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </main>
  );
}
