import hashlib
import json
from functools import wraps

from django.core.cache import cache


CATALOG_PREFIX = "catalog"
PRODUCTS_TTL = 300
META_TTL = 600


def _version_key():
    return f"{CATALOG_PREFIX}:version"


def catalog_version():
    version = cache.get(_version_key())
    if version is None:
        version = 1
        cache.set(_version_key(), version, None)
    return version


def invalidate_catalog_cache():
    try:
        cache.incr(_version_key())
    except ValueError:
        cache.set(_version_key(), 1, None)


def _make_key(namespace: str, payload: dict) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    digest = hashlib.md5(raw.encode()).hexdigest()
    return f"{CATALOG_PREFIX}:v{catalog_version()}:{namespace}:{digest}"


def get_cached(namespace: str, payload: dict):
    return cache.get(_make_key(namespace, payload))


def set_cached(namespace: str, payload: dict, data, timeout: int):
    cache.set(_make_key(namespace, payload), data, timeout)


def cached_catalog(namespace: str, ttl: int):
    """Cache DRF Response .data dict built by the wrapped view."""

    def decorator(view_fn):
        @wraps(view_fn)
        def wrapper(request, *args, **kwargs):
            cache_payload = {
                "path": request.path,
                "query": dict(request.query_params),
                "args": args,
                "kwargs": kwargs,
            }
            hit = get_cached(namespace, cache_payload)
            if hit is not None:
                from rest_framework.response import Response

                response = Response(hit)
                response["X-Cache"] = "HIT"
                return response

            response = view_fn(request, *args, **kwargs)
            if response.status_code == 200:
                set_cached(namespace, cache_payload, response.data, ttl)
                response["X-Cache"] = "MISS"
            return response

        return wrapper

    return decorator
