import time

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional


@dataclass
class Rule(object):
    second: int = 0
    minute: int = 0
    hour: int = 0
    day: int = 0
    week: int = 0

    max_token: Optional[int] = None
    gen_token: int = 1
    token_num: Optional[int] = None

    block_time: Optional[int] = None

    _kwargs: Optional[Dict[str, Any]] = None

    def gen_second(self) -> float:
        return timedelta(
            weeks=self.week,
            days=self.day,
            hours=self.hour,
            minutes=self.minute,
            seconds=self.second
        ).total_seconds()

    def gen_rate(self) -> int:
        """
        gen_second: 60 gen_token: 1  = 1 req/m
        gen_second: 1  gen_token: 1000 = 1000 req/s = 1 req/ms
        """
        return int(self.gen_token / self.gen_second())

    def gen_kwargs(self) -> Dict[str, Any]:
        if not self._kwargs:
            self._kwargs: Dict[str, Any] = {
                'rate': self.gen_rate(),
                'timestamp': time.time(),
            }
            for key in ['token_num', 'max_token', 'block_time']:
                value = getattr(self, key, None)
                if value is not None:
                    self._kwargs[key] = value
        return self._kwargs
