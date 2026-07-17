"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getEvidencePack, getEvidencePackUrl } from "@/lib/api";
import { BackendEvidencePack } from "@/lib/types";
import { VERDICT_LABELS, VERDICT_BG_COLORS } from "@/lib/constants";
import { formatDate, formatConfidence } from "@/lib/utils";
import { ConfidenceGauge } from "@/components/detection/ConfidenceGauge";
import { AlertCircle, Clock, Code2, Copy, Check } from "lucide-react";

const DECISION_BAND_LABELS: Record<string, string> = {
  human: "Human",
  uncertain: "Uncertain",
  ai: "AI",
};

interface LoadedEvidence {
  id: string;
  pack: BackendEvidencePack | null;
  error: string | null;
}

function toPercent(value: number): number {
  return Number((Math.max(0, Math.min(value, 1)) * 100).toFixed(1));
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wider text-gray-500">{label}</dt>
      <dd className="text-sm text-gray-200 mt-1 break-words">{value}</dd>
    </div>
  );
}

function ChunkTable({ pack }: { pack: BackendEvidencePack }) {
  const summary = pack.trace.chunk_summary;
  if (!summary) return null;

  return (
    <section>
      <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
        Chunk Consistency
      </h2>
      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        <Field label="Chunks" value={String(summary.chunk_count)} />
        <Field label="Mean confidence" value={formatConfidence(toPercent(summary.mean_confidence))} />
        <Field label="Spread" value={formatConfidence(toPercent(summary.confidence_spread))} />
        <Field label="Disagreement" value={formatConfidence(toPercent(summary.disagreement_ratio))} />
      </dl>
      <p className="text-sm text-gray-400 mb-4">
        Chunks were routed mostly as <span className="text-gray-200">{summary.dominant_domain}</span>
        {summary.route_mismatch
          ? ", which disagrees with the case-level route."
          : ", matching the case-level route."}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wider text-gray-500 border-b border-gray-800">
              <th className="py-2 pr-4 font-medium">Chunk</th>
              <th className="py-2 pr-4 font-medium">Words</th>
              <th className="py-2 pr-4 font-medium">Sentences</th>
              <th className="py-2 pr-4 font-medium">AI confidence</th>
              <th className="py-2 pr-4 font-medium">Band</th>
              <th className="py-2 font-medium">Route</th>
            </tr>
          </thead>
          <tbody>
            {summary.chunks.map((chunk) => (
              <tr key={chunk.index} className="border-b border-gray-800/60">
                <td className="py-2 pr-4 text-gray-400">{chunk.index + 1}</td>
                <td className="py-2 pr-4 text-gray-300">{chunk.word_count}</td>
                <td className="py-2 pr-4 text-gray-300">{chunk.sentence_count}</td>
                <td className="py-2 pr-4 text-gray-200">
                  {formatConfidence(toPercent(chunk.confidence))}
                </td>
                <td className="py-2 pr-4 text-gray-300">
                  {DECISION_BAND_LABELS[chunk.decision_band] || chunk.decision_band}
                </td>
                <td className="py-2 text-gray-400">{chunk.domain_profile}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function EvidencePage() {
  const params = useParams<{ id: string }>();
  const analysisId = params.id;
  const [loaded, setLoaded] = useState<LoadedEvidence | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let active = true;
    getEvidencePack(analysisId)
      .then((pack) => {
        if (active) setLoaded({ id: analysisId, pack, error: null });
      })
      .catch((err: Error) => {
        if (active) setLoaded({ id: analysisId, pack: null, error: err.message });
      });
    return () => {
      active = false;
    };
  }, [analysisId]);

  // Anything loaded for a previous id is stale while the new one is in flight.
  const loading = loaded?.id !== analysisId;
  const pack = loaded?.pack ?? null;
  const error = loaded?.error ?? null;

  async function copyLink() {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  if (loading) {
    return (
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="h-8 w-64 rounded-lg bg-gray-800 animate-pulse" />
        <div
          className="h-72 rounded-2xl bg-gray-800 animate-pulse mt-8"
          role="status"
          aria-label="Loading evidence report"
        />
      </main>
    );
  }

  if (error || !pack) {
    return (
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div
          role="alert"
          className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3"
        >
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" aria-hidden="true" />
          <p className="text-sm text-red-300">{error || "Evidence report not found."}</p>
        </div>
        <Link
          href="/detect/text"
          className="inline-block mt-6 text-sm text-gray-400 hover:text-gray-200 transition-colors"
        >
          Run a new analysis
        </Link>
      </main>
    );
  }

  const confidencePercent = toPercent(pack.confidence);
  const { trace, detector_versions: versions } = pack;
  const lineage = trace.artifact_lineage;

  return (
    <main
      className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12"
      aria-labelledby="evidence-heading"
    >
      <div className="mb-8">
        <h1 id="evidence-heading" className="text-3xl font-bold text-white">
          Evidence Report
        </h1>
        <p className="text-gray-400 mt-2">
          A shareable record of how whoisfake.com reached this verdict.
        </p>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-8">
        <div className="flex items-center justify-between">
          <span
            className={`px-3 py-1 rounded-full text-sm font-medium border ${
              VERDICT_BG_COLORS[pack.verdict] || ""
            }`}
          >
            {VERDICT_LABELS[pack.verdict] || pack.verdict}
          </span>
          <div className="flex items-center gap-1.5 text-xs text-gray-500">
            <Clock className="h-3.5 w-3.5" />
            {formatDate(pack.timestamp)}
          </div>
        </div>

        <div className="flex justify-center py-2">
          <ConfidenceGauge score={confidencePercent} verdict={pack.verdict} />
        </div>

        {pack.explanation && (
          <div className="bg-gray-800/30 rounded-xl p-4">
            <p className="text-sm text-gray-300 leading-relaxed">{pack.explanation}</p>
          </div>
        )}

        {pack.uncertainty_reason && (
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4">
            <p className="text-sm text-yellow-200">{pack.uncertainty_reason}</p>
          </div>
        )}

        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
            Analysis
          </h2>
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <Field label="Analysis ID" value={pack.analysis_id} />
            <Field label="Content type" value={pack.content_type} />
            <Field
              label="Decision band"
              value={
                pack.decision_band
                  ? DECISION_BAND_LABELS[pack.decision_band] || pack.decision_band
                  : "—"
              }
            />
            <Field label="Source" value={pack.source} />
            <Field label="Source URL" value={pack.source_url || "—"} />
            <Field label="Route profile" value={trace.route_profile || "—"} />
          </dl>
        </section>

        {(trace.uncertainty_flags.length > 0 || trace.disagreement_reasons.length > 0) && (
          <section>
            <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
              Guardrails
            </h2>
            <ul className="space-y-2">
              {[...trace.uncertainty_flags, ...trace.disagreement_reasons].map((item) => (
                <li key={item} className="text-sm text-gray-300">
                  {item}
                </li>
              ))}
            </ul>
          </section>
        )}

        <ChunkTable pack={pack} />

        <section>
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
            Detector Versions
          </h2>
          <dl className="grid grid-cols-2 sm:grid-cols-3 gap-4">
            <Field label="Model" value={versions.model_version || "—"} />
            <Field label="Calibration" value={versions.calibration_version || "—"} />
            <Field label="Model bundle" value={lineage.model_bundle_version || "—"} />
            <Field label="Calibration bundle" value={lineage.calibration_bundle_version || "—"} />
            <Field label="Benchmark manifest" value={lineage.private_benchmark_manifest || "—"} />
          </dl>
        </section>

        <div className="flex flex-wrap justify-end gap-2 border-t border-gray-800 pt-6">
          <a
            href={getEvidencePackUrl(pack.analysis_id)}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#333] text-gray-200 hover:text-white hover:border-[#4a4a4a] transition-colors text-xs"
          >
            <Code2 className="h-3.5 w-3.5" />
            View raw JSON
          </a>
          <button
            type="button"
            onClick={copyLink}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#333] text-gray-200 hover:text-white hover:border-[#4a4a4a] transition-colors text-xs"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Link copied" : "Copy link"}
          </button>
        </div>
      </div>
    </main>
  );
}
