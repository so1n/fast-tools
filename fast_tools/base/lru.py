from collections import OrderedDict
from threading import Lock
from typing import Any, Optional

__all__ = ["LRUCache"]
_MISS_OBJECT = object()


class LRUCache:
    def __init__(self, capacity: int) -> None:
        self.capacity: int = capacity
        self.cache: OrderedDict[Any, Any] = OrderedDict()
        self._lock: Lock = Lock()

    def get(self, key: Any, default_value: Optional[Any] = _MISS_OBJECT) -> Any:
        with self._lock:
            try:
                value = self.cache.pop(key)
                self.cache[key] = value
                return value
            except KeyError as e:
                if default_value is _MISS_OBJECT:
                    raise e
                return default_value

    def set(self, key: Any, value: Any) -> Any:
        with self._lock:
            try:
                self.cache.pop(key)
            except KeyError:
                if len(self.cache) >= self.capacity:
                    self.cache.popitem(last=False)
            self.cache[key] = value
