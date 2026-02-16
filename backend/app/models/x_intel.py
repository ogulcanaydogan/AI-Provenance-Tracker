"""Models for X (Twitter) intelligence data collection."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RoleHint = Literal["seed", "amplifier", "bridge"]
Confidence = Literal["low", "medium", "high"]
RiskTolerance = Literal["low", "medium", "high"]
UserProfile = Literal["influencer", "brand", "journalist", "politician", "startup_ceo"]
LegalPrCapacity = Literal["none", "basic", "advanced"]
Goal = Literal[
    "reputation_protection",
    "crisis_response",
    "brand_safety",
    "misinfo_mitigation",
]


class XPostMetrics(BaseModel):
    """Tweet-level engagement metrics."""

    likes: int = 0
    reposts: int = 0
    replies: int = 0
    views: int = 0


class XAuthor(BaseModel):
    """Normalized author metadata."""

    user_id: str
    handle: str
    created_at: str
    followers: int = 0
    following: int = 0
    verified: bool = False
    profile_fields: dict[str, Any] = Field(default_factory=dict)


class XPost(BaseModel):
    """Normalized post shape required by downstream analyzer."""

    tweet_id: str
    created_at: str
    text: str
    lang: str
    media_urls: list[str] = Field(default_factory=list)
    metrics: XPostMetrics
    author: XAuthor
    reply_to: str | None = None
    quoted_tweet_id: str | None = None
    urls: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)


class ClusterTopAccount(BaseModel):
    """High-impact account in a coordinated cluster."""

    user_id: str
    handle: str
    role_hint: RoleHint


class ClusterTopPost(BaseModel):
    """Representative post in a coordinated cluster."""

    tweet_id: str
    text: str
    created_at: str
    urls: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)


class CoordinatedCluster(BaseModel):
    """Detected coordinated activity cluster."""

    cluster_id: str
    size: int
    shared_hashtags: list[str] = Field(default_factory=list)
    shared_urls: list[str] = Field(default_factory=list)
    time_burst_score: float = 0.0
    text_similarity_score: float = 0.0
    top_accounts: list[ClusterTopAccount] = Field(default_factory=list)
    top_posts: list[ClusterTopPost] = Field(default_factory=list)


class CentralAccount(BaseModel):
    """Central node in amplification graph."""

    handle: str
    score: float


class AmplificationGraphMetrics(BaseModel):
    """Graph-level amplification metrics."""

    density: float = 0.0
    modularity: float = 0.0
    central_accounts: list[CentralAccount] = Field(default_factory=list)


class NetworkSignals(BaseModel):
    """Network-level coordination signals."""

    coordinated_clusters: list[CoordinatedCluster] = Field(default_factory=list)
    amplification_graph_metrics: AmplificationGraphMetrics


class BotFeature(BaseModel):
    """Single bot feature explanation."""

    feature: str
    value: str
    why_it_matters: str


class BotScore(BaseModel):
    """Account-level bot likelihood signal."""

    user_id: str
    handle: str
    bot_probability: float
    top_features: list[BotFeature] = Field(default_factory=list)
    confidence: Confidence


class AIContentScore(BaseModel):
    """Tweet-level AI content likelihood score."""

    tweet_id: str
    ai_text_probability: float
    ai_image_probability: float
    provenance_notes: list[str] = Field(default_factory=list)
    confidence: Confidence


class ClaimCluster(BaseModel):
    """Narrative cluster extracted from posts."""

    cluster_id: str
    topic_label: str
    representative_claims: list[str] = Field(default_factory=list)
    spread_over_time: str
    key_accounts: list[str] = Field(default_factory=list)
    sentiment: str


class UserContext(BaseModel):
    """User context required by downstream strategy engine."""

    sector: str = "unknown"
    risk_tolerance: RiskTolerance = "medium"
    preferred_language: str = "tr"
    user_profile: UserProfile = "brand"
    legal_pr_capacity: LegalPrCapacity = "basic"
    goal: Goal = "reputation_protection"


class XIntelCollectionRequest(BaseModel):
    """Request payload for X data collection."""

    target_handle: str = Field(..., description="Target X handle, with or without @")
    window_days: int = Field(default=14, ge=1, le=90)
    max_posts: int = Field(default=250, ge=20, le=1000)
    query: str | None = Field(
        default=None,
        description="Optional X search query for broader topic collection",
    )
    user_context: UserContext | None = None


class XIntelEstimateRequest(BaseModel):
    """Request payload for no-network request-cost preflight."""

    window_days: int = Field(default=14, ge=1, le=90)
    max_posts: int = Field(default=250, ge=20, le=1000)
    max_pages: int | None = Field(default=None, ge=1, le=10)


class XIntelEstimateResponse(BaseModel):
    """Response payload for no-network request-cost preflight."""

    estimated_requests: int
    worst_case_requests: int
    page_cap: int
    target_limit: int
    mention_limit: int
    interaction_limit: int
    guard_enabled: bool
    max_requests_per_run: int
    within_budget: bool
    recommended_max_posts: int


class XIntelInput(BaseModel):
    """Final input contract for trust and safety report generation."""

    target: str
    window: str
    posts: list[XPost] = Field(default_factory=list)
    network_signals: NetworkSignals
    bot_scores: list[BotScore] = Field(default_factory=list)
    ai_content_scores: list[AIContentScore] = Field(default_factory=list)
    claim_clusters: list[ClaimCluster] = Field(default_factory=list)
    user_context: UserContext
