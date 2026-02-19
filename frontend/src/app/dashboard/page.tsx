"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, Bot, CalendarDays, BarChart3, RefreshCw, Download } from "lucide-react";
import { getDashboard, getEvaluation, getXCollectEstimate, getExportUrl } from "@/lib/api";
import {
  BackendDashboardResponse,
  BackendEvaluationResponse,
  BackendXCollectEstimateResponse,
} from "@/lib/types";

function formatPct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function downloadFile(url: string, filename: string) {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function maxTimelineValue(items: BackendDashboardResponse["timeline"]): number {
  return items.reduce((max, item) => Math.max(max, item.total), 0);
}

export default function DashboardPage() {
  const [days, setDays] = useState(14);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BackendDashboardResponse | null>(null);
  const [evaluation, setEvaluation] = useState<BackendEvaluationResponse | null>(null);
  const [estimateWindowDays, setEstimateWindowDays] = useState(14);
  const [estimateMaxPosts, setEstimateMaxPosts] = useState(60);
  const [estimateMaxPages, setEstimateMaxPages] = useState(1);
  const [estimateLoading, setEstimateLoading] = useState(false);
  const [estimateError, setEstimateError] = useState<string | null>(null);
  const [estimate, setEstimate] = useState<BackendXCollectEstimateResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([getDashboard(days), getEvaluation(Math.max(days, 30))])
      .then(([dashboardPayload, evaluationPayload]) => {
        if (cancelled) return;
        setData(dashboardPayload);
        setEvaluation(evaluationPayload);
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

  const runEstimate = useCallback(async () => {
    try {
      setEstimateLoading(true);
      setEstimateError(null);
      const payload = await getXCollectEstimate({
        window_days: estimateWindowDays,
        max_posts: estimateMaxPosts,
        max_pages: estimateMaxPages,
      });
      setEstimate(payload);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to estimate X collection cost";
      setEstimateError(message);
    } finally {
      setEstimateLoading(false);
    }
  }, [estimateWindowDays, estimateMaxPosts, estimateMaxPages]);

  useEffect(() => {
    void runEstimate();
  }, [runEstimate]);

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
  const evalAlerts = useMemo(() => evaluation?.alerts || [], [evaluation]);
  const evalLatestRows = useMemo(
    () => Object.entries(evaluation?.latest_by_content_type || {}).sort((a, b) => a[0].localeCompare(b[0])),
    [evaluation]
  );
  const evalTrendRows = useMemo(
    () => [...(evaluation?.trend || [])].slice(-12).reverse(),
    [evaluation]
  );

  const maxTimeline = maxTimelineValue(data?.timeline || []);
  const loading = (data === null || evaluation === null) && error === null;

  return (
    <main className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12" aria-labelledby="dashboard-heading">
      <div className="mb-8 flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 id="dashboard-heading" className="text-3xl font-bold text-white">API Analytics Dashboard</h1>
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
              setEvaluation(null);
            }}
            className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
          >
            <option value={7}>7 days</option>
            <option value={14}>14 days</option>
            <option value={30}>30 days</option>
            <option value={60}>60 days</option>
            <option value={90}>90 days</option>
          </select>
          <button
            onClick={() =>
              downloadFile(
                getExportUrl("dashboard", "csv", { days }),
                "dashboard_timeline.csv",
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
                getExportUrl("dashboard", "json", { days }),
                "dashboard.json",
              )
            }
            className="inline-flex items-center gap-1.5 rounded-lg border border-gray-700 bg-gray-900 px-3 py-2 text-xs text-gray-300 hover:border-gray-500 hover:text-white transition-colors"
          >
            <Download className="h-3 w-3" />
            JSON
          </button>
        </div>
      </div>

      {loading && (
        <div role="status" className="rounded-xl border border-gray-800 bg-gray-900 p-6 text-gray-300 flex items-center gap-3">
          <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading dashboard...
        </div>
      )}

      {!loading && error && (
        <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-6 text-red-300">{error}</div>
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

          {evalAlerts.length > 0 && (
            <section className="rounded-xl border border-red-500/30 bg-red-500/10 p-4">
              <h2 className="text-sm font-semibold text-red-200 mb-2">Evaluation Alerts</h2>
              <div className="space-y-1">
                {evalAlerts.map((alert) => (
                  <p key={`${alert.code}-${alert.message}`} className="text-sm text-red-100">
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
            <h2 className="text-lg font-semibold text-white mb-2">X Collection Cost Precheck</h2>
            <p className="text-sm text-gray-400 mb-4">
              Estimates API request usage before running X intelligence collection.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
              <label className="text-xs text-gray-400">
                Window (days)
                <input
                  type="number"
                  min={1}
                  max={90}
                  value={estimateWindowDays}
                  onChange={(e) => setEstimateWindowDays(Number(e.target.value) || 1)}
                  className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                />
              </label>
              <label className="text-xs text-gray-400">
                Max posts
                <input
                  type="number"
                  min={20}
                  max={1000}
                  value={estimateMaxPosts}
                  onChange={(e) => setEstimateMaxPosts(Number(e.target.value) || 20)}
                  className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                />
              </label>
              <label className="text-xs text-gray-400">
                Max pages
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={estimateMaxPages}
                  onChange={(e) => setEstimateMaxPages(Number(e.target.value) || 1)}
                  className="mt-1 w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
                />
              </label>
            </div>
            <div className="mb-4">
              <button
                type="button"
                onClick={() => void runEstimate()}
                disabled={estimateLoading}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-700 bg-gray-950 px-4 py-2 text-sm text-gray-200 hover:border-gray-500 disabled:opacity-60"
              >
                {estimateLoading && <RefreshCw className="h-4 w-4 animate-spin" />}
                Recalculate
              </button>
            </div>

            {estimateLoading && (
              <p className="text-sm text-gray-400 flex items-center gap-2">
                <RefreshCw className="h-4 w-4 animate-spin" />
                Estimating request usage...
              </p>
            )}

            {!estimateLoading && estimateError && (
              <p className="text-sm text-red-300">{estimateError}</p>
            )}

            {!estimateLoading && !estimateError && estimate && (
              <div className="space-y-2 text-sm">
                <p className="text-gray-200">
                  Estimated requests:{" "}
                  <span className="font-semibold text-white">{estimate.estimated_requests}</span>{" "}
                  (cap {estimate.max_requests_per_run}, worst case {estimate.worst_case_requests})
                </p>
                <p className={estimate.within_budget ? "text-emerald-300" : "text-amber-300"}>
                  {estimate.within_budget
                    ? "Within current budget guard."
                    : `Exceeds budget guard. Recommended max posts: ${estimate.recommended_max_posts}.`}
                </p>
                <p className="text-gray-400">
                  Split: target {estimate.target_limit}, mentions {estimate.mention_limit}, search{" "}
                  {estimate.interaction_limit}, page cap {estimate.page_cap}.
                </p>
              </div>
            )}
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

          <section className="rounded-xl border border-gray-800 bg-gray-900 p-6">
            <h2 className="text-lg font-semibold text-white mb-4">Evaluation Trend</h2>
            <p className="text-sm text-gray-400 mb-4">
              Recent calibration snapshots (precision, recall, F1, threshold) across modalities.
            </p>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-300">Latest by Content Type</h3>
                {evalLatestRows.length === 0 && (
                  <p className="text-sm text-gray-500">No evaluation reports found.</p>
                )}
                {evalLatestRows.map(([contentType, metrics]) => (
                  <div
                    key={contentType}
                    className="rounded-lg border border-gray-800 bg-gray-950 p-3 text-sm"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-gray-200 capitalize">{contentType}</span>
                      <span className="text-gray-400">{metrics.generated_at.slice(0, 10)}</span>
                    </div>
                    <div className="text-gray-400">
                      P {formatPct(metrics.precision)} | R {formatPct(metrics.recall)} | F1{" "}
                      {formatPct(metrics.f1)} | Th {metrics.recommended_threshold.toFixed(2)}
                    </div>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <h3 className="text-sm font-medium text-gray-300">Recent Snapshots</h3>
                {evalTrendRows.length === 0 && (
                  <p className="text-sm text-gray-500">No trend rows yet.</p>
                )}
                {evalTrendRows.map((row, index) => (
                  <div
                    key={`${row.generated_at}-${row.content_type}-${index}`}
                    className="flex items-center justify-between text-xs border-b border-gray-800 py-1"
                  >
                    <span className="text-gray-400">
                      {row.date} {row.content_type}
                    </span>
                    <span className="text-gray-300">
                      F1 {formatPct(row.f1)} | P {formatPct(row.precision)} | R {formatPct(row.recall)}
                    </span>
                  </div>
                ))}
              </div>
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
    </main>
  );
}
