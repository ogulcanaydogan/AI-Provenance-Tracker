"""Trust and safety report generation from normalized X intelligence input."""

from __future__ import annotations

from collections import Counter
from datetime import date
from datetime import UTC, datetime
import re
from typing import Any

from app.models.x_intel import XIntelInput

SCAM_HINTS = ("airdrop", "telegram", "whatsapp", "dm ", "dm me", "wallet", "seed phrase")
SMEAR_HINTS = ("fraud", "scam", "liar", "fake", "corrupt", "blackmail", "kill")
POLITICAL_HINTS = ("election", "party", "ideology", "president", "parliament", "government")
ENGAGEMENT_HINTS = ("follow", "retweet", "like", "share", "giveaway")


class TrustReportGenerator:
    """Generate explainable trust-and-safety report JSON."""

    def generate(self, payload: XIntelInput | dict[str, Any]) -> dict[str, Any]:
        """Build a schema-compliant report from XIntelInput."""
        data = payload if isinstance(payload, XIntelInput) else XIntelInput.model_validate(payload)

        posts = data.posts
        clusters = data.network_signals.coordinated_clusters
        bot_scores = data.bot_scores
        ai_scores = data.ai_content_scores
        claim_clusters = data.claim_clusters
        context = data.user_context

        post_count = len(posts)
        unique_accounts = len({post.author.handle.lower() for post in posts})
        max_bot_probability = max((score.bot_probability for score in bot_scores), default=0.0)

        timeline = self._build_timeline(posts)
        bot_activity = self._build_bot_activity(clusters, bot_scores)
        ai_generated = self._build_ai_content(ai_scores, posts)
        claims = self._build_claims(claim_clusters)
        risk_level = self._infer_risk_level(
            suspected_clusters=bot_activity["suspected_clusters"],
            claims=claims,
            max_bot_probability=max_bot_probability,
            post_count=post_count,
        )

        strategy = self._build_strategy(context.goal, context.risk_tolerance)
        confidence = self._overall_confidence(post_count, len(clusters), unique_accounts)

        return {
            "executive_summary": {
                "risk_level": risk_level,
                "what_is_happening": (
                    f"Collected {post_count} posts for {data.target}. "
                    "Observed narrative-driven discussion with probabilistic bot/AI signals."
                ),
                "why_now": self._why_now(timeline),
                "top_3_findings": [
                    f"post_count={post_count}; unique_accounts={unique_accounts}",
                    f"coordinated_clusters={len(clusters)}",
                    f"max_bot_probability={round(max_bot_probability, 3)}",
                ],
                "risk_rationale": [
                    "All bot/AI judgments are probabilistic and evidence-based.",
                    "Confidence depends on sample size, network coverage, and provenance availability.",
                ],
            },
            "timeline": timeline,
            "bot_activity": bot_activity,
            "ai_generated_content": ai_generated,
            "claims_and_narratives": claims,
            "recommended_strategy": strategy,
            "data_gaps": self._data_gaps(post_count),
            "confidence_overall": confidence,
        }

    def generate_drilldown(self, payload: XIntelInput | dict[str, Any]) -> dict[str, Any]:
        """Build cluster drill-down, claim timeline, and alert list for dashboards."""
        data = payload if isinstance(payload, XIntelInput) else XIntelInput.model_validate(payload)
        claims_timeline = self._claim_timeline(data.posts, data.claim_clusters)
        alerts = self._intel_alerts(data)
        clusters = []
        for cluster in data.network_signals.coordinated_clusters:
            objective, rationale = self._infer_objective(cluster)
            clusters.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "size": cluster.size,
                    "time_burst_score": cluster.time_burst_score,
                    "text_similarity_score": cluster.text_similarity_score,
                    "shared_hashtags": cluster.shared_hashtags,
                    "shared_urls": cluster.shared_urls,
                    "top_accounts": [acct.model_dump() for acct in cluster.top_accounts],
                    "top_posts": [post.model_dump() for post in cluster.top_posts],
                    "likely_objective": objective,
                    "objective_rationale": rationale,
                }
            )
        return {
            "target": data.target,
            "window": data.window,
            "clusters": clusters,
            "claim_timeline": claims_timeline,
            "alerts": alerts,
        }

    def _build_timeline(self, posts: list[Any]) -> list[dict[str, Any]]:
        if not posts:
            return []

        grouped: Counter[str] = Counter()
        for post in posts:
            grouped[post.created_at[:10]] += 1

        timeline: list[dict[str, Any]] = []
        for date, count in sorted(grouped.items()):
            timeline.append(
                {
                    "date": date,
                    "events": [f"{count} posts observed in scope."],
                    "spikes": [f"post_volume={count}"] if count >= 10 else [],
                }
            )
        return timeline

    def _build_bot_activity(self, clusters: list[Any], bot_scores: list[Any]) -> dict[str, Any]:
        bot_map = {score.handle.lower(): score.bot_probability for score in bot_scores}
        suspected_clusters: list[dict[str, Any]] = []

        for cluster in clusters:
            top_accounts: list[dict[str, Any]] = []
            probs: list[float] = []
            for account in cluster.top_accounts:
                probability = bot_map.get(account.handle.lower(), 0.0)
                probs.append(probability)
                top_accounts.append(
                    {
                        "handle": account.handle,
                        "bot_probability": round(probability, 3),
                        "role": account.role_hint,
                    }
                )

            objective, objective_rationale = self._infer_objective(cluster)
            suspected_clusters.append(
                {
                    "cluster_id": cluster.cluster_id,
                    "size": cluster.size,
                    "bot_likelihood": round(sum(probs) / len(probs), 3) if probs else 0.0,
                    "evidence": [
                        f"time_burst_score={cluster.time_burst_score}",
                        f"text_similarity_score={cluster.text_similarity_score}",
                        f"shared_hashtags={len(cluster.shared_hashtags)}",
                        f"shared_urls={len(cluster.shared_urls)}",
                    ],
                    "top_accounts": top_accounts,
                    "likely_objective": objective,
                    "objective_rationale": objective_rationale,
                    "confidence": "high"
                    if cluster.size >= 50 and cluster.text_similarity_score >= 0.7
                    else "medium"
                    if cluster.size >= 15
                    else "low",
                }
            )

        overall = (
            "No strong coordinated bot activity detected in this sample."
            if not suspected_clusters
            else "Potential coordinated activity exists; review clusters with highest bot_likelihood first."
        )

        return {
            "overall_assessment": overall,
            "suspected_clusters": suspected_clusters,
        }

    def _infer_objective(self, cluster: Any) -> tuple[str, list[str]]:
        text_blob = " ".join(post.text.lower() for post in cluster.top_posts)
        shared_urls = " ".join(cluster.shared_urls).lower()

        if any(hint in text_blob or hint in shared_urls for hint in SCAM_HINTS):
            return (
                "scam",
                [
                    "Contains scam-like redirect terms or messaging app pivots.",
                    "URL reuse and burst timing increase campaign risk.",
                    "Classification is probabilistic, not definitive attribution.",
                ],
            )
        if any(hint in text_blob for hint in POLITICAL_HINTS):
            return (
                "political",
                [
                    "Political entities/keywords appear in representative content.",
                    "Cluster structure indicates synchronized amplification signals.",
                    "Requires cross-platform corroboration for high-confidence labeling.",
                ],
            )
        if cluster.text_similarity_score >= 0.7 and len(cluster.shared_hashtags) >= 2:
            return (
                "astroturf",
                [
                    "High text similarity with repeated slogans/hashtags.",
                    "Content appears coordinated while mimicking organic spread.",
                    "No direct scam trigger words observed.",
                ],
            )
        if any(hint in text_blob for hint in SMEAR_HINTS):
            return (
                "smear",
                [
                    "Contains reputation-damaging accusation language.",
                    "Repeated claim framing can indicate coordinated pressure.",
                    "Further validation needed for intent attribution.",
                ],
            )
        if any(hint in text_blob for hint in ENGAGEMENT_HINTS):
            return (
                "engagement_farm",
                [
                    "Engagement-boost prompts appear in cluster text.",
                    "Shared hashtags/URLs can indicate metric-seeking behavior.",
                    "Heuristic-based classification with medium confidence.",
                ],
            )

        return (
            "other",
            [
                "Cluster does not cleanly match predefined objective classes.",
                "Evidence is retained for analyst review.",
                "Treat as watchlist candidate rather than confirmed campaign.",
            ],
        )

    def _build_ai_content(self, ai_scores: list[Any], posts: list[Any]) -> dict[str, Any]:
        post_map = {post.tweet_id: post for post in posts}
        notable = sorted(
            ai_scores,
            key=lambda item: (item.ai_text_probability, item.ai_image_probability),
            reverse=True,
        )[:5]

        notable_items: list[dict[str, Any]] = []
        for item in notable:
            post = post_map.get(item.tweet_id)
            why = [
                f"ai_text_probability={item.ai_text_probability}",
                f"ai_image_probability={item.ai_image_probability}",
            ]
            if post and post.media_urls:
                why.append("Media exists but original binary provenance not verified in this pass.")
            notable_items.append(
                {
                    "tweet_id": item.tweet_id,
                    "ai_probability_text": item.ai_text_probability,
                    "ai_probability_image": item.ai_image_probability,
                    "why_it_looks_ai": why,
                    "provenance_notes": item.provenance_notes,
                    "impact": "high"
                    if item.ai_text_probability >= 0.7 or item.ai_image_probability >= 0.7
                    else "medium"
                    if item.ai_text_probability >= 0.3 or item.ai_image_probability >= 0.3
                    else "low",
                    "confidence": item.confidence,
                }
            )

        overall = (
            "AI-content signals are low-to-moderate and remain probabilistic."
            if notable_items
            else "No AI-content signals were available in this sample."
        )
        return {
            "overall_assessment": overall,
            "notable_items": notable_items,
            "limitations": [
                "AI probability is heuristic/model-based and not legal proof.",
                "Provenance (C2PA/original binary chain) may be unavailable from API-only collection.",
                "High-confidence decisions require independent verification.",
            ],
        }

    def _build_claims(self, claim_clusters: list[Any]) -> list[dict[str, Any]]:
        claims: list[dict[str, Any]] = []
        for cluster in claim_clusters[:10]:
            max_daily = self._max_spread_count(cluster.spread_over_time)
            reach = "high" if max_daily >= 30 else "medium" if max_daily >= 10 else "low"

            topic = cluster.topic_label.lower()
            if any(hint in topic for hint in ("breaking", "fraud", "scam", "blackmail", "kill")):
                response = "debunk"
            elif any(hint in topic for hint in ("anthropic", "claude", "support", "billing")):
                response = "clarify"
            elif reach == "high":
                response = "escalate"
            else:
                response = "ignore"

            claims.append(
                {
                    "topic_label": cluster.topic_label,
                    "representative_claims": cluster.representative_claims[:2],
                    "reach_proxy": reach,
                    "harm_assessment": (
                        "Narrative may influence reputation and should be monitored."
                        if reach in {"medium", "high"}
                        else "Limited observed spread in current sample."
                    ),
                    "recommended_response": response,
                    "response_rationale": [
                        f"spread_over_time={cluster.spread_over_time}",
                        f"sentiment={cluster.sentiment}",
                    ],
                }
            )
        return claims

    def _claim_timeline(self, posts: list[Any], claim_clusters: list[Any]) -> list[dict[str, Any]]:
        topics = [cluster.topic_label for cluster in claim_clusters]
        normalized_topics = [self._normalize_topic_tokens(topic) for topic in topics]
        by_day: dict[date, Counter[str]] = {}

        for post in posts:
            post_day = datetime.fromisoformat(post.created_at.replace("Z", "+00:00")).date()
            bucket = by_day.setdefault(post_day, Counter())
            text_tokens = self._normalize_topic_tokens(post.text)
            for topic_label, topic_tokens in zip(topics, normalized_topics, strict=False):
                if topic_tokens and any(token in text_tokens for token in topic_tokens):
                    bucket[topic_label] += 1

        rows: list[dict[str, Any]] = []
        for day in sorted(by_day):
            counter = by_day[day]
            rows.append(
                {
                    "date": day.isoformat(),
                    "total_mentions": int(sum(counter.values())),
                    "topics": [
                        {"topic_label": topic_label, "count": count}
                        for topic_label, count in counter.most_common(8)
                    ],
                }
            )
        return rows

    @staticmethod
    def _normalize_topic_tokens(text: str) -> set[str]:
        return {token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if len(token) >= 4}

    def _intel_alerts(self, data: XIntelInput) -> list[dict[str, Any]]:
        alerts: list[dict[str, Any]] = []
        clusters = data.network_signals.coordinated_clusters
        claims = data.claim_clusters
        bot_scores = data.bot_scores

        if any(cluster.time_burst_score >= 0.8 and cluster.text_similarity_score >= 0.7 for cluster in clusters):
            alerts.append(
                {
                    "severity": "high",
                    "code": "coordinated_burst",
                    "message": "High burst + text-similarity cluster detected.",
                    "evidence": ["time_burst_score>=0.8", "text_similarity_score>=0.7"],
                }
            )

        if any(score.bot_probability >= 0.8 for score in bot_scores):
            alerts.append(
                {
                    "severity": "medium",
                    "code": "high_bot_probability_accounts",
                    "message": "At least one top account has elevated bot probability.",
                    "evidence": ["bot_probability>=0.8"],
                }
            )

        if any(self._max_spread_count(cluster.spread_over_time) >= 30 for cluster in claims):
            alerts.append(
                {
                    "severity": "medium",
                    "code": "high_claim_velocity",
                    "message": "At least one claim cluster shows high observed daily spread.",
                    "evidence": ["max spread_over_time daily count >= 30"],
                }
            )

        return alerts

    def _build_strategy(self, goal: str, risk_tolerance: str) -> dict[str, Any]:
        intensity = "high" if risk_tolerance == "low" else "medium"
        goal_line = {
            "reputation_protection": "Protect brand trust with fast clarifications and source-backed updates.",
            "crisis_response": "Prioritize speed and narrative containment in high-velocity cycles.",
            "brand_safety": "Reduce adjacency risk by filtering high-risk narratives early.",
            "misinfo_mitigation": "Focus on evidence-led debunks and recurring claim tracking.",
        }.get(goal, "Maintain evidence-based monitoring and calibrated responses.")

        return {
            "next_24h": [
                {
                    "action": "Publish one source-backed clarification for top active narrative.",
                    "why": goal_line,
                    "impact": "Reduces ambiguity and rumor spread.",
                    "cost": "low",
                },
                {
                    "action": "Activate keyword watchlist and alert thresholds for sudden volume spikes.",
                    "why": "Early detection prevents delayed responses.",
                    "impact": "Improves response speed.",
                    "cost": "low",
                },
            ],
            "next_7d": [
                {
                    "action": "Track daily claim deltas, repeated-text ratio, and shared-URL bursts.",
                    "why": "Separates organic discussion from coordinated amplification.",
                    "impact": "Improves decision quality.",
                    "cost": "med",
                },
                {
                    "action": "Create reusable FAQ snippets for recurring claims.",
                    "why": "Ensures consistent messaging quality.",
                    "impact": "Lowers operational load.",
                    "cost": "med",
                },
            ],
            "next_30d": [
                {
                    "action": "Add media provenance checks (hashing + metadata chain) for high-impact posts.",
                    "why": "Raises confidence in AI-image assertions.",
                    "impact": "Higher-quality moderation outcomes.",
                    "cost": "high" if intensity == "high" else "med",
                },
                {
                    "action": "Benchmark thresholds against historical baselines and labeled samples.",
                    "why": "Reduces false positives and improves calibration.",
                    "impact": "Higher analyst confidence.",
                    "cost": "med",
                },
            ],
            "platform_actions": [
                "report_spam",
                "report_impersonation",
                "mute_block",
                "label_with_sources",
                "monitor_keywords",
            ],
            "communications_playbook": [
                {
                    "scenario": "Unverified claim with medium reach",
                    "do": "Clarify with timestamps and primary sources.",
                    "dont": "Use definitive language without evidence.",
                },
                {
                    "scenario": "Rapid rumor spike",
                    "do": "Debunk once with canonical evidence and pin the update.",
                    "dont": "Repeat rumor framing in headlines.",
                },
            ],
            "response_templates": [
                {
                    "channel": "X",
                    "template": "We are monitoring this topic and sharing only evidence-backed updates with source links and timestamps.",
                },
                {
                    "channel": "statement",
                    "template": "Our monitoring detected increased discussion. We are validating claims and will publish verified findings transparently.",
                },
            ],
        }

    @staticmethod
    def _max_spread_count(spread_over_time: str) -> int:
        max_count = 0
        for chunk in spread_over_time.split(","):
            part = chunk.strip()
            if ":" not in part:
                continue
            try:
                max_count = max(max_count, int(part.split(":")[-1].strip()))
            except ValueError:
                continue
        return max_count

    @staticmethod
    def _infer_risk_level(
        suspected_clusters: list[dict[str, Any]],
        claims: list[dict[str, Any]],
        max_bot_probability: float,
        post_count: int,
    ) -> str:
        high_risk_claim = any(
            claim["recommended_response"] in {"debunk", "escalate"} and claim["reach_proxy"] in {"medium", "high"}
            for claim in claims
        )
        strong_cluster = any(
            cluster["bot_likelihood"] >= 0.6 and cluster["size"] >= 20 for cluster in suspected_clusters
        )

        if strong_cluster and high_risk_claim:
            return "critical"
        if strong_cluster or high_risk_claim or max_bot_probability >= 0.7:
            return "high"
        if post_count >= 100 or max_bot_probability >= 0.4:
            return "medium"
        return "low"

    @staticmethod
    def _overall_confidence(post_count: int, cluster_count: int, unique_accounts: int) -> str:
        if post_count >= 100 and unique_accounts >= 50:
            return "high" if cluster_count > 0 else "medium"
        if post_count >= 30:
            return "medium"
        return "low"

    @staticmethod
    def _why_now(timeline: list[dict[str, Any]]) -> str:
        if not timeline:
            return "No posts were collected in the selected window."
        top = max(timeline, key=lambda item: int(item["events"][0].split(" ")[0]))
        return f"Volume spike centered on {top['date']} based on collected in-window activity."

    @staticmethod
    def _data_gaps(post_count: int) -> list[str]:
        gaps = [
            "Original media provenance artifacts (C2PA/original binary chain).",
            "Cross-platform corroboration outside X.",
            "Ground-truth labels for bot/non-bot calibration.",
        ]
        if post_count < 100:
            gaps.append("Larger sample size needed for stronger coordination confidence.")
        return gaps


def generate_trust_report(payload: XIntelInput | dict[str, Any]) -> dict[str, Any]:
    """Convenience wrapper for report generation."""
    return TrustReportGenerator().generate(payload)


def generate_x_drilldown(payload: XIntelInput | dict[str, Any]) -> dict[str, Any]:
    """Convenience wrapper for drill-down dashboard data."""
    return TrustReportGenerator().generate_drilldown(payload)
