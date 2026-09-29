"""Redis cache and rate-limiter provider.

Redis does two jobs in CivicPulse:
  Job 1 — read-through cache for /api/stats (TTL 30s, X-Cache: HIT|MISS)
  Job 2 — distributed rate limiter on POST /api/complaints
"""

import hashlib
import json
import time

import redis.asyncio as redis

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# Singleton connection pool — lazy initialized
_pool: redis.Redis | None = None


async def get_redis() -> redis.Redis:
    """Return (and lazily create) the Redis connection."""
    global _pool
    if _pool is None:
        _pool = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            retry_on_timeout=True,
        )
    return _pool


async def close_redis() -> None:
    """Close the Redis connection pool during shutdown."""
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


# ── Job 1: Stats cache ─────────────────────────────────────────────────

STATS_CACHE_KEY = "civicpulse:stats"
STATS_CACHE_TTL = 30  # seconds


async def get_cached_stats() -> tuple[dict | None, bool]:
    """Fetch stats from cache. Returns (data, is_hit)."""
    r = await get_redis()
    cached = await r.get(STATS_CACHE_KEY)
    if cached is not None:
        return json.loads(cached), True
    return None, False


async def set_cached_stats(stats: dict) -> None:
    """Store stats in cache with TTL."""
    r = await get_redis()
    await r.setex(STATS_CACHE_KEY, STATS_CACHE_TTL, json.dumps(stats))


async def invalidate_stats_cache() -> None:
    """Invalidate stats cache on write — so newly submitted complaints appear immediately."""
    r = await get_redis()
    await r.delete(STATS_CACHE_KEY)


# ── Job 2: Distributed rate limiter ────────────────────────────────────

RATE_LIMIT_PREFIX = "civicpulse:ratelimit:"


async def check_rate_limit(client_ip: str) -> tuple[bool, int]:
    """Fixed-window rate limiter in Redis keyed by client IP.

    Returns:
        (allowed, retry_after_seconds)
        allowed=True means the request can proceed.
        retry_after_seconds is the time until the window resets (only meaningful when not allowed).
    """
    r = await get_redis()
    key = f"{RATE_LIMIT_PREFIX}{client_ip}"
    window = settings.rate_limit_window_seconds
    max_requests = settings.rate_limit_requests

    pipe = r.pipeline()
    pipe.incr(key)
    pipe.ttl(key)
    results = await pipe.execute()

    current_count = results[0]
    ttl = results[1]

    # First request in this window — set expiry
    if ttl == -1:
        await r.expire(key, window)
        ttl = window

    if current_count > max_requests:
        return False, max(ttl, 1)

    return True, 0


# ── Triage result cache (content-hash, 24h TTL) ────────────────────────

TRIAGE_CACHE_PREFIX = "civicpulse:triage:"
TRIAGE_CACHE_TTL = 86400  # 24 hours

# Counters for measuring cache hit rate
_triage_cache_hits = 0
_triage_cache_misses = 0


async def get_cached_triage(text: str, location: str) -> dict | None:
    """Check if we already triaged this exact complaint content."""
    global _triage_cache_hits, _triage_cache_misses
    r = await get_redis()
    content_hash = _content_hash(text, location)
    key = f"{TRIAGE_CACHE_PREFIX}{content_hash}"
    cached = await r.get(key)
    if cached is not None:
        _triage_cache_hits += 1
        logger.info("triage_cache_hit", content_hash=content_hash)
        return json.loads(cached)
    _triage_cache_misses += 1
    return None


async def set_cached_triage(text: str, location: str, result: dict) -> None:
    """Cache a triage result by content hash."""
    r = await get_redis()
    content_hash = _content_hash(text, location)
    key = f"{TRIAGE_CACHE_PREFIX}{content_hash}"
    await r.setex(key, TRIAGE_CACHE_TTL, json.dumps(result))


def get_triage_cache_stats() -> dict[str, int]:
    """Return measured triage cache hit rate."""
    total = _triage_cache_hits + _triage_cache_misses
    return {
        "hits": _triage_cache_hits,
        "misses": _triage_cache_misses,
        "total": total,
        "hit_rate_percent": round((_triage_cache_hits / total * 100) if total > 0 else 0, 1),
    }


def _content_hash(text: str, location: str) -> str:
    """SHA-256 hash of complaint content for deduplication."""
    content = f"{text.strip().lower()}|{location.strip().lower()}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# ── Health check ───────────────────────────────────────────────────────

async def redis_health_check() -> bool:
    """Return True if Redis is reachable."""
    try:
        r = await get_redis()
        return await r.ping()
    except Exception:
        return False
