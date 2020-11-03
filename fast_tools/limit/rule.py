import time

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional


@dataclass
class Rule(object):
    # gen_second param
    second: int = 0
    minute: int = 0
    hour: int = 0
    day: int = 0
    week: int = 0

    max_token_num: Optional[int] = None  # Maximum number of tokens per bucket
    gen_token_num: int = 1  # The number of tokens generated per unit time
    init_token_num: Optional[int] = None  # The initial number of tokens in the bucket

    group: Optional[str] = None

    block_time: Optional[int] = None

    _kwargs: Optional[Dict[str, Any]] = None

    def gen_second(self) -> float:
        """How long does it take to generate token"""
        return timedelta(
            weeks=self.week, days=self.day, hours=self.hour, minutes=self.minute, seconds=self.second
        ).total_seconds()

    def gen_rate(self) -> float:
        """
        gen_second: 60 gen_token: 1  = 1 req/m
        gen_second: 1  gen_token: 1000 = 1000 req/s = 1 req/ms
        """
        return self.gen_token_num / self.gen_second()
