"use client";

import { useMemo, useState } from "react";
import { Link2, Loader2, AlertCircle } from "lucide-react";

interface URLDetectorProps {
  onAnalyze: (url: string) => void;
  isLoading: boolean;
  error?: string | null;
  examples?: string[];
}

const DEFAULT_EXAMPLES = [
  "https://example.com/news/article",
  "https://www.instagram.com/reel/ABC123/",
  "https://cdn.example.com/media/clip.mp4",
];

function isValidUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

export function URLDetector({
  onAnalyze,
  isLoading,
  error = null,
  examples = DEFAULT_EXAMPLES,
}: URLDetectorProps) {
  const [url, setUrl] = useState("");
  const [dirty, setDirty] = useState(false);

  const trimmedUrl = url.trim();
  const validUrl = useMemo(() => isValidUrl(trimmedUrl), [trimmedUrl]);
  const canAnalyze = !isLoading && trimmedUrl.length > 0 && validUrl;

  function applyExample(value: string) {
    setUrl(value);
    setDirty(true);
  }

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="url-input" className="block text-sm font-medium text-gray-200 mb-2">
          Public URL
        </label>
        <div className="relative">
          <Link2 className="h-4 w-4 text-gray-500 absolute left-3 top-3.5" aria-hidden="true" />
          <input
            id="url-input"
            type="url"
            value={url}
            onChange={(event) => {
              setUrl(event.target.value);
              setDirty(true);
            }}
            placeholder="https://..."
            aria-label="URL to analyze"
            disabled={isLoading}
            className="w-full bg-gray-900 border border-gray-700 rounded-xl pl-10 pr-4 py-3 text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-colors text-sm"
          />
        </div>
        {dirty && trimmedUrl.length > 0 && !validUrl && (
          <p className="text-xs text-red-300 mt-2">Please enter a valid http(s) URL.</p>
        )}
      </div>

      <div className="rounded-xl border border-[#262626] bg-[#111111] p-3">
        <p className="text-xs uppercase tracking-wide text-gray-500 mb-2">Examples</p>
        <div className="flex flex-wrap gap-2">
          {examples.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => applyExample(example)}
              disabled={isLoading}
              className="text-xs px-2.5 py-1 rounded-md border border-[#303030] text-gray-300 hover:text-white hover:border-[#4a4a4a] transition-colors"
            >
              {example}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-xl border border-[#2a2a2a] bg-[#121212] p-3 text-sm text-gray-300 space-y-1">
        <p className="font-medium text-gray-200">URL Analyze flow</p>
        <p className="text-gray-400">
          Upload/Paste/URL -&gt; Explainable report. For Instagram/TikTok/X, use a public post link.
          Tag or DM <span className="text-blue-300">@whoisfake</span> on Instagram, or paste the
          same public link here. Private pages are unsupported.
        </p>
      </div>

      {error && (
        <div
          role="alert"
          className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 flex items-start gap-2"
        >
          <AlertCircle className="h-4 w-4 text-red-400 mt-0.5" aria-hidden="true" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      <button
        type="button"
        onClick={() => onAnalyze(trimmedUrl)}
        disabled={!canAnalyze}
        className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-medium rounded-xl hover:from-blue-500 hover:to-purple-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all text-sm inline-flex items-center gap-2"
      >
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : null}
        {isLoading ? "Resolving URL..." : "Analyze URL"}
      </button>
    </div>
  );
}
