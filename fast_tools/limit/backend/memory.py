import threading
import time
from dataclasses import dataclass
from typing import Optional

from fast_tools.base import LRUCache
from fast_tools.limit.rule import Rule

from .base import BaseLimitBackend  # type: ignore


@dataclass
class Bucket(object):
    rate: float
    token_num: int
    max_token_num: int
    block_time: Optional[float]
    block_timestamp: float = 0


class TokenBucket(BaseLimitBackend):
    def __init__(self) -> None:
        self._cache_dict: LRUCache = LRUCache(10000)

    @staticmethod
    def _gen_bucket(rule: Rule) -> "Bucket":
        bucket: Bucket = Bucket(
            rate=rule.rate,
            token_num=rule.init_token_num,
            max_token_num=rule.max_token_num,
            block_time=rule.block_time,
        )
        return bucket

    def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        bucket: "Bucket" = self._cache_dict.get(key, self._gen_bucket(rule))
        now_timestamp: float = time.time()
        if bucket.block_time and bucket.block_timestamp - now_timestamp > 0:
            return False

        can_request: bool = False
        self._update_tokens(bucket)
        if token_num <= bucket.token_num:
            bucket.token_num -= token_num
            can_request = True
        elif bucket.block_time:
            bucket.block_timestamp = now_timestamp + bucket.block_time
        self._cache_dict.set(key, bucket)
        return can_request

    def expected_time(self, key: str, rule: Rule) -> float:
        bucket: "Bucket" = self._cache_dict.get(key, self._gen_bucket(rule))
        if bucket.block_timestamp:
            diff_block_time: float = bucket.block_timestamp - time.time()
            if diff_block_time > 0:
                return diff_block_time

        now_token_num: int = self._update_tokens(bucket)

        self._cache_dict.set(key, bucket)
        if now_token_num < bucket.max_token_num:
            return 0
        else:
            return 1 / bucket.rate

    @staticmethod
    def _update_tokens(bucket: "Bucket") -> int:
        if bucket.token_num < bucket.max_token_num:
            now: float = time.time()
            diff_time: float = now - bucket.block_timestamp
            gen_token = int(diff_time * bucket.rate)
            bucket.block_timestamp = now - (diff_time - int(diff_time))
            bucket.token_num = min(bucket.max_token_num, bucket.token_num + gen_token)
        return bucket.token_num

    def get_token_num(self, key: str) -> int:
        return self._cache_dict.get(key).token_num


class ThreadingTokenBucket(TokenBucket):
    def __init__(self) -> None:
        super().__init__()
        self._lock: "threading.Lock" = threading.Lock()

    def can_requests(self, key: str, rule: Rule, token_num: int = 1) -> bool:
        with self._lock:
            return super().can_requests(key, rule, token_num)

    def expected_time(self, key: str, rule: Rule) -> float:
        with self._lock:
            return super().expected_time(key, rule)


if __name__ == "__main__":
    token_bucket: TokenBucket = TokenBucket()
    test_rule: Rule = Rule(second=1, init_token_num=50, max_token_num=100)
    test_key: str = "test"
    print(token_bucket.expected_time(test_key, test_rule))
    print(token_bucket.get_token_num(test_key))
    token_bucket.can_requests(test_key, test_rule)
    print(token_bucket.expected_time(test_key, test_rule))
    print(token_bucket.get_token_num(test_key))
