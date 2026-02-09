"use client";

import { useState } from "react";
import ResultCard from "./ResultCard";

interface TextAnalysis {
  perplexity: number;
  burstiness: number;
  vocabulary_richness: number;
  average_sentence_length: number;
  repetition_score: number;
}

interface DetectionResult {
  is_ai_generated: boolean;
  confidence: number;
  model_prediction: string | null;
  analysis: TextAnalysis;
  explanation: string;
  processing_time_ms: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://ai-provenance-tracker-production-4622.up.railway.app";

export default function TextDetector() {
  const [text, setText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!text.trim()) {
      setError("Please enter some text to analyze");
      return;
    }

    setIsLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/api/v1/detect/text`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      if (!response.ok) {
        throw new Error(`Detection failed: ${response.statusText}`);
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setText("");
    setResult(null);
    setError(null);
  };

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <div className="mb-4">
          <label htmlFor="text-input" className="block text-sm font-medium mb-2">
            Enter text to analyze
          </label>
          <textarea
            id="text-input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste the text you want to analyze for AI generation..."
            className="w-full h-48 p-4 bg-[#0a0a0a] border border-[#262626] rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            maxLength={50000}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>{text.length.toLocaleString()} / 50,000 characters</span>
            <span>{text.split(/\s+/).filter(Boolean).length} words</span>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={isLoading || !text.trim()}
            className="btn-primary flex-1 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <span className="animate-spin">⏳</span>
                Analyzing...
              </>
            ) : (
              <>
                <span>🔍</span>
                Analyze Text
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleClear}
            className="px-6 py-3 bg-[#262626] text-gray-400 rounded-lg hover:bg-[#333] transition-colors"
          >
            Clear
          </button>
        </div>
      </form>

      {result && (
        <ResultCard
          type="text"
          isAiGenerated={result.is_ai_generated}
          confidence={result.confidence}
          modelPrediction={result.model_prediction}
          explanation={result.explanation}
          processingTime={result.processing_time_ms}
          analysis={result.analysis}
        />
      )}
    </div>
  );
}
