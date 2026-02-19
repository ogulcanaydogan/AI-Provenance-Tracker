"use client";

import { useState } from "react";
import { detectTextStream } from "@/lib/api";
import { DetectionResult } from "@/lib/types";

type Status = "idle" | "loading" | "success" | "error";

export function useTextDetection() {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);

  async function analyze(text: string) {
    setStatus("loading");
    setError(null);
    setResult(null);
    setProgressMessage("Starting analysis...");

    try {
      const data = await detectTextStream(text, (progress) => {
        setProgressMessage(progress.message);
      });
      setResult(data);
      setStatus("success");
      setProgressMessage(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Analysis failed";
      setError(message);
      setStatus("error");
      setProgressMessage(null);
    }
  }

  function reset() {
    setStatus("idle");
    setResult(null);
    setError(null);
    setProgressMessage(null);
  }

  return { status, result, error, progressMessage, analyze, reset };
}
