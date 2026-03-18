"use client";

import { useState } from "react";
import { DetectionResult } from "@/lib/types";
import { formatDate } from "@/lib/utils";
import { VERDICT_LABELS, VERDICT_BG_COLORS } from "@/lib/constants";
import { ConfidenceGauge } from "./ConfidenceGauge";
import { SignalBreakdown } from "./SignalBreakdown";
import { Clock, Copy, Check } from "lucide-react";

interface ResultCardProps {
  result: DetectionResult;
}

export function ResultCard({ result }: ResultCardProps) {
  const [copied, setCopied] = useState(false);

  async function copyEvidenceSummary() {
    const summary = [
      `verdict: ${VERDICT_LABELS[result.verdict] || result.verdict}`,
      `confidence: ${result.confidence_score}%`,
      `timestamp: ${result.analyzed_at}`,
      `analysis_id: ${result.id}`,
      `content_type: ${result.content_type}`,
    ].join("\n");

    try {
      await navigator.clipboard.writeText(summary);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2500);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium border ${
            VERDICT_BG_COLORS[result.verdict] || ""
          }`}
        >
          {VERDICT_LABELS[result.verdict] || result.verdict}
        </span>
        <div className="flex items-center gap-1.5 text-xs text-gray-500">
          <Clock className="h-3.5 w-3.5" />
          {formatDate(result.analyzed_at)}
        </div>
      </div>

      {/* Confidence Gauge */}
      <div className="flex justify-center py-4">
        <ConfidenceGauge score={result.confidence_score} verdict={result.verdict} />
      </div>

      {/* Summary */}
      <div className="bg-gray-800/30 rounded-xl p-4">
        <p className="text-sm text-gray-300 leading-relaxed">{result.summary}</p>
      </div>

      <div className="flex justify-end">
        <button
          type="button"
          onClick={copyEvidenceSummary}
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#333] text-gray-200 hover:text-white hover:border-[#4a4a4a] transition-colors text-xs"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied evidence" : "Copy Shareable Evidence"}
        </button>
      </div>

      {/* Signal Breakdown */}
      <div>
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">
          Detection Signals
        </h3>
        <SignalBreakdown signals={result.signals} />
      </div>
    </div>
  );
}
