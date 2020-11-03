import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional
from fast_tools.limit.rule import Rule
from .base import BaseLimitBackend


@dataclass
class Bucket(object):
    rate: float
    token_num: int
    max_token_num: int
    block_time: float
    block_timestamp: Optional[float] = None


class TokenBucket(BaseLimitBackend):
    def __init__(self, init_token_num: Optional[int] = None, block_time: Optional[int] = None, max_token: int = 100):
        self._init_token_num: int = init_token_num if init_token_num else max_token
        self._max_token_num: int = max_token
        self._block_time: Optional[int] = block_time
        self._cache_dict: Dict[str, "Bucket"] = {}

    def _gen_bucket(self, rule: Rule) -> "Bucket":
        bucket: Bucket = Bucket(
            rate=rule.gen_rate(),
            token_num=rule.init_token_num if rule.init_token_num else self._init_token_num,
            max_token_num=rule.max_token_num if rule.max_token_num else self._max_token_num,
            block_time=rule.block_time if rule.block_time else self._block_time,
        )
        return bucket

    def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        bucket: "Bucket" = self._cache_dict.get(key, self._gen_bucket(rule))
        now_timestamp: float = time.time()
        if bucket.block_timestamp and (bucket.block_timestamp - now_timestamp) > 0:
            return False

        result: bool = False
        if token_num <= self._get_tokens(bucket):
            bucket.token_num -= token_num
            result = True
        else:
            bucket.block_timestamp = now_timestamp + bucket.block_time
        self._cache_dict[key] = bucket
        return result

    def expected_time(self, key: str, rule: Rule) -> float:
        bucket: "Bucket" = self._cache_dict.get(key, self._gen_bucket(rule))
        if bucket.block_timestamp:
            diff_block_time: float = bucket.block_timestamp - time.time()
            if diff_block_time > 0:
                return diff_block_time

        now_token_num: int = self._get_tokens(bucket)

        self._cache_dict[key] = bucket
        if now_token_num < self._cache_dict[key].max_token_num:
            return 0
        else:
            return 1 / bucket.rate

    @staticmethod
    def _get_tokens(bucket: "Bucket") -> int:
        if bucket.token_num < bucket.max_token_num:
            now: float = time.time()
            diff_time: float = now - bucket.block_timestamp
            gen_token = int(diff_time * bucket.rate)
            bucket.block_timestamp = now - (diff_time - int(diff_time))
            bucket.token_num = min(bucket.max_token_num, bucket.token_num + gen_token)
        return bucket.token_num

    def get_token_num(self, key: str) -> int:
        return self._cache_dict[key].token_num


class ThreadingTokenBucket(BaseLimitBackend):
    def __init__(self, token_num: Optional[int] = None, block_time: Optional[int] = None, max_token: int = 100):
        super().__init__(token_num, block_time, max_token)
        self._lock = threading.Lock()

    def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        with self._lock:
            return super().can_requests(key, rule, token_num)

    def expected_time(self, key: str, rule: Rule) -> float:
        with self._lock:
            return super().expected_time(key, rule)


if __name__ == "__main__":
    token_bucket: TokenBucket = TokenBucket(1)
    test_rule: Rule = Rule(second=1, init_token_num=50, max_token_num=100)
    test_key: str = "test"
    print(token_bucket.expected_time(test_key, test_rule))
    print(token_bucket.get_token_num(test_key))
    token_bucket.can_requests(test_key, test_rule)
    print(token_bucket.expected_time(test_key, test_rule))
    print(token_bucket.get_token_num(test_key))
