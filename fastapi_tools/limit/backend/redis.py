from abc import ABC
from typing import Dict, List, Optional

from fastapi_tools.base.redis_helper import RedisHelper
from fastapi_tools.limit.backend.base import BaseLimitBackend
from fastapi_tools.limit.rule import Rule


class BaseRedisBackend(BaseLimitBackend, ABC):

    def __init__(
            self,
            backend: 'RedisHelper',
            token_num: Optional[int] = None,
            block_time: Optional[int] = None,
            max_token: int = 100
    ):
        self._token_num: int = token_num if token_num else max_token
        self._max_token: int = max_token
        self._block_time: Optional[int] = block_time
        self._backend: 'RedisHelper' = backend


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
        max_token: int = rule.max_token if rule.max_token else self._max_token
        result: List[int] = await self._backend.execute(
            'CL.THROTTLE', key, max_token, rule.token_num, rule.gen_token, rule.gen_second(), token_num
        )
        return result

    async def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        result: List[int] = await self._call_cell(key, rule, token_num)
        return bool(result[0])

    async def expected_time(self, key: str, rule: Rule, token_num=1) -> float:
        result: List[int] = await self._call_cell(key, rule, token_num)
        return float(max(result[3], 0))
