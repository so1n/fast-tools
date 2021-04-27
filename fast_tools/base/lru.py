from collections import OrderedDict
from threading import Lock
from typing import Any, Generic, TypeVar, Union

__all__ = ["LRUCache"]
_MISS_OBJECT = object()
KT = TypeVar("KT")
VT = TypeVar("VT")


class LRUCache(Generic[KT, VT]):
    def __init__(self, capacity: int) -> None:
        self.capacity: int = capacity
        self.cache: OrderedDict[Any, Any] = OrderedDict()
        self._lock: Lock = Lock()

    def __getitem__(self, key: KT) -> VT:
        with self._lock:
            value = self.cache.pop(key)
            self.cache[key] = value
            return value

    def __setitem__(self, key: KT, value: VT) -> None:
        with self._lock:
            if len(self.cache) >= self.capacity:
                self.cache.popitem(last=False)
            if key in self.cache:
                self.cache.pop(key)
            self.cache[key] = value

    def get(self, key: KT, default_value: Union[VT, object] = _MISS_OBJECT) -> VT:
        try:
            return self.__getitem__(key)
        except KeyError as e:
            if default_value is _MISS_OBJECT:
                raise e
            return default_value  # type: ignore

    def set(self, key: KT, value: VT) -> None:
        self.__setitem__(key, value)

