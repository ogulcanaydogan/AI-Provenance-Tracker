"""X (Twitter) data collection and normalization for trust-and-safety analysis."""

from __future__ import annotations

import asyncio
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import combinations
from typing import Any, Awaitable
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.models.x_intel import (
    AIContentScore,
    AmplificationGraphMetrics,
    BotFeature,
    BotScore,
    CentralAccount,
    ClaimCluster,
    ClusterTopAccount,
    ClusterTopPost,
    CoordinatedCluster,
    NetworkSignals,
    UserContext,
    XAuthor,
    XIntelInput,
    XPost,
    XPostMetrics,
)

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
MENTION_RE = re.compile(r"@\w+", re.IGNORECASE)
NON_WORD_RE = re.compile(r"[^\w#\s]", re.UNICODE)
WS_RE = re.compile(r"\s+")

DEFAULT_STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "your",
    "you",
    "are",
    "about",
    "have",
    "will",
    "into",
    "more",
    "just",
    "https",
    "http",
    "bir",
    "ve",
    "için",
    "ile",
    "çok",
    "daha",
    "gibi",
    "ama",
    "şu",
    "bu",
    "de",
    "da",
}

POSITIVE_WORDS = {
    "good",
    "great",
    "support",
    "safe",
    "başarılı",
    "iyi",
    "tebrikler",
    "destek",
    "güvenli",
}

NEGATIVE_WORDS = {
    "scam",
    "fraud",
    "fake",
    "lie",
    "liar",
    "spam",
    "bot",
    "sahte",
    "dolandırıcılık",
    "yalan",
    "kötü",
    "rezalet",
}

FORMAL_AI_MARKERS = {
    "furthermore",
    "moreover",
    "therefore",
    "overall",
    "in conclusion",
    "sonuç olarak",
    "ayrıca",
    "bununla birlikte",
}


@dataclass(slots=True)
class _WorkingPost:
    """Internal normalized post representation used for clustering."""

    post: XPost
    created_at: datetime
    normalized_text: str
    tokens: set[str]


class XDataCollectionError(Exception):
    """Raised when collection from X API fails."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


class XBudgetExceededError(XDataCollectionError):
    """Raised when X request budget would be exceeded."""


class XIntelCollector:
    """Collect and normalize X API data into analysis input schema."""

    def __init__(self) -> None:
        self._request_count = 0
        self._max_requests_per_run = max(1, int(settings.x_max_requests_per_run))

    @property
    def request_count(self) -> int:
        """Return number of X API requests made in the latest collect attempt."""
        return self._request_count

    @staticmethod
    def _auth_headers() -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.x_bearer_token}",
            "User-Agent": "AIProvenanceTracker-XCollector/0.1",
        }

    @staticmethod
    def estimate_request_plan(max_posts: int, max_pages: int | None = None) -> dict[str, int]:
        """Estimate expected request count for one collect run."""
        bounded_posts = max(1, int(max_posts))
        page_cap = max(1, int(max_pages if max_pages is not None else settings.x_max_pages))

        target_limit = max(20, int(bounded_posts * 0.5))
        mention_limit = max(20, int(bounded_posts * 0.3))
        interaction_limit = max(20, bounded_posts - target_limit - mention_limit)

        target_pages = max(1, min(page_cap, math.ceil(target_limit / 100)))
        mention_pages = max(1, min(page_cap, math.ceil(mention_limit / 100)))
        interaction_pages = max(1, min(page_cap, math.ceil(interaction_limit / 100)))

        estimated_requests = 1 + target_pages + mention_pages + interaction_pages
        return {
            "estimated_requests": estimated_requests,
            "worst_case_requests": 1 + (3 * page_cap),
            "page_cap": page_cap,
            "target_limit": target_limit,
            "mention_limit": mention_limit,
            "interaction_limit": interaction_limit,
        }

    async def collect(
        self,
        target_handle: str,
        window_days: int = 14,
        max_posts: int = 250,
        query: str | None = None,
        user_context: UserContext | None = None,
    ) -> XIntelInput:
        """Collect target-centered X data and return a normalized schema-compliant payload."""
        handle = self._normalize_handle(target_handle)
        if not settings.x_bearer_token:
            raise XDataCollectionError(
                "X_BEARER_TOKEN is not configured. Set it in environment before collection.",
                status_code=400,
            )
        self._request_count = 0
        self._max_requests_per_run = max(1, int(settings.x_max_requests_per_run))
        plan = self.estimate_request_plan(max_posts=max_posts)
        if (
            settings.x_cost_guard_enabled
            and plan["estimated_requests"] > self._max_requests_per_run
        ):
            raise XBudgetExceededError(
                "Estimated X API request usage exceeds budget "
                f"({plan['estimated_requests']} > {self._max_requests_per_run}). "
                "Reduce max_posts/X_MAX_PAGES or increase X_MAX_REQUESTS_PER_RUN.",
                status_code=400,
            )

        end_time = datetime.now(UTC)
        start_time = end_time - timedelta(days=window_days)
        collection_notes: list[str] = []

        async with httpx.AsyncClient(
            base_url=settings.x_api_base_url,
            timeout=httpx.Timeout(settings.x_request_timeout_seconds),
        ) as client:
            target_user = await self._fetch_target_user(client, handle)
            user_id = str(target_user.get("id", ""))
            if not user_id:
                raise XDataCollectionError("Target user_id could not be resolved from X API.", 502)

            target_limit = max(20, int(max_posts * 0.5))
            mention_limit = max(20, int(max_posts * 0.3))
            interaction_limit = max(20, max_posts - target_limit - mention_limit)

            search_end_time = end_time - timedelta(seconds=20)
            interaction_start = max(start_time, search_end_time - timedelta(days=7))
            if interaction_start >= search_end_time:
                interaction_start = search_end_time - timedelta(minutes=5)
            interaction_query = (query or "").strip() or f"@{handle}"

            target_task = self._safe_fetch(
                "target_tweets",
                self._fetch_tweets_paginated(
                    client=client,
                    path=f"/users/{user_id}/tweets",
                    params=self._tweet_query_params(
                        start_time,
                        end_time,
                        include_time_bounds=False,
                    ),
                    limit=target_limit,
                ),
                collection_notes,
            )
            mentions_task = self._safe_fetch(
                "mentions",
                self._fetch_tweets_paginated(
                    client=client,
                    path=f"/users/{user_id}/mentions",
                    params=self._tweet_query_params(
                        start_time,
                        end_time,
                        include_time_bounds=False,
                    ),
                    limit=mention_limit,
                ),
                collection_notes,
            )
            interaction_task = self._safe_fetch(
                "search_recent",
                self._fetch_tweets_paginated(
                    client=client,
                    path="/tweets/search/recent",
                    params={
                        **self._tweet_query_params(
                            interaction_start,
                            search_end_time,
                            include_time_bounds=False,
                        ),
                        "query": interaction_query,
                    },
                    limit=interaction_limit,
                ),
                collection_notes,
            )

            target_result, mentions_result, interaction_result = await asyncio.gather(
                target_task,
                mentions_task,
                interaction_task,
            )

        raw_posts, users_by_id, media_by_key = self._merge_fetch_results(
            target_user,
            [target_result, mentions_result, interaction_result],
            max_posts=max_posts,
        )
        raw_posts = self._filter_posts_by_window(raw_posts, start_time, end_time)
        posts = self._normalize_posts(
            raw_posts=raw_posts,
            users_by_id=users_by_id,
            media_by_key=media_by_key,
            target_user=target_user,
        )

        clusters, membership = self._find_coordinated_clusters(posts)
        network_signals = NetworkSignals(
            coordinated_clusters=clusters,
            amplification_graph_metrics=self._build_amplification_graph_metrics(
                posts=posts,
                account_membership=membership,
            ),
        )

        bot_scores = self._build_bot_scores(posts=posts, account_membership=membership)
        ai_scores = self._build_ai_content_scores(posts=posts, collection_notes=collection_notes)
        claim_clusters = self._build_claim_clusters(posts)

        if not bot_scores:
            bot_scores = [self._fallback_bot_score(target_user)]
        if not ai_scores:
            ai_scores = [self._fallback_ai_score(collection_notes)]

        if not claim_clusters and posts:
            claim_clusters = [
                ClaimCluster(
                    cluster_id="claim-1",
                    topic_label="general_discussion",
                    representative_claims=[post.text[:280] for post in posts[:2]],
                    spread_over_time=self._spread_over_time(posts),
                    key_accounts=self._top_account_handles(posts, limit=3),
                    sentiment=self._estimate_sentiment(posts),
                )
            ]

        return XIntelInput(
            target=f"@{handle}",
            window=f"{start_time.date().isoformat()}/{end_time.date().isoformat()}",
            posts=posts,
            network_signals=network_signals,
            bot_scores=bot_scores,
            ai_content_scores=ai_scores,
            claim_clusters=claim_clusters,
            user_context=user_context or UserContext(),
        )

    async def _safe_fetch(
        self,
        label: str,
        task: Awaitable[
            tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]
        ],
        notes: list[str],
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        try:
            return await task
        except XBudgetExceededError:
            raise
        except XDataCollectionError as exc:
            notes.append(f"{label} unavailable: {exc}")
            return [], {}, {}

    @staticmethod
    def _normalize_handle(handle: str) -> str:
        cleaned = handle.strip()
        if cleaned.startswith("@"):
            cleaned = cleaned[1:]
        return cleaned.lower()

    @staticmethod
    def _tweet_query_params(
        start_time: datetime,
        end_time: datetime,
        include_time_bounds: bool = True,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "max_results": 100,
            "tweet.fields": (
                "id,author_id,created_at,lang,public_metrics,entities,"
                "referenced_tweets,conversation_id,attachments"
            ),
            "user.fields": (
                "id,username,created_at,verified,description,location,url,"
                "public_metrics,name,profile_image_url"
            ),
            "media.fields": "media_key,type,url,preview_image_url",
            "expansions": "author_id,attachments.media_keys",
        }
        if include_time_bounds:
            params["start_time"] = start_time.isoformat().replace("+00:00", "Z")
            params["end_time"] = end_time.isoformat().replace("+00:00", "Z")
        return params

    @staticmethod
    def _filter_posts_by_window(
        raw_posts: list[dict[str, Any]],
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for raw in raw_posts:
            created_at = raw.get("created_at")
            if not created_at:
                continue
            try:
                dt = XIntelCollector._parse_datetime(created_at)
            except ValueError:
                continue
            if start_time <= dt <= end_time:
                filtered.append(raw)
        return filtered

    async def _fetch_target_user(self, client: httpx.AsyncClient, handle: str) -> dict[str, Any]:
        payload = await self._request_json(
            client,
            f"/users/by/username/{handle}",
            {
                "user.fields": (
                    "id,username,created_at,verified,description,location,url,"
                    "public_metrics,name,profile_image_url"
                )
            },
        )
        user = payload.get("data")
        if not user:
            raise XDataCollectionError(f"Target handle '{handle}' not found.", status_code=404)
        return user

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if settings.x_cost_guard_enabled and self._request_count >= self._max_requests_per_run:
            raise XBudgetExceededError(
                "X request budget exceeded during collection "
                f"(attempted {self._request_count + 1}, max {self._max_requests_per_run}). "
                "Lower max_posts/X_MAX_PAGES or increase X_MAX_REQUESTS_PER_RUN.",
                status_code=400,
            )
        self._request_count += 1
        response = await client.get(path, params=params, headers=self._auth_headers())
        if response.status_code >= 400:
            detail = self._extract_error_detail(response)
            if response.status_code in {401, 403}:
                raise XDataCollectionError(
                    f"X API auth error ({response.status_code}): {detail}", 401
                )
            if response.status_code == 404:
                raise XDataCollectionError(f"X API endpoint not found: {detail}", 404)
            if response.status_code == 429:
                raise XDataCollectionError("X API rate limit reached. Retry later.", 429)
            raise XDataCollectionError(
                f"X API request failed ({response.status_code}): {detail}",
                status_code=502,
            )
        return response.json()

    @staticmethod
    def _extract_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:300]

        if isinstance(payload, dict):
            if "detail" in payload and isinstance(payload["detail"], str):
                return payload["detail"]
            if "title" in payload and isinstance(payload["title"], str):
                return payload["title"]
            if "errors" in payload and payload["errors"]:
                first = payload["errors"][0]
                if isinstance(first, dict):
                    return str(first.get("message") or first.get("detail") or first)
                return str(first)
        return str(payload)[:300]

    async def _fetch_tweets_paginated(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: dict[str, Any],
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        tweets: list[dict[str, Any]] = []
        users_by_id: dict[str, dict[str, Any]] = {}
        media_by_key: dict[str, dict[str, Any]] = {}

        next_token: str | None = None
        pages = 0
        while len(tweets) < limit and pages < settings.x_max_pages:
            page_params = dict(params)
            page_params["max_results"] = min(100, max(10, limit - len(tweets)))
            if next_token:
                page_params["pagination_token"] = next_token

            payload = await self._request_json(client, path, page_params)
            page_tweets = payload.get("data", [])
            if page_tweets:
                tweets.extend(page_tweets)

            includes = payload.get("includes", {})
            for raw_user in includes.get("users", []):
                user_id = str(raw_user.get("id", ""))
                if user_id:
                    users_by_id[user_id] = raw_user
            for media in includes.get("media", []):
                media_key = str(media.get("media_key", ""))
                if media_key:
                    media_by_key[media_key] = media

            meta = payload.get("meta", {})
            next_token = meta.get("next_token")
            pages += 1
            if not next_token:
                break

        return tweets[:limit], users_by_id, media_by_key

    @staticmethod
    def _merge_fetch_results(
        target_user: dict[str, Any],
        results: list[
            tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]
        ],
        max_posts: int,
    ) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        posts_by_id: dict[str, dict[str, Any]] = {}
        users_by_id: dict[str, dict[str, Any]] = {str(target_user.get("id", "")): target_user}
        media_by_key: dict[str, dict[str, Any]] = {}

        for tweets, users, media in results:
            for raw in tweets:
                tweet_id = str(raw.get("id", ""))
                if tweet_id and tweet_id not in posts_by_id:
                    posts_by_id[tweet_id] = raw
            users_by_id.update(users)
            media_by_key.update(media)

        deduped = list(posts_by_id.values())
        deduped.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return deduped[:max_posts], users_by_id, media_by_key

    def _normalize_posts(
        self,
        raw_posts: list[dict[str, Any]],
        users_by_id: dict[str, dict[str, Any]],
        media_by_key: dict[str, dict[str, Any]],
        target_user: dict[str, Any],
    ) -> list[XPost]:
        posts: list[XPost] = []

        for raw in raw_posts:
            author_id = str(raw.get("author_id", ""))
            author_raw = users_by_id.get(author_id)
            if not author_raw and author_id == str(target_user.get("id", "")):
                author_raw = target_user

            created_at = raw.get("created_at") or datetime.now(UTC).isoformat()
            entities = raw.get("entities") or {}
            metrics = raw.get("public_metrics") or {}

            urls = self._extract_urls(entities)
            hashtags = self._extract_hashtags(entities)
            mentions = self._extract_mentions(entities)
            media_urls = self._extract_media_urls(raw, media_by_key)
            reply_to, quoted_tweet_id = self._extract_references(raw)

            profile_fields = {}
            for key in ("name", "description", "location", "url", "profile_image_url"):
                if author_raw and author_raw.get(key):
                    profile_fields[key] = author_raw.get(key)

            author_metrics = (author_raw or {}).get("public_metrics", {})
            author = XAuthor(
                user_id=author_id or "unknown",
                handle=(author_raw or {}).get("username", f"user_{author_id or 'unknown'}"),
                created_at=(author_raw or {}).get("created_at", ""),
                followers=int(author_metrics.get("followers_count", 0) or 0),
                following=int(author_metrics.get("following_count", 0) or 0),
                verified=bool((author_raw or {}).get("verified", False)),
                profile_fields=profile_fields,
            )

            post = XPost(
                tweet_id=str(raw.get("id", "")),
                created_at=created_at,
                text=raw.get("text", ""),
                lang=raw.get("lang", "und"),
                media_urls=media_urls,
                metrics=XPostMetrics(
                    likes=int(metrics.get("like_count", 0) or 0),
                    reposts=int(metrics.get("retweet_count", 0) or 0),
                    replies=int(metrics.get("reply_count", 0) or 0),
                    views=int(metrics.get("impression_count", 0) or 0),
                ),
                author=author,
                reply_to=reply_to,
                quoted_tweet_id=quoted_tweet_id,
                urls=urls,
                hashtags=hashtags,
                mentions=mentions,
            )
            if post.tweet_id:
                posts.append(post)

        posts.sort(key=lambda post: self._parse_datetime(post.created_at))
        return posts

    @staticmethod
    def _extract_urls(entities: dict[str, Any]) -> list[str]:
        urls: list[str] = []
        for url_item in entities.get("urls", []):
            for field in ("expanded_url", "unwound_url", "url"):
                value = url_item.get(field)
                if value:
                    urls.append(value)
                    break
        return urls

    @staticmethod
    def _extract_hashtags(entities: dict[str, Any]) -> list[str]:
        return [
            str(item.get("tag", "")).lower()
            for item in entities.get("hashtags", [])
            if item.get("tag")
        ]

    @staticmethod
    def _extract_mentions(entities: dict[str, Any]) -> list[str]:
        return [
            str(item.get("username", "")).lower()
            for item in entities.get("mentions", [])
            if item.get("username")
        ]

    @staticmethod
    def _extract_media_urls(
        raw_post: dict[str, Any], media_by_key: dict[str, dict[str, Any]]
    ) -> list[str]:
        media_urls: list[str] = []
        media_keys = (raw_post.get("attachments") or {}).get("media_keys", [])
        for media_key in media_keys:
            media = media_by_key.get(str(media_key), {})
            for field in ("url", "preview_image_url"):
                value = media.get(field)
                if value:
                    media_urls.append(str(value))
                    break
        return media_urls

    @staticmethod
    def _extract_references(raw_post: dict[str, Any]) -> tuple[str | None, str | None]:
        reply_to = None
        quoted = None
        for ref in raw_post.get("referenced_tweets", []):
            ref_type = ref.get("type")
            ref_id = ref.get("id")
            if ref_type == "replied_to":
                reply_to = str(ref_id)
            if ref_type == "quoted":
                quoted = str(ref_id)
        return reply_to, quoted

    def _find_coordinated_clusters(
        self,
        posts: list[XPost],
    ) -> tuple[list[CoordinatedCluster], dict[str, set[str]]]:
        working = [self._to_working_post(post) for post in posts]
        if len(working) < 3:
            return [], defaultdict(set)

        hashtag_groups: dict[str, set[str]] = defaultdict(set)
        url_groups: dict[str, set[str]] = defaultdict(set)
        text_groups: dict[str, set[str]] = defaultdict(set)

        post_map = {item.post.tweet_id: item for item in working}
        for item in working:
            for hashtag in item.post.hashtags:
                hashtag_groups[hashtag].add(item.post.tweet_id)
            for url in item.post.urls:
                url_groups[self._canonical_url(url)].add(item.post.tweet_id)
            if item.normalized_text:
                text_groups[item.normalized_text].add(item.post.tweet_id)

        candidate_sets: list[set[str]] = []
        candidate_sets.extend(self._cluster_candidates_from_groups(post_map, hashtag_groups))
        candidate_sets.extend(self._cluster_candidates_from_groups(post_map, url_groups))
        candidate_sets.extend(self._cluster_candidates_from_groups(post_map, text_groups))
        candidate_sets.extend(self._cluster_candidates_from_bursts(working))

        merged_sets = self._merge_candidate_sets(candidate_sets)
        account_membership: dict[str, set[str]] = defaultdict(set)
        clusters: list[CoordinatedCluster] = []
        for index, tweet_ids in enumerate(merged_sets, start=1):
            cluster_posts = sorted(
                (post_map[tweet_id] for tweet_id in tweet_ids if tweet_id in post_map),
                key=lambda item: item.created_at,
            )
            if len(cluster_posts) < 3:
                continue

            cluster_id = f"cluster-{index}"
            for item in cluster_posts:
                account_membership[item.post.author.handle.lower()].add(cluster_id)

            cluster = self._build_cluster(cluster_id, cluster_posts, account_membership)
            if cluster is not None:
                clusters.append(cluster)

        return clusters, account_membership

    @staticmethod
    def _cluster_candidates_from_groups(
        post_map: dict[str, _WorkingPost],
        groups: dict[str, set[str]],
    ) -> list[set[str]]:
        candidates: list[set[str]] = []
        for tweet_ids in groups.values():
            if len(tweet_ids) < 3:
                continue
            authors = {post_map[tweet_id].post.author.handle.lower() for tweet_id in tweet_ids}
            if len(authors) < 3:
                continue
            candidates.append(set(tweet_ids))
        return candidates

    @staticmethod
    def _cluster_candidates_from_bursts(working: list[_WorkingPost]) -> list[set[str]]:
        if len(working) < 4:
            return []

        sorted_posts = sorted(working, key=lambda item: item.created_at)
        candidates: list[set[str]] = []
        left = 0
        window_seconds = 45 * 60
        for right in range(len(sorted_posts)):
            while (
                sorted_posts[right].created_at - sorted_posts[left].created_at
            ).total_seconds() > window_seconds:
                left += 1

            window = sorted_posts[left : right + 1]
            if len(window) < 4:
                continue
            authors = {item.post.author.handle.lower() for item in window}
            if len(authors) < 3:
                continue
            candidates.append({item.post.tweet_id for item in window})

        return candidates

    @staticmethod
    def _merge_candidate_sets(candidate_sets: list[set[str]]) -> list[set[str]]:
        merged: list[set[str]] = []
        for current in candidate_sets:
            if len(current) < 3:
                continue
            attached = False
            for existing in merged:
                overlap = len(existing & current)
                min_size = min(len(existing), len(current))
                if min_size > 0 and overlap / min_size >= 0.5:
                    existing.update(current)
                    attached = True
                    break
            if not attached:
                merged.append(set(current))

        changed = True
        while changed:
            changed = False
            for i in range(len(merged)):
                if changed:
                    break
                for j in range(i + 1, len(merged)):
                    overlap = len(merged[i] & merged[j])
                    min_size = min(len(merged[i]), len(merged[j]))
                    if min_size > 0 and overlap / min_size >= 0.5:
                        merged[i].update(merged[j])
                        merged.pop(j)
                        changed = True
                        break

        return [item for item in merged if len(item) >= 3]

    def _build_cluster(
        self,
        cluster_id: str,
        posts: list[_WorkingPost],
        account_membership: dict[str, set[str]],
    ) -> CoordinatedCluster | None:
        if len(posts) < 3:
            return None

        hashtag_counter = Counter(tag for item in posts for tag in item.post.hashtags)
        url_counter = Counter(self._canonical_url(url) for item in posts for url in item.post.urls)

        shared_hashtags = [tag for tag, count in hashtag_counter.items() if count >= 2][:8]
        shared_urls = [url for url, count in url_counter.items() if count >= 2][:8]

        text_similarity = self._text_similarity(posts)
        burst_score = self._burst_score(posts)

        if not shared_hashtags and not shared_urls and text_similarity < 0.65:
            return None
        if len(posts) > 25 and text_similarity < 0.1 and burst_score < 0.25:
            return None

        earliest = posts[0].post.author.handle.lower()
        author_counts = Counter(item.post.author.handle.lower() for item in posts)

        bridge_candidates = [
            handle
            for handle, _ in author_counts.most_common()
            if len(account_membership.get(handle, set())) > 1 and handle != earliest
        ]
        bridge_handle = bridge_candidates[0] if bridge_candidates else None

        selected_handles: list[str] = [earliest]
        if bridge_handle and bridge_handle not in selected_handles:
            selected_handles.append(bridge_handle)
        for handle, _ in author_counts.most_common():
            if handle not in selected_handles:
                selected_handles.append(handle)
            if len(selected_handles) >= 3:
                break

        top_accounts: list[ClusterTopAccount] = []
        for handle in selected_handles[:3]:
            role = "amplifier"
            if handle == earliest:
                role = "seed"
            elif bridge_handle and handle == bridge_handle:
                role = "bridge"

            exemplar = next(
                item.post for item in posts if item.post.author.handle.lower() == handle
            )
            top_accounts.append(
                ClusterTopAccount(
                    user_id=exemplar.author.user_id,
                    handle=exemplar.author.handle,
                    role_hint=role,
                )
            )

        ranked_posts = sorted(
            (item.post for item in posts),
            key=lambda post: post.metrics.likes + post.metrics.reposts + post.metrics.replies,
            reverse=True,
        )
        top_posts = [
            ClusterTopPost(
                tweet_id=post.tweet_id,
                text=post.text[:280],
                created_at=post.created_at,
                urls=post.urls,
                hashtags=post.hashtags,
                mentions=post.mentions,
            )
            for post in ranked_posts[:3]
        ]

        return CoordinatedCluster(
            cluster_id=cluster_id,
            size=len(posts),
            shared_hashtags=shared_hashtags,
            shared_urls=shared_urls,
            time_burst_score=burst_score,
            text_similarity_score=text_similarity,
            top_accounts=top_accounts,
            top_posts=top_posts,
        )

    def _build_amplification_graph_metrics(
        self,
        posts: list[XPost],
        account_membership: dict[str, set[str]],
    ) -> AmplificationGraphMetrics:
        if not posts:
            return AmplificationGraphMetrics(density=0.0, modularity=0.0, central_accounts=[])

        tweet_to_author = {post.tweet_id: post.author.handle.lower() for post in posts}
        nodes = {post.author.handle.lower() for post in posts}
        edges: set[tuple[str, str]] = set()

        for post in posts:
            source = post.author.handle.lower()

            for mention in post.mentions:
                target = mention.lower()
                if source != target:
                    nodes.add(target)
                    edges.add((source, target))

            for ref_id in [post.reply_to, post.quoted_tweet_id]:
                if ref_id and ref_id in tweet_to_author:
                    target = tweet_to_author[ref_id]
                    if source != target:
                        edges.add((source, target))

        node_count = len(nodes)
        possible_edges = node_count * (node_count - 1)
        density = (len(edges) / possible_edges) if possible_edges > 0 else 0.0

        in_degree: Counter[str] = Counter()
        out_degree: Counter[str] = Counter()
        for source, target in edges:
            out_degree[source] += 1
            in_degree[target] += 1

        central_accounts = []
        for handle in nodes:
            degree = in_degree[handle] + out_degree[handle]
            score = degree / (2 * (node_count - 1)) if node_count > 1 else 0.0
            central_accounts.append(CentralAccount(handle=handle, score=round(score, 3)))
        central_accounts.sort(key=lambda item: item.score, reverse=True)

        modularity = self._modularity_proxy(edges, account_membership)
        return AmplificationGraphMetrics(
            density=round(density, 3),
            modularity=round(modularity, 3),
            central_accounts=central_accounts[:10],
        )

    @staticmethod
    def _modularity_proxy(
        edges: set[tuple[str, str]],
        account_membership: dict[str, set[str]],
    ) -> float:
        if not edges:
            return 0.0

        assigned_edges = 0
        intra_edges = 0
        for source, target in edges:
            source_clusters = account_membership.get(source, set())
            target_clusters = account_membership.get(target, set())
            if not source_clusters or not target_clusters:
                continue
            assigned_edges += 1
            if source_clusters.intersection(target_clusters):
                intra_edges += 1

        if assigned_edges == 0:
            return 0.0
        return intra_edges / assigned_edges

    def _build_bot_scores(
        self,
        posts: list[XPost],
        account_membership: dict[str, set[str]],
    ) -> list[BotScore]:
        posts_by_account: dict[str, list[XPost]] = defaultdict(list)
        for post in posts:
            posts_by_account[post.author.handle.lower()].append(post)

        if not posts_by_account:
            return []

        scores: list[BotScore] = []
        for handle_key, account_posts in posts_by_account.items():
            exemplar = account_posts[0]
            post_count = len(account_posts)
            normalized_texts = [self._normalize_text(post.text) for post in account_posts]
            unique_ratio = len(set(normalized_texts)) / post_count if post_count > 0 else 1.0
            duplicate_ratio = 1.0 - unique_ratio
            avg_hashtag_count = sum(len(post.hashtags) for post in account_posts) / post_count

            account_age_days = self._account_age_days(exemplar.author.created_at)
            days_span = max(self._window_days(account_posts), 1.0)
            activity_rate = post_count / days_span

            follower_ratio = exemplar.author.followers / max(exemplar.author.following, 1)
            cluster_count = len(account_membership.get(handle_key, set()))

            score = 0.05
            if account_age_days is not None:
                if account_age_days < 30:
                    score += 0.25
                elif account_age_days < 90:
                    score += 0.15

            if activity_rate >= 15:
                score += 0.2
            elif activity_rate >= 8:
                score += 0.1

            if duplicate_ratio >= 0.6:
                score += 0.25
            elif duplicate_ratio >= 0.35:
                score += 0.15

            if avg_hashtag_count >= 4:
                score += 0.1

            if follower_ratio < 0.1 or follower_ratio > 20:
                score += 0.1

            if cluster_count > 0:
                score += min(0.15, 0.05 * cluster_count)

            score = float(max(0.0, min(score, 0.99)))

            confidence = "low"
            if post_count >= 8 and account_age_days is not None:
                confidence = "high"
            elif post_count >= 3:
                confidence = "medium"

            features = [
                BotFeature(
                    feature="account_age_days",
                    value="unknown" if account_age_days is None else str(int(account_age_days)),
                    why_it_matters="Newly created accounts can indicate disposable amplification actors.",
                ),
                BotFeature(
                    feature="duplicate_text_ratio",
                    value=f"{duplicate_ratio:.2f}",
                    why_it_matters="High text reuse is a common indicator of scripted posting.",
                ),
                BotFeature(
                    feature="posts_per_day",
                    value=f"{activity_rate:.2f}",
                    why_it_matters="Very high posting velocity can indicate automated behavior.",
                ),
            ]

            scores.append(
                BotScore(
                    user_id=exemplar.author.user_id,
                    handle=exemplar.author.handle,
                    bot_probability=round(score, 3),
                    top_features=features,
                    confidence=confidence,
                )
            )

        scores.sort(key=lambda item: item.bot_probability, reverse=True)
        return scores[:200]

    def _build_ai_content_scores(
        self,
        posts: list[XPost],
        collection_notes: list[str],
    ) -> list[AIContentScore]:
        if not posts:
            return []

        scores: list[AIContentScore] = []
        for post in posts:
            normalized = self._normalize_text(post.text)
            words = [part for part in normalized.split(" ") if part]
            word_count = len(words)
            unique_ratio = len(set(words)) / word_count if word_count else 1.0
            repetition = self._repeated_bigram_ratio(words)

            marker_hits = 0
            lowered = post.text.lower()
            for marker in FORMAL_AI_MARKERS:
                if marker in lowered:
                    marker_hits += 1

            sentence_lengths = [
                len(segment.split())
                for segment in re.split(r"[.!?]+", post.text)
                if segment.strip()
            ]
            sentence_std = self._std_dev(sentence_lengths)

            ai_text_probability = 0.08
            if unique_ratio < 0.45:
                ai_text_probability += 0.25
            elif unique_ratio < 0.55:
                ai_text_probability += 0.15

            if repetition > 0.22:
                ai_text_probability += 0.25
            elif repetition > 0.12:
                ai_text_probability += 0.1

            if marker_hits >= 2:
                ai_text_probability += 0.2
            elif marker_hits == 1:
                ai_text_probability += 0.1

            if word_count >= 80 and sentence_std < 4.5:
                ai_text_probability += 0.15

            ai_text_probability = float(max(0.0, min(ai_text_probability, 0.99)))

            ai_image_probability = 0.0
            provenance_notes = ["X API does not expose original file provenance/C2PA metadata."]
            if post.media_urls:
                ai_image_probability = 0.2
                provenance_notes.append(
                    "Media URLs are present, but original binaries were not downloaded in this pass."
                )

            for note in collection_notes[:2]:
                provenance_notes.append(note)

            confidence = "medium" if word_count >= 40 else "low"
            scores.append(
                AIContentScore(
                    tweet_id=post.tweet_id,
                    ai_text_probability=round(ai_text_probability, 3),
                    ai_image_probability=round(ai_image_probability, 3),
                    provenance_notes=provenance_notes,
                    confidence=confidence,
                )
            )

        return scores

    def _build_claim_clusters(self, posts: list[XPost]) -> list[ClaimCluster]:
        if not posts:
            return []

        grouped: dict[str, list[XPost]] = defaultdict(list)
        for post in posts:
            topic = self._topic_key(post)
            grouped[topic].append(post)

        significant_groups = [
            (topic, grouped_posts)
            for topic, grouped_posts in grouped.items()
            if len(grouped_posts) >= 2
        ]
        if not significant_groups:
            significant_groups = [("general_discussion", posts)]

        significant_groups.sort(key=lambda item: len(item[1]), reverse=True)

        clusters: list[ClaimCluster] = []
        for index, (topic, grouped_posts) in enumerate(significant_groups[:10], start=1):
            representative_claims = []
            seen_claims: set[str] = set()
            for post in grouped_posts:
                cleaned = WS_RE.sub(" ", post.text).strip()
                if not cleaned:
                    continue
                if cleaned in seen_claims:
                    continue
                representative_claims.append(cleaned[:280])
                seen_claims.add(cleaned)
                if len(representative_claims) >= 3:
                    break

            clusters.append(
                ClaimCluster(
                    cluster_id=f"claim-{index}",
                    topic_label=topic,
                    representative_claims=representative_claims,
                    spread_over_time=self._spread_over_time(grouped_posts),
                    key_accounts=self._top_account_handles(grouped_posts, limit=5),
                    sentiment=self._estimate_sentiment(grouped_posts),
                )
            )

        return clusters

    @staticmethod
    def _topic_key(post: XPost) -> str:
        if post.hashtags:
            return post.hashtags[0].lower()

        normalized = XIntelCollector._normalize_text(post.text)
        token_candidates = [
            token
            for token in normalized.split(" ")
            if token and token not in DEFAULT_STOPWORDS and len(token) > 3
        ]
        if token_candidates:
            return token_candidates[0][:40]
        return "general_discussion"

    @staticmethod
    def _spread_over_time(posts: list[XPost]) -> str:
        counts: Counter[str] = Counter()
        for post in posts:
            dt = XIntelCollector._parse_datetime(post.created_at)
            counts[dt.date().isoformat()] += 1
        return ", ".join(f"{date}: {count}" for date, count in sorted(counts.items()))

    @staticmethod
    def _top_account_handles(posts: list[XPost], limit: int) -> list[str]:
        counter = Counter(post.author.handle for post in posts)
        return [handle for handle, _ in counter.most_common(limit)]

    @staticmethod
    def _estimate_sentiment(posts: list[XPost]) -> str:
        positive = 0
        negative = 0
        for post in posts:
            text = post.text.lower()
            positive += sum(1 for token in POSITIVE_WORDS if token in text)
            negative += sum(1 for token in NEGATIVE_WORDS if token in text)

        if negative >= positive * 1.4 and negative > 0:
            return "negative"
        if positive >= negative * 1.4 and positive > 0:
            return "positive"
        if positive > 0 and negative > 0:
            return "mixed"
        return "neutral"

    @staticmethod
    def _fallback_bot_score(target_user: dict[str, Any]) -> BotScore:
        return BotScore(
            user_id=str(target_user.get("id", "unknown")),
            handle=str(target_user.get("username", "unknown")),
            bot_probability=0.0,
            top_features=[
                BotFeature(
                    feature="data_availability",
                    value="insufficient",
                    why_it_matters="Bot probability could not be computed because no posts were collected.",
                )
            ],
            confidence="low",
        )

    @staticmethod
    def _fallback_ai_score(collection_notes: list[str]) -> AIContentScore:
        notes = [
            "No posts were collected in the selected window; AI content scoring is unavailable.",
        ]
        notes.extend(collection_notes[:2])
        return AIContentScore(
            tweet_id="unavailable",
            ai_text_probability=0.0,
            ai_image_probability=0.0,
            provenance_notes=notes,
            confidence="low",
        )

    @staticmethod
    def _window_days(posts: list[XPost]) -> float:
        if not posts:
            return 1.0
        times = [XIntelCollector._parse_datetime(post.created_at) for post in posts]
        span_days = (max(times) - min(times)).total_seconds() / 86400
        return max(span_days, 1.0)

    @staticmethod
    def _account_age_days(created_at: str) -> float | None:
        if not created_at:
            return None
        try:
            created = XIntelCollector._parse_datetime(created_at)
        except ValueError:
            return None
        return max((datetime.now(UTC) - created).total_seconds() / 86400, 0.0)

    @staticmethod
    def _to_working_post(post: XPost) -> _WorkingPost:
        normalized = XIntelCollector._normalize_text(post.text)
        token_set = {
            token
            for token in normalized.split(" ")
            if token and token not in DEFAULT_STOPWORDS and len(token) > 2
        }
        return _WorkingPost(
            post=post,
            created_at=XIntelCollector._parse_datetime(post.created_at),
            normalized_text=normalized,
            tokens=token_set,
        )

    @staticmethod
    def _normalize_text(text: str) -> str:
        stripped = URL_RE.sub(" ", text.lower())
        stripped = MENTION_RE.sub(" ", stripped)
        stripped = NON_WORD_RE.sub(" ", stripped)
        stripped = WS_RE.sub(" ", stripped).strip()
        return stripped

    @staticmethod
    def _canonical_url(url: str) -> str:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        return f"{host}{path}"

    @staticmethod
    def _parse_datetime(value: str) -> datetime:
        cleaned = value.strip()
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        parsed = datetime.fromisoformat(cleaned)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _burst_score(posts: list[_WorkingPost]) -> float:
        if len(posts) < 2:
            return 0.0
        span_seconds = max((posts[-1].created_at - posts[0].created_at).total_seconds(), 1.0)
        expected_span = max(900.0, len(posts) * 900.0)
        burst = 1.0 - min(span_seconds / expected_span, 1.0)
        return round(max(0.0, burst), 3)

    @staticmethod
    def _text_similarity(posts: list[_WorkingPost]) -> float:
        if len(posts) < 2:
            return 0.0

        similarities: list[float] = []
        for left, right in combinations(posts, 2):
            if not left.tokens or not right.tokens:
                continue
            union = left.tokens | right.tokens
            if not union:
                continue
            jaccard = len(left.tokens & right.tokens) / len(union)
            similarities.append(jaccard)
            if len(similarities) >= 50:
                break

        if not similarities:
            return 0.0
        return round(sum(similarities) / len(similarities), 3)

    @staticmethod
    def _repeated_bigram_ratio(words: list[str]) -> float:
        if len(words) < 4:
            return 0.0
        bigrams = [f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1)]
        counts = Counter(bigrams)
        repeated = sum(count - 1 for count in counts.values() if count > 1)
        return repeated / max(len(bigrams), 1)

    @staticmethod
    def _std_dev(values: list[int]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return math.sqrt(variance)
