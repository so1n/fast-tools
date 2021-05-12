import pytest

from fast_tools.base.lru import LRUCache


class TestLru:
    def test_lru(self) -> None:
        lru_cache: LRUCache[str, int] = LRUCache(3)
        for i in range(4):
            lru_cache.set(str(i), i)

        assert lru_cache.get("0", None) is None
        assert lru_cache.get("1", None) == 1
        lru_cache.set("4", 4)
        assert lru_cache.get("2", None) is None

        with pytest.raises(KeyError):
            lru_cache.get("2")
