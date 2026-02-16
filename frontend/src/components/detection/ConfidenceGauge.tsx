"use client";

import { getConfidenceColor } from "@/lib/utils";
import { VERDICT_LABELS, VERDICT_COLORS } from "@/lib/constants";

interface ConfidenceGaugeProps {
  score: number;
  verdict: string;
}

export function ConfidenceGauge({ score, verdict }: ConfidenceGaugeProps) {
  const color = getConfidenceColor(score);
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * 0.75; // 270 degrees
  const filled = (score / 100) * arcLength;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-48 h-48">
        <svg viewBox="0 0 200 200" className="w-full h-full -rotate-[135deg]">
          {/* Background arc */}
          <circle
            cx="100"
            cy="100"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="12"
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
            className="text-gray-800"
          />
          {/* Filled arc */}
          <circle
            cx="100"
            cy="100"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="12"
            strokeDasharray={`${filled} ${circumference}`}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-white">{score.toFixed(0)}%</span>
          <span className="text-xs text-gray-400 mt-1">AI Confidence</span>
        </div>
      </div>
      <span
        className={`text-lg font-semibold ${VERDICT_COLORS[verdict] || "text-gray-400"}`}
      >
        {VERDICT_LABELS[verdict] || verdict}
      </span>
    </div>
  );
}
