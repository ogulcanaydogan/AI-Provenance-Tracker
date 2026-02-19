import { Loader2 } from "lucide-react";

export default function RootLoading() {
  return (
    <div
      role="status"
      aria-label="Loading page"
      className="min-h-screen flex items-center justify-center"
    >
      <div className="flex flex-col items-center gap-3">
        <Loader2
          className="h-8 w-8 text-blue-500 animate-spin"
          aria-hidden="true"
        />
        <span className="text-sm text-gray-400">Loading…</span>
      </div>
    </div>
  );
}
