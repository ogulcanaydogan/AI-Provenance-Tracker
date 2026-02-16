"use client";

import { DetectionSignal } from "@/lib/types";
import { getConfidenceColor } from "@/lib/utils";
import {
  Brain,
  BarChart3,
  Type,
  ImageIcon,
  Search,
  AudioLines,
  Film,
} from "lucide-react";

const signalIcons: Record<string, React.ReactNode> = {
  ml_classifier: <Brain className="h-5 w-5" />,
  perplexity: <BarChart3 className="h-5 w-5" />,
  burstiness: <Type className="h-5 w-5" />,
  vocabulary: <Search className="h-5 w-5" />,
  frequency_analysis: <BarChart3 className="h-5 w-5" />,
  metadata: <ImageIcon className="h-5 w-5" />,
  artifacts: <Search className="h-5 w-5" />,
  spectral_flatness: <BarChart3 className="h-5 w-5" />,
  dynamic_range: <AudioLines className="h-5 w-5" />,
  clipping_ratio: <AudioLines className="h-5 w-5" />,
  zero_crossing_rate: <AudioLines className="h-5 w-5" />,
  entropy_score: <Film className="h-5 w-5" />,
  byte_uniformity: <Film className="h-5 w-5" />,
  repeated_chunk_ratio: <Film className="h-5 w-5" />,
  signature_flags: <Film className="h-5 w-5" />,
};

const signalLabels: Record<string, string> = {
  ml_classifier: "ML Classifier",
  perplexity: "Perplexity Analysis",
  burstiness: "Burstiness",
  vocabulary: "Vocabulary",
  frequency_analysis: "Frequency Analysis",
  metadata: "Metadata",
  artifacts: "Artifact Detection",
  spectral_flatness: "Spectral Flatness",
  dynamic_range: "Dynamic Range",
  clipping_ratio: "Clipping Ratio",
  zero_crossing_rate: "Zero-Crossing Rate",
  entropy_score: "Entropy Score",
  byte_uniformity: "Byte Uniformity",
  repeated_chunk_ratio: "Repeated Chunks",
  signature_flags: "Signature Flags",
};

interface SignalBreakdownProps {
  signals: DetectionSignal[];
}

export function SignalBreakdown({ signals }: SignalBreakdownProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {signals.map((signal) => {
        const percentage = signal.score * 100;
        const color = getConfidenceColor(percentage);

        return (
          <div
            key={signal.name}
            className="bg-gray-800/50 border border-gray-700 rounded-xl p-4"
          >
            <div className="flex items-center gap-2 mb-3">
              <div className="text-gray-400">
                {signalIcons[signal.name] || <Search className="h-5 w-5" />}
              </div>
              <h4 className="font-medium text-white text-sm">
                {signalLabels[signal.name] || signal.name}
              </h4>
              <span className="ml-auto text-sm font-mono" style={{ color }}>
                {percentage.toFixed(0)}%
              </span>
            </div>

            <div className="w-full bg-gray-700 rounded-full h-2 mb-3">
              <div
                className="h-2 rounded-full transition-all duration-700 ease-out"
                style={{ width: `${percentage}%`, backgroundColor: color }}
              />
            </div>

            <p className="text-xs text-gray-400 leading-relaxed">
              {signal.description}
            </p>
          </div>
        );
      })}
    </div>
  );
}
