"use client";

interface TextAnalysis {
  perplexity: number;
  burstiness: number;
  vocabulary_richness: number;
  average_sentence_length: number;
  repetition_score: number;
}

interface ImageAnalysis {
  frequency_anomaly: number;
  artifact_score: number;
  metadata_flags: string[];
  compression_analysis: string | null;
}

interface ResultCardProps {
  type: "text" | "image";
  isAiGenerated: boolean;
  confidence: number;
  modelPrediction: string | null;
  explanation: string;
  processingTime: number;
  analysis: TextAnalysis | ImageAnalysis;
  dimensions?: [number, number];
}

export default function ResultCard({
  type,
  isAiGenerated,
  confidence,
  modelPrediction,
  explanation,
  processingTime,
  analysis,
  dimensions,
}: ResultCardProps) {
  const confidencePercent = (confidence * 100).toFixed(1);
  const confidenceClass =
    confidence > 0.75
      ? "confidence-high"
      : confidence > 0.5
      ? "confidence-medium"
      : "confidence-low";

  const isTextAnalysis = (a: TextAnalysis | ImageAnalysis): a is TextAnalysis => {
    return "perplexity" in a;
  };

  return (
    <div className="mt-6 p-6 bg-[#0a0a0a] border border-[#262626] rounded-lg">
      {/* Main Result */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div
            className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl ${
              isAiGenerated ? "bg-red-900/30" : "bg-green-900/30"
            }`}
          >
            {isAiGenerated ? "🤖" : "👤"}
          </div>
          <div>
            <h3 className="font-semibold text-lg">
              {isAiGenerated ? "Likely AI-Generated" : "Likely Human-Created"}
            </h3>
            {modelPrediction && (
              <p className="text-gray-500 text-sm">
                Predicted model: {modelPrediction}
              </p>
            )}
          </div>
        </div>

        <div className="text-right">
          <div className={`text-3xl font-bold ${confidenceClass}`}>
            {confidencePercent}%
          </div>
          <div className="text-gray-500 text-sm">confidence</div>
        </div>
      </div>

      {/* Explanation */}
      <div className="mb-6 p-4 bg-[#171717] rounded-lg">
        <p className="text-gray-300">{explanation}</p>
      </div>

      {/* Analysis Details */}
      <div className="mb-4">
        <h4 className="font-medium mb-3 text-gray-400">Analysis Details</h4>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {isTextAnalysis(analysis) ? (
            <>
              <MetricCard
                label="Perplexity"
                value={analysis.perplexity.toFixed(2)}
                description="Lower = more predictable"
              />
              <MetricCard
                label="Burstiness"
                value={(analysis.burstiness * 100).toFixed(1) + "%"}
                description="Sentence variation"
              />
              <MetricCard
                label="Vocabulary"
                value={(analysis.vocabulary_richness * 100).toFixed(1) + "%"}
                description="Word variety"
              />
              <MetricCard
                label="Avg Sentence"
                value={analysis.average_sentence_length.toFixed(1) + " words"}
                description="Sentence length"
              />
              <MetricCard
                label="Repetition"
                value={(analysis.repetition_score * 100).toFixed(1) + "%"}
                description="Phrase patterns"
              />
            </>
          ) : (
            <>
              <MetricCard
                label="Frequency Anomaly"
                value={(analysis.frequency_anomaly * 100).toFixed(1) + "%"}
                description="FFT pattern score"
              />
              <MetricCard
                label="Artifact Score"
                value={(analysis.artifact_score * 100).toFixed(1) + "%"}
                description="Generation artifacts"
              />
              {dimensions && (
                <MetricCard
                  label="Dimensions"
                  value={`${dimensions[0]}×${dimensions[1]}`}
                  description="Image size"
                />
              )}
              {analysis.compression_analysis && (
                <MetricCard
                  label="Compression"
                  value={analysis.compression_analysis.replace("_", " ")}
                  description="File compression"
                />
              )}
            </>
          )}
        </div>

        {/* Metadata Flags for Images */}
        {!isTextAnalysis(analysis) && analysis.metadata_flags.length > 0 && (
          <div className="mt-4">
            <h5 className="text-sm text-gray-500 mb-2">Metadata Flags</h5>
            <div className="flex flex-wrap gap-2">
              {analysis.metadata_flags.map((flag, i) => (
                <span
                  key={i}
                  className="px-2 py-1 bg-yellow-900/30 text-yellow-500 text-xs rounded"
                >
                  {flag.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="pt-4 border-t border-[#262626] text-xs text-gray-600">
        Processed in {processingTime.toFixed(0)}ms
      </div>
    </div>
  );
}

function MetricCard({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description: string;
}) {
  return (
    <div className="p-3 bg-[#171717] rounded-lg">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="font-semibold">{value}</div>
      <div className="text-xs text-gray-600">{description}</div>
    </div>
  );
}
