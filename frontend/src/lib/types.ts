export type ContentType = "text" | "image" | "audio" | "video";

export type Verdict =
  | "human"
  | "likely_human"
  | "uncertain"
  | "likely_ai"
  | "ai_generated";

export interface DetectionSignal {
  name: string;
  score: number; // 0-1
  weight: number; // 0-1
  description: string;
}

export interface DetectionResult {
  id: string;
  content_type: ContentType;
  confidence_score: number; // 0-100
  verdict: Verdict;
  signals: DetectionSignal[];
  summary: string;
  analyzed_at: string;
  model_prediction?: string | null;
}

export interface HistoryResponse {
  items: DetectionResult[];
  total: number;
  page: number;
  per_page: number;
}

export interface TextDetectionAnalysis {
  perplexity: number;
  burstiness: number;
  vocabulary_richness: number;
  average_sentence_length: number;
  repetition_score: number;
}

export interface ImageDetectionAnalysis {
  frequency_anomaly: number;
  artifact_score: number;
  metadata_flags: string[];
  compression_analysis: string | null;
}

export interface AudioDetectionAnalysis {
  sample_rate: number;
  duration_seconds: number;
  channel_count: number;
  spectral_flatness: number;
  dynamic_range: number;
  clipping_ratio: number;
  zero_crossing_rate: number;
}

export interface VideoDetectionAnalysis {
  file_size_mb: number;
  entropy_score: number;
  byte_uniformity: number;
  repeated_chunk_ratio: number;
  signature_flags: string[];
}

export interface BackendConsensusVote {
  provider: string;
  probability: number;
  weight: number;
  status: "ok" | "unavailable" | "unsupported" | "error";
  rationale: string;
}

export interface BackendConsensusSummary {
  final_probability: number;
  threshold: number;
  is_ai_generated: boolean;
  disagreement: number;
  providers: BackendConsensusVote[];
}

export interface BackendTextDetectionResponse {
  analysis_id?: string | null;
  is_ai_generated: boolean;
  confidence: number; // 0-1
  model_prediction: string | null;
  analysis: TextDetectionAnalysis;
  explanation: string;
  processing_time_ms: number;
  consensus?: BackendConsensusSummary | null;
}

export interface BackendImageDetectionResponse {
  analysis_id?: string | null;
  is_ai_generated: boolean;
  confidence: number; // 0-1
  model_prediction: string | null;
  analysis: ImageDetectionAnalysis;
  explanation: string;
  filename: string;
  dimensions: [number, number];
  processing_time_ms: number;
  consensus?: BackendConsensusSummary | null;
}

export interface BackendAudioDetectionResponse {
  analysis_id?: string | null;
  is_ai_generated: boolean;
  confidence: number; // 0-1
  model_prediction: string | null;
  analysis: AudioDetectionAnalysis;
  explanation: string;
  filename: string;
  processing_time_ms: number;
  consensus?: BackendConsensusSummary | null;
}

export interface BackendVideoDetectionResponse {
  analysis_id?: string | null;
  is_ai_generated: boolean;
  confidence: number; // 0-1
  model_prediction: string | null;
  analysis: VideoDetectionAnalysis;
  explanation: string;
  filename: string;
  processing_time_ms: number;
  consensus?: BackendConsensusSummary | null;
}

export type BackendDetectionResponse =
  | BackendTextDetectionResponse
  | BackendImageDetectionResponse
  | BackendAudioDetectionResponse
  | BackendVideoDetectionResponse;

export interface BackendHistoryItem {
  analysis_id: string;
  content_type: ContentType;
  is_ai_generated: boolean;
  confidence: number;
  model_prediction: string | null;
  created_at: string;
  source: string;
  source_url: string | null;
  explanation: string;
}

export interface BackendHistoryResponse {
  items: BackendHistoryItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface BackendDetailedAnalysisResponse {
  content_id: string;
  analysis_type: ContentType;
  details: {
    analysis_id: string;
    content_type: ContentType;
    result: BackendDetectionResponse;
  };
  metadata?: {
    created_at?: string;
  };
}

export interface BackendDashboardSummary {
  total_analyses_all_time: number;
  total_analyses_window: number;
  ai_detected_window: number;
  human_detected_window: number;
  ai_rate_window: number;
  average_confidence_window: number;
}

export interface BackendDashboardTimelineItem {
  date: string;
  total: number;
  ai_detected: number;
  human_detected: number;
}

export interface BackendDashboardResponse {
  window_days: number;
  summary: BackendDashboardSummary;
  by_type_window: Record<string, number>;
  by_source_window: Record<string, number>;
  top_models_window: Array<{ model: string; count: number }>;
  alerts_window?: Array<{ code: string; severity: string; message: string }>;
  timeline: BackendDashboardTimelineItem[];
}

export interface BackendEvaluationTrendItem {
  date: string;
  generated_at: string;
  content_type: string;
  sample_count: number;
  threshold: number;
  precision: number;
  recall: number;
  f1: number;
  accuracy: number;
}

export interface BackendEvaluationResponse {
  window_days: number;
  total_reports: number;
  by_content_type: Record<string, number>;
  latest_by_content_type: Record<
    string,
    {
      generated_at: string;
      sample_count: number;
      recommended_threshold: number;
      precision: number;
      recall: number;
      f1: number;
      accuracy: number;
    }
  >;
  trend: BackendEvaluationTrendItem[];
  alerts: Array<{ severity: string; code: string; message: string }>;
}

export interface BackendXCollectEstimateRequest {
  window_days: number;
  max_posts: number;
  max_pages?: number;
}

export interface BackendXCollectEstimateResponse {
  estimated_requests: number;
  worst_case_requests: number;
  page_cap: number;
  target_limit: number;
  mention_limit: number;
  interaction_limit: number;
  guard_enabled: boolean;
  max_requests_per_run: number;
  within_budget: boolean;
  recommended_max_posts: number;
}
