"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getHistory, getExportUrl } from "@/lib/api";
import { DetectionResult } from "@/lib/types";
import { VERDICT_LABELS, VERDICT_COLORS } from "@/lib/constants";
import { formatDate, formatConfidence } from "@/lib/utils";
import {
  Clock,
  Type,
  ImageIcon,
  AudioLines,
  Film,
  ChevronLeft,
  ChevronRight,
  Download,
  Filter,
} from "lucide-react";

function downloadFile(url: string, filename: string) {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export default function HistoryPage() {
  const [items, setItems] = useState<DetectionResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [contentType, setContentType] = useState("");
  const perPage = 20;

  useEffect(() => {
    setLoading(true);
    getHistory(page, perPage, contentType || undefined)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [page, contentType]);

  const totalPages = Math.ceil(total / perPage);

  function ContentTypeIcon({ type }: { type: DetectionResult["content_type"] }) {
    if (type === "text") return <Type className="h-4 w-4" />;
    if (type === "image") return <ImageIcon className="h-4 w-4" />;
    if (type === "audio") return <AudioLines className="h-4 w-4" />;
    return <Film className="h-4 w-4" />;
  }

  return (
    <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12" aria-labelledby="history-heading">
      <div className="mb-8">
        <h1 id="history-heading" className="text-3xl font-bold text-white">Analysis History</h1>
        <p className="text-gray-400 mt-2">
          Recent content analyses performed by the system.
        </p>
        <Link
          href="/dashboard"
          className="inline-block mt-3 text-sm text-blue-400 hover:text-blue-300 transition-colors"
        >
          View analytics dashboard &rarr;
        </Link>
      </div>

      {/* Filter & export bar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" aria-hidden="true" />
          <select
            value={contentType}
            onChange={(e) => {
              setContentType(e.target.value);
              setPage(1);
            }}
            aria-label="Filter by content type"
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100 focus:border-gray-500 focus:outline-none"
          >
            <option value="">All types</option>
            <option value="text">Text</option>
            <option value="image">Image</option>
            <option value="audio">Audio</option>
            <option value="video">Video</option>
          </select>
        </div>
        <div className="flex-1" />
        <button
          onClick={() =>
            downloadFile(
              getExportUrl("history", "csv", {
                contentType: contentType || undefined,
              }),
              "analysis_history.csv",
            )
          }
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-xs text-gray-300 hover:border-gray-500 hover:text-white transition-colors"
        >
          <Download className="h-3 w-3" />
          CSV
        </button>
        <button
          onClick={() =>
            downloadFile(
              getExportUrl("history", "json", {
                contentType: contentType || undefined,
              }),
              "analysis_history.json",
            )
          }
          className="inline-flex items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-xs text-gray-300 hover:border-gray-500 hover:text-white transition-colors"
        >
          <Download className="h-3 w-3" />
          JSON
        </button>
      </div>

      {loading ? (
        <div role="status" className="text-center py-12 text-gray-400">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-400">
            {contentType
              ? `No ${contentType} analyses found.`
              : "No analyses yet."}
          </p>
          {!contentType && (
            <div className="mt-4 flex gap-4 justify-center">
              <Link
                href="/detect/text"
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                Analyze text &rarr;
              </Link>
              <Link
                href="/detect/image"
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                Analyze image &rarr;
              </Link>
              <Link
                href="/detect/audio"
                className="text-sm text-blue-400 hover:text-blue-300"
              >
                Analyze audio &rarr;
              </Link>
            </div>
          )}
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {items.map((item) => (
              <div
                key={item.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4 hover:border-gray-700 transition-colors"
              >
                <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center text-gray-400">
                  <ContentTypeIcon type={item.content_type} />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-white capitalize">
                      {item.content_type}
                    </span>
                    <span
                      className={`text-xs font-medium ${
                        VERDICT_COLORS[item.verdict] || "text-gray-400"
                      }`}
                    >
                      {VERDICT_LABELS[item.verdict]}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-500">
                    <Clock className="h-3 w-3" />
                    {formatDate(item.analyzed_at)}
                  </div>
                </div>

                <span className="text-sm font-mono text-gray-300">
                  {formatConfidence(item.confidence_score)}
                </span>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <nav aria-label="History pagination" className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => {
                  setLoading(true);
                  setPage((p) => Math.max(1, p - 1));
                }}
                disabled={page === 1}
                aria-label="Previous page"
                className="p-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="h-5 w-5" aria-hidden="true" />
              </button>
              <span className="text-sm text-gray-400">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => {
                  setLoading(true);
                  setPage((p) => Math.min(totalPages, p + 1));
                }}
                disabled={page === totalPages}
                aria-label="Next page"
                className="p-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="h-5 w-5" aria-hidden="true" />
              </button>
            </nav>
          )}
        </>
      )}
    </main>
  );
}
