"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, Bot, CalendarDays, BarChart3, RefreshCw } from "lucide-react";
import { getDashboard } from "@/lib/api";
import { BackendDashboardResponse } from "@/lib/types";

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function maxTimelineValue(items: BackendDashboardResponse["timeline"]): number {
  return items.reduce((max, item) => Math.max(max, item.total), 0);
}

export default function DashboardPage() {
  const [days, setDays] = useState(14);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BackendDashboardResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    getDashboard(days)
      .then((payload) => {
        if (!cancelled) {
          setData(payload);
        }
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message || "Failed to load dashboard data");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [days]);

  const typeRows = useMemo(
    () =>
      Object.entries(data?.by_type_window || {})
        .sort((a, b) => b[1] - a[1])
        .filter(([, count]) => count > 0),
    [data]
  );

  const sourceRows = useMemo(
    () =>
      Object.entries(data?.by_source_window || {})
        .sort((a, b) => b[1] - a[1])
        .filter(([, count]) => count > 0),
    [data]
  );
  const modelRows = useMemo(
    () => (data?.top_models_window || []).filter((entry) => entry.count > 0),
    [data]
  );
  const alerts = useMemo(() => data?.alerts_window || [], [data]);

  const maxTimeline = maxTimelineValue(data?.timeline || []);
  const loading = data === null && error === null;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">API Analytics Dashboard</h1>
          <p className="text-gray-400 mt-2">
            Windowed analysis activity, AI detection rate, and source/type breakdown.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label htmlFor="days" className="text-sm text-gray-400">
            Window
          </label>
          <select
            id="days"
            value={days}
            onChange={(e) => {
              setDays(Number(e.target.value));
              setError(null);
              setData(null);
            }}
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
          >
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </select>
        </div>
      </div>

      {loading && (
        <div className="rounded-xl border border-gray-800 bg-gray-900 p-6 text-gray-300 flex items-center gap-3">
          <RefreshCw className="h-4 w-4 animate-spin" />
          Loading dashboard...
        </div>
      )}

      {!loading && error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300">{error}</div>
      )}

      {!loading && !error && data && (
        <div className="space-y-8">
          {alerts.length > 0 && (
            <section className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
              <h2 className="text-sm font-semibold text-amber-200 mb-2">Alerts</h2>
              <div className="space-y-1">
                {alerts.map((alert) => (
                  <p key={`${alert.code}-${alert.message}`} className="text-sm text-amber-100">
                    [{alert.severity}] {alert.message}
                  </p>
                ))}
              </div>
            </section>
          )}

          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <Activity className="h-4 w-4" />
                Window Analyses
              </div>
              <div className="text-2xl font-semibold text-white mt-2">
                {data.summary.total_analyses_window}
              </div>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <Bot className="h-4 w-4" />
                AI Rate
              </div>
              <div className="text-2xl font-semibold text-white mt-2">
                {formatPct(data.summary.ai_rate_window)}
              </div>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <BarChart3 className="h-4 w-4" />
                Avg Confidence
              </div>
              <div className="text-2xl font-semibold text-white mt-2">
                {formatPct(data.summary.average_confidence_window)}
              </div>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-900 p-5">
              <div className="flex items-center gap-2 text-gray-400 text-sm">
                <CalendarDays className="h-4 w-4" />
                All-Time Analyses
              </div>
              <div className="text-2xl font-semibold text-white mt-2">
                {data.summary.total_analyses_all_time}
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-gray-800 bg-gray-900 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Daily Activity</h2>
            <div className="space-y-3">
              {data.timeline.map((item) => {
                const width = maxTimeline > 0 ? (item.total / maxTimeline) * 100 : 0;
                return (
                  <div key={item.date}>
                    <div className="flex items-center justify-between text-xs text-gray-400 mb-1">
                      <span>{item.date}</span>
                      <span>
                        total {item.total} | ai {item.ai_detected} | human {item.human_detected}
                      </span>
                    </div>
                    <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-2 bg-blue-500 rounded-full"
                        style={{ width: `${width}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">By Content Type</h2>
              <div className="space-y-2">
                {typeRows.length === 0 && <p className="text-sm text-gray-500">No data</p>}
                {typeRows.map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between text-sm">
                    <span className="text-gray-300 capitalize">{type}</span>
                    <span className="text-white font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
              <h2 className="text-lg font-semibold text-white mb-4">By Source</h2>
              <div className="space-y-2">
                {sourceRows.length === 0 && <p className="text-sm text-gray-500">No data</p>}
                {sourceRows.map(([source, count]) => (
                  <div key={source} className="flex items-center justify-between text-sm">
                    <span className="text-gray-300">{source}</span>
                    <span className="text-white font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <section className="rounded-xl border border-gray-800 bg-gray-900 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Top Predicted Models</h2>
            <div className="space-y-2">
              {modelRows.length === 0 && <p className="text-sm text-gray-500">No model data</p>}
              {modelRows.map((row) => (
                <div
                  key={`${row.model}-${row.count}`}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-gray-300">{row.model}</span>
                  <span className="text-white font-medium">{row.count}</span>
                </div>
              ))}
            </div>
          </section>

          <div className="text-sm text-gray-400">
            Need item-level details?{" "}
            <Link href="/history" className="text-blue-400 hover:text-blue-300">
              Open analysis history
            </Link>
            .
          </div>
        </div>
      )}
    </div>
  );
}
