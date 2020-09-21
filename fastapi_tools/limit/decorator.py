from functools import wraps
from typing import Any, Callable, Dict

from starlette.responses import Response
from fastapi_tools.limit.rule import Rule
from fastapi_tools.limit.token_bucket import TokenBucket


_cache_dict: Dict[str, Any] = {}


def limit(rule: Rule):
    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        async def _limit(*args, **kwargs):
            key: str = str(id(func))
            token_bucket: TokenBucket = _cache_dict.get(key, None)
            if token_bucket is None:
                token_bucket: TokenBucket = TokenBucket(rule.get_token(), max_token=rule.max_token)
                _cache_dict[key] = token_bucket
            if token_bucket.can_consume():
                return await func(*args, **kwargs)
            else:
                return Response(status_code=429)
        return _limit
    return wrapper
