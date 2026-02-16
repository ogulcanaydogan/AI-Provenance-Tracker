"use client";

import { useState } from "react";
import { detectText } from "@/lib/api";
import { DetectionResult } from "@/lib/types";

type Status = "idle" | "loading" | "success" | "error";

export function useTextDetection() {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function analyze(text: string) {
    setStatus("loading");
    setError(null);
    setResult(null);

    try {
      const data = await detectText(text);
      setResult(data);
      setStatus("success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Analysis failed";
      setError(message);
      setStatus("error");
    }
  }

  function reset() {
    setStatus("idle");
    setResult(null);
    setError(null);
  }

  return { status, result, error, analyze, reset };
}
