import {
  BackendDashboardResponse,
  BackendDetailedAnalysisResponse,
  BackendDetectionResponse,
  BackendEvaluationResponse,
  BackendHistoryItem,
  BackendHistoryResponse,
  BackendXCollectEstimateRequest,
  BackendXCollectEstimateResponse,
  DetectionResult,
  DetectionSignal,
  HistoryResponse,
  Verdict,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type TextStreamEvent =
  | "started"
  | "internal"
  | "consensus"
  | "result"
  | "done"
  | "error";

export interface TextStreamProgress {
  event: TextStreamEvent;
  stage: string;
  message: string;
  payload: Record<string, unknown>;
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function toPercent(value: number): number {
  return Number((clamp(value, 0, 1) * 100).toFixed(1));
}

function toVerdict(isAi: boolean, confidence: number): Verdict {
  const normalized = clamp(confidence, 0, 1);

  if (isAi) {
    if (normalized >= 0.85) return "ai_generated";
    if (normalized >= 0.6) return "likely_ai";
    return "uncertain";
  }

  if (normalized <= 0.15) return "human";
  if (normalized <= 0.4) return "likely_human";
  return "uncertain";
}

function buildTextSignals(result: BackendDetectionResponse): DetectionSignal[] {
  if (!("perplexity" in result.analysis)) {
    return [];
  }

  const analysis = result.analysis;

  const perplexityScore = clamp((30 - analysis.perplexity) / 30, 0, 1);
  const burstinessScore = clamp(1 - analysis.burstiness, 0, 1);
  const vocabularyCenter = 0.45;
  const vocabularyScore = clamp(
    1 - Math.abs(analysis.vocabulary_richness - vocabularyCenter) / vocabularyCenter,
    0,
    1
  );
  const repetitionScore = clamp(analysis.repetition_score, 0, 1);

  return [
    {
      name: "perplexity",
      score: perplexityScore,
      weight: 0.3,
      description: `Perplexity: ${analysis.perplexity.toFixed(2)}. Lower values are generally more AI-like.`,
    },
    {
      name: "burstiness",
      score: burstinessScore,
      weight: 0.25,
      description: `Burstiness: ${(analysis.burstiness * 100).toFixed(0)}%. Lower variation can indicate AI output.`,
    },
    {
      name: "vocabulary",
      score: vocabularyScore,
      weight: 0.2,
      description: `Vocabulary richness: ${(analysis.vocabulary_richness * 100).toFixed(0)}%.`,
    },
    {
      name: "ml_classifier",
      score: repetitionScore,
      weight: 0.25,
      description: `Repetition score: ${(analysis.repetition_score * 100).toFixed(0)}%.`,
    },
  ];
}

function metadataScore(flags: string[]): number {
  let score = 0;
  if (flags.includes("missing_exif")) score += 0.4;
  if (flags.includes("no_camera_info")) score += 0.2;
  if (flags.includes("unusual_compression")) score += 0.2;
  if (flags.includes("ai_software_tag")) score += 0.8;
  return clamp(score, 0, 1);
}

function buildImageSignals(result: BackendDetectionResponse): DetectionSignal[] {
  if (!("frequency_anomaly" in result.analysis)) {
    return [];
  }

  const analysis = result.analysis;

  return [
    {
      name: "frequency_analysis",
      score: clamp(analysis.frequency_anomaly, 0, 1),
      weight: 0.35,
      description: `Frequency anomaly: ${(analysis.frequency_anomaly * 100).toFixed(0)}%.`,
    },
    {
      name: "artifacts",
      score: clamp(analysis.artifact_score, 0, 1),
      weight: 0.35,
      description: `Artifact score: ${(analysis.artifact_score * 100).toFixed(0)}%.`,
    },
    {
      name: "metadata",
      score: metadataScore(analysis.metadata_flags),
      weight: 0.3,
      description:
        analysis.metadata_flags.length > 0
          ? `Metadata flags: ${analysis.metadata_flags.join(", ")}.`
          : "No suspicious metadata flags found.",
    },
  ];
}

function buildAudioSignals(result: BackendDetectionResponse): DetectionSignal[] {
  if (!("spectral_flatness" in result.analysis)) {
    return [];
  }

  const analysis = result.analysis;

  return [
    {
      name: "spectral_flatness",
      score: clamp(analysis.spectral_flatness, 0, 1),
      weight: 0.35,
      description: `Spectral flatness: ${(analysis.spectral_flatness * 100).toFixed(0)}%.`,
    },
    {
      name: "dynamic_range",
      score: clamp(1 - analysis.dynamic_range, 0, 1),
      weight: 0.3,
      description: `Dynamic range: ${(analysis.dynamic_range * 100).toFixed(0)}%. Lower can indicate synthesis.`,
    },
    {
      name: "clipping_ratio",
      score: clamp(analysis.clipping_ratio / 0.05, 0, 1),
      weight: 0.2,
      description: `Clipping ratio: ${(analysis.clipping_ratio * 100).toFixed(2)}%.`,
    },
    {
      name: "zero_crossing_rate",
      score: clamp(analysis.zero_crossing_rate, 0, 1),
      weight: 0.15,
      description: `Zero-crossing rate: ${(analysis.zero_crossing_rate * 100).toFixed(2)}%.`,
    },
  ];
}

function buildVideoSignals(result: BackendDetectionResponse): DetectionSignal[] {
  if (!("entropy_score" in result.analysis)) {
    return [];
  }

  const analysis = result.analysis;
  const signatureScore = clamp(analysis.signature_flags.length / 4, 0, 1);

  return [
    {
      name: "entropy_score",
      score: clamp(analysis.entropy_score / 8, 0, 1),
      weight: 0.3,
      description: `Byte entropy: ${analysis.entropy_score.toFixed(2)} / 8.`,
    },
    {
      name: "byte_uniformity",
      score: clamp(analysis.byte_uniformity, 0, 1),
      weight: 0.25,
      description: `Byte uniformity: ${(analysis.byte_uniformity * 100).toFixed(0)}%.`,
    },
    {
      name: "repeated_chunk_ratio",
      score: clamp(analysis.repeated_chunk_ratio, 0, 1),
      weight: 0.25,
      description: `Repeated chunk ratio: ${(analysis.repeated_chunk_ratio * 100).toFixed(2)}%.`,
    },
    {
      name: "signature_flags",
      score: signatureScore,
      weight: 0.2,
      description:
        analysis.signature_flags.length > 0
          ? `Signature flags: ${analysis.signature_flags.join(", ")}.`
          : "No notable signature flags.",
    },
  ];
}

function mapDetection(
  payload: BackendDetectionResponse,
  contentType: "text" | "image" | "audio" | "video",
  analyzedAt?: string
): DetectionResult {
  const confidence = clamp(payload.confidence, 0, 1);

  return {
    id: payload.analysis_id || `${contentType}-${Date.now()}`,
    content_type: contentType,
    confidence_score: toPercent(confidence),
    verdict: toVerdict(payload.is_ai_generated, confidence),
    signals:
      contentType === "text"
        ? buildTextSignals(payload)
        : contentType === "image"
        ? buildImageSignals(payload)
        : contentType === "audio"
        ? buildAudioSignals(payload)
        : buildVideoSignals(payload),
    summary: payload.explanation,
    analyzed_at: analyzedAt || new Date().toISOString(),
    model_prediction: payload.model_prediction,
  };
}

function mapHistoryItem(item: BackendHistoryItem): DetectionResult {
  return {
    id: item.analysis_id,
    content_type: item.content_type,
    confidence_score: toPercent(item.confidence),
    verdict: toVerdict(item.is_ai_generated, item.confidence),
    signals: [],
    summary: item.explanation || "No explanation available.",
    analyzed_at: item.created_at,
    model_prediction: item.model_prediction,
  };
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

export async function detectText(text: string): Promise<DetectionResult> {
  const response = await fetch(`${API_URL}/api/v1/detect/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const payload = await handleResponse<BackendDetectionResponse>(response);
  return mapDetection(payload, "text");
}

function streamMessage(event: TextStreamEvent, payload: Record<string, unknown>): string {
  if (event === "started") return "Text received, detection started.";
  if (event === "internal") return "Internal detector finished. Computing consensus.";
  if (event === "consensus") {
    const value = payload.final_probability;
    const formatted = typeof value === "number" ? `${(value * 100).toFixed(1)}%` : "n/a";
    return `Consensus complete (${formatted}). Preparing final result.`;
  }
  if (event === "result") return "Final result received.";
  if (event === "done") return "Streaming analysis completed.";
  if (event === "error") return "Streaming analysis failed.";
  return "Streaming update received.";
}

function parseSseBlock(block: string): {
  event: TextStreamEvent;
  payload: Record<string, unknown>;
} | null {
  const lines = block
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) return null;

  let event: TextStreamEvent | null = null;
  const dataParts: string[] = [];
  for (const line of lines) {
    if (line.startsWith("event:")) {
      const rawEvent = line.replace("event:", "").trim();
      if (
        rawEvent === "started" ||
        rawEvent === "internal" ||
        rawEvent === "consensus" ||
        rawEvent === "result" ||
        rawEvent === "done" ||
        rawEvent === "error"
      ) {
        event = rawEvent;
      }
    } else if (line.startsWith("data:")) {
      dataParts.push(line.replace("data:", "").trim());
    }
  }

  if (!event) return null;

  const rawData = dataParts.join("\n");
  if (!rawData) {
    return { event, payload: {} };
  }

  try {
    const parsed = JSON.parse(rawData);
    if (parsed && typeof parsed === "object") {
      return { event, payload: parsed as Record<string, unknown> };
    }
  } catch {
    // Ignore malformed payloads; handled by caller through missing fields.
  }
  return { event, payload: {} };
}

export async function detectTextStream(
  text: string,
  onProgress?: (progress: TextStreamProgress) => void,
): Promise<DetectionResult> {
  const response = await fetch(`${API_URL}/api/v1/detect/stream/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });

  // Fallback to non-stream endpoint for environments where SSE route is unavailable.
  if (!response.ok && response.status === 404) {
    return detectText(text);
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  if (!response.body) {
    return detectText(text);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalPayload: BackendDetectionResponse | null = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      const parsed = parseSseBlock(block);
      if (!parsed) continue;

      const stage =
        typeof parsed.payload.stage === "string"
          ? parsed.payload.stage
          : parsed.event;
      onProgress?.({
        event: parsed.event,
        stage,
        message: streamMessage(parsed.event, parsed.payload),
        payload: parsed.payload,
      });

      if (parsed.event === "error") {
        const detail =
          typeof parsed.payload.detail === "string"
            ? parsed.payload.detail
            : "Streaming analysis failed";
        throw new Error(detail);
      }

      if (parsed.event === "result") {
        finalPayload = parsed.payload as unknown as BackendDetectionResponse;
      }
    }
  }

  if (!finalPayload) {
    return detectText(text);
  }
  return mapDetection(finalPayload, "text");
}

export async function detectImage(file: File): Promise<DetectionResult> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/api/v1/detect/image`, {
    method: "POST",
    body: formData,
  });
  const payload = await handleResponse<BackendDetectionResponse>(response);
  return mapDetection(payload, "image");
}

export async function detectAudio(file: File): Promise<DetectionResult> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/api/v1/detect/audio`, {
    method: "POST",
    body: formData,
  });
  const payload = await handleResponse<BackendDetectionResponse>(response);
  return mapDetection(payload, "audio");
}

export async function detectVideo(file: File): Promise<DetectionResult> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_URL}/api/v1/detect/video`, {
    method: "POST",
    body: formData,
  });
  const payload = await handleResponse<BackendDetectionResponse>(response);
  return mapDetection(payload, "video");
}

export async function getHistory(
  page = 1,
  perPage = 20,
  contentType?: string,
): Promise<HistoryResponse> {
  const offset = (page - 1) * perPage;
  const params = new URLSearchParams({
    limit: String(perPage),
    offset: String(offset),
  });
  if (contentType) params.set("content_type", contentType);

  const response = await fetch(
    `${API_URL}/api/v1/analyze/history?${params.toString()}`
  );
  const payload = await handleResponse<BackendHistoryResponse>(response);

  return {
    items: payload.items.map(mapHistoryItem),
    total: payload.total,
    page,
    per_page: perPage,
  };
}

export function getExportUrl(
  endpoint: "history" | "dashboard",
  format: "csv" | "json",
  options?: { days?: number; contentType?: string },
): string {
  const base = `${API_URL}/api/v1/analyze/${endpoint}/export`;
  const params = new URLSearchParams({ format });
  if (options?.days) params.set("days", String(options.days));
  if (options?.contentType) params.set("content_type", options.contentType);
  return `${base}?${params.toString()}`;
}

export async function getAnalysis(id: string): Promise<DetectionResult> {
  const response = await fetch(`${API_URL}/api/v1/analyze/detailed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      content_id: id,
      include_metadata: true,
      include_timeline: false,
    }),
  });
  const payload = await handleResponse<BackendDetailedAnalysisResponse>(response);

  return mapDetection(
    payload.details.result,
    payload.details.content_type,
    payload.metadata?.created_at
  );
}

export async function getDashboard(days = 14): Promise<BackendDashboardResponse> {
  const boundedDays = Math.max(1, Math.min(days, 90));
  const response = await fetch(`${API_URL}/api/v1/analyze/dashboard?days=${boundedDays}`);
  return handleResponse<BackendDashboardResponse>(response);
}

export async function getEvaluation(days = 90): Promise<BackendEvaluationResponse> {
  const boundedDays = Math.max(1, Math.min(days, 365));
  const response = await fetch(`${API_URL}/api/v1/analyze/evaluation?days=${boundedDays}`);
  return handleResponse<BackendEvaluationResponse>(response);
}

export async function getXCollectEstimate(
  payload: BackendXCollectEstimateRequest
): Promise<BackendXCollectEstimateResponse> {
  const boundedWindowDays = Math.max(1, Math.min(payload.window_days, 90));
  const boundedMaxPosts = Math.max(20, Math.min(payload.max_posts, 1000));
  const boundedMaxPages =
    payload.max_pages === undefined
      ? undefined
      : Math.max(1, Math.min(payload.max_pages, 10));

  const response = await fetch(`${API_URL}/api/v1/intel/x/collect/estimate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      window_days: boundedWindowDays,
      max_posts: boundedMaxPosts,
      ...(boundedMaxPages ? { max_pages: boundedMaxPages } : {}),
    }),
  });
  return handleResponse<BackendXCollectEstimateResponse>(response);
}
