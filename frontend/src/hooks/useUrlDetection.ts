"use client";

import { useState } from "react";
import { detectUrl } from "@/lib/api";
import { DetectionResult } from "@/lib/types";

type Status = "idle" | "loading" | "success" | "error";

function normalizeUrlError(rawMessage: string): string {
  const message = rawMessage.toLowerCase();

  if (message.includes("cannot reach api") || message.includes("failed to fetch")) {
    return "Network/CORS issue: API endpoint is unreachable from this browser right now.";
  }
  if (message.includes("platform page detected but no public direct media found")) {
    return "Platform page detected but no public direct media found. Use a public post link or a direct media URL.";
  }
  if (message.includes("unsupported content type")) {
    return "Unsupported URL content. Use text/article pages or direct image/video media links.";
  }
  if (message.includes("exceeds maximum size")) {
    return "Media file is larger than the current analysis size limit.";
  }
  if (message.includes("rate limit")) {
    return "Rate limit reached. Wait a moment and retry.";
  }
  if (message.includes("status code 401") || message.includes("status code 403")) {
    return "This page likely requires authentication and cannot be analyzed publicly.";
  }
  if (message.includes("status code 404")) {
    return "URL returned 404. Verify the link and try again.";
  }
  return rawMessage;
}

export function useUrlDetection() {
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function analyze(url: string) {
    setStatus("loading");
    setError(null);
    setResult(null);

    try {
      const data = await detectUrl(url);
      setResult(data);
      setStatus("success");
    } catch (err) {
      const message = err instanceof Error ? err.message : "URL analysis failed";
      setError(normalizeUrlError(message));
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
