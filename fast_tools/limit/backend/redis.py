import time
from abc import ABC
from typing import Awaitable, Callable, List, Optional

from fast_tools.base.redis_helper import RedisHelper
from fast_tools.limit.backend.base import BaseLimitBackend
from fast_tools.limit.rule import Rule


class BaseRedisBackend(BaseLimitBackend, ABC):
    def __init__(
        self,
        backend: "RedisHelper",
        init_token_num: Optional[int] = None,
        block_time: Optional[int] = None,
        max_token_num: int = 100,
    ):
        self._init_token_num: int = init_token_num if init_token_num else max_token_num
        self._max_token_num: int = max_token_num
        self._block_time: Optional[int] = block_time
        self._backend: "RedisHelper" = backend

    async def _block_time_handle(self, key: str, rule: Rule, func: Callable[..., Awaitable[bool]]):
        block_time_key: str = key + f":block_time"
        bucket_block_time: int = rule.block_time if rule.block_time is not None else self._block_time

        if bucket_block_time is not None:
            if await self._backend.exists(block_time_key):
                return False

        can_requests = await func()
        if not can_requests and bucket_block_time is not None:
            await self._backend.redis_pool.set(block_time_key, bucket_block_time, expire=bucket_block_time)

        return can_requests


class RedisFixedWindowBackend(BaseRedisBackend):
    async def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        async def _can_requests() -> bool:
            access_num: int = await self._backend.redis_pool.incr(key)
            if access_num == 1:
                await self._backend.redis_pool.expire(key, rule.gen_second())

            can_requests: bool = not access_num > rule.gen_token_num
            return can_requests

        return await self._block_time_handle(key, rule, _can_requests)

    async def expected_time(self, key: str, rule: Rule) -> float:
        block_time_key: str = key + ":block_time"
        block_time = await self._backend.redis_pool.get(block_time_key)
        if block_time:
            return await self._backend.redis_pool.ttl(block_time_key)

        token_num: Optional[str] = await self._backend.redis_pool.get(key)
        if token_num is None:
            return 0
        else:
            token_num: int = int(token_num)

        if token_num < rule.gen_token_num:
            return 0
        return await self._backend.redis_pool.ttl(key)


class RedisCellBackend(BaseRedisBackend):
    """
    use redis-cell module
    learn more:https://github.com/brandur/redis-cell

    input: CL.THROTTLE user123 15 30 60 1
        # param  |  desc
        # user123 key
        # 15 maxburst
        # 30 token
        # 60 seconds
        # 1 apply 1token
    output:
        1) (integer) 0        # is allowed
        2) (integer) 16       # total bucket num
        3) (integer) 15       # the remaining limit of the key.
        4) (integer) -1       # the number of seconds until the user should retry,
                              #   and always -1 if the action was allowed.
        5) (integer) 2        # The number of seconds until the limit will reset to its maximum capacity
    """

    async def _call_cell(self, key: str, rule: Rule, token_num: int = 1) -> List[int]:
        max_token: int = rule.max_token_num if rule.max_token_num else self._max_token_num
        result: List[int] = await self._backend.execute(
            "CL.THROTTLE", key, max_token, rule.gen_token_num, rule.gen_second(), token_num
        )
        return result

    async def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        async def _can_requests() -> bool:
            result: List[int] = await self._call_cell(key, rule, token_num)
            can_requests: bool = bool(result[0])
            return can_requests

        return await self._block_time_handle(key, rule, _can_requests)

    async def expected_time(self, key: str, rule: Rule) -> float:
        block_time_key: str = key + ":block_time"
        block_time = await self._backend.redis_pool.get(block_time_key)
        if block_time:
            return await self._backend.redis_pool.ttl(block_time_key)

        result: List[int] = await self._call_cell(key, rule, 0)
        return float(max(result[3], 0))


class RedisTokenBucketBackend(BaseRedisBackend):
    _lua_script = """
local key = KEYS[1]
local currentTime = tonumber(ARGV[1])
local intervalPerToken = tonumber(ARGV[2])
local maxToken = tonumber(ARGV[3])
local initToken = tonumber(ARGV[4])
local tokens
local bucket = redis.call("hmget", key, "lastTime", "lastToken")
local lastTime = bucket[1]
local lastToken = bucket[2]
if lastTime == false or lastToken == false then
    tokens = initToken
    redis.call('hset', key, 'lastTime', currentTime)
else
    local thisInterval = currentTime - tonumber(lastTime)
    if thisInterval > 1 then
        local tokensToAdd = math.floor(thisInterval * intervalPerToken)
        tokens = math.min(lastToken + tokensToAdd, maxToken)
        redis.call('hset', key, 'lastTime', currentTime)
    else
        tokens = lastToken
    end
end
if tokens < 1 then
    redis.call('hset', key, 'lastToken', tokens)
    return 'false'
else
    redis.call('hset', key, 'lastToken', tokens - 1)
    return tokens - 1
end
    """

    async def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        async def _can_requests() -> bool:
            max_token: int = rule.max_token_num if rule.max_token_num else self._max_token_num
            init_token_num: int = rule.init_token_num if rule.init_token_num else self._init_token_num
            result = await self._backend.redis_pool.eval(
                self._lua_script, keys=[key], args=[time.time(), rule.gen_rate(), max_token, init_token_num]
            )
            return result

        return await self._block_time_handle(key, rule, _can_requests)

    async def expected_time(self, key: str, rule: Rule) -> float:
        block_time_key: str = key + ":block_time"
        block_time = await self._backend.redis_pool.get(block_time_key)
        if block_time:
            return await self._backend.redis_pool.ttl(block_time_key)
        last_time = await self._backend.redis_pool.hget(key, "lastTime")
        if last_time is None:
            return 0
        diff_time = last_time - time.time() * 1000
        if diff_time > 0:
            return diff_time
        return 0
