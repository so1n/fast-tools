from collections import OrderedDict
from dataclasses import MISSING
from threading import Lock
from typing import Any, Generic, TypeVar, Union

__all__ = ["LRUCache"]
KT = TypeVar("KT")
VT = TypeVar("VT")


class LRUCache(Generic[KT, VT]):
    def __init__(self, capacity: int) -> None:
        self.capacity: int = capacity
        self.cache: OrderedDict[Any, Any] = OrderedDict()

    def _get(self, key: KT) -> VT:
        value = self.cache.pop(key)
        self.cache[key] = value
        return value

    def _set(self, key: KT, value: VT) -> None:
        if key in self.cache:
            self.cache.pop(key)
        elif len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[key] = value

    def __getitem__(self, key: KT) -> VT:
        return self._get(key)

    def __setitem__(self, key: KT, value: VT) -> None:
        self._set(key, value)

    def get(self, key: KT, default_value: Union[VT, object] = MISSING) -> VT:
        try:
            return self._get(key)
        except KeyError as e:
            if default_value is MISSING:
                raise e
            return default_value  # type: ignore

    def set(self, key: KT, value: VT) -> None:
        self._set(key, value)


class ThreadLRUCache(LRUCache):
    def __init__(self, capacity: int) -> None:
        super().__init__(capacity)
        self._lock: Lock = Lock()

    def _get(self, key: KT) -> VT:
        with self._lock:
            return super(ThreadLRUCache, self)._get(key)

    def _set(self, key: KT, value: VT) -> None:
        with self._lock:
            super(ThreadLRUCache, self)._set(key, value)
