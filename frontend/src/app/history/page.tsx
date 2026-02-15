"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getHistory } from "@/lib/api";
import { DetectionResult } from "@/lib/types";
import { VERDICT_LABELS, VERDICT_COLORS } from "@/lib/constants";
import { formatDate, formatConfidence } from "@/lib/utils";
import { Clock, Type, ImageIcon, AudioLines, Film, ChevronLeft, ChevronRight } from "lucide-react";

export default function HistoryPage() {
  const [items, setItems] = useState<DetectionResult[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const perPage = 20;

  useEffect(() => {
    getHistory(page, perPage)
      .then((data) => {
        setItems(data.items);
        setTotal(data.total);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [page]);

  const totalPages = Math.ceil(total / perPage);

  function ContentTypeIcon({ type }: { type: DetectionResult["content_type"] }) {
    if (type === "text") return <Type className="h-4 w-4" />;
    if (type === "image") return <ImageIcon className="h-4 w-4" />;
    if (type === "audio") return <AudioLines className="h-4 w-4" />;
    return <Film className="h-4 w-4" />;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white">Analysis History</h1>
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

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading...</div>
      ) : items.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-400">No analyses yet.</p>
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
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => {
                  setLoading(true);
                  setPage((p) => Math.max(1, p - 1));
                }}
                disabled={page === 1}
                className="p-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
              >
                <ChevronLeft className="h-5 w-5" />
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
                className="p-2 text-gray-400 hover:text-white disabled:opacity-30 transition-colors"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
