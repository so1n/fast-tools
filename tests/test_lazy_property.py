import time

import pytest

from fast_tools.lazy_property import LazyAsyncPropertyNoParam, LazyProperty, LazyPropertyNoParam

pytestmark = pytest.mark.asyncio


class TestLazyProperty:
    async def test_lazy_property_fun(self) -> None:
        @LazyProperty()
        def _demo(a: int, b: int) -> int:
            return a + b

        @LazyProperty()
        async def _async_demo(a: int, b: int) -> int:
            return a + b

        assert _demo(1, 3) == _demo(1, 4)
        assert await _async_demo(1, 5) == await _async_demo(1, 6)
        assert _demo(2, 1) != await _async_demo(2, 1)

    async def test_lazy_property_class(self) -> None:
        class Demo(object):
            @LazyProperty()
            def demo_func(self, a: int, b: int) -> int:
                return a + b

            @LazyProperty()
            async def async_demo_func(self, a: int, b: int) -> int:
                return a + b

        demo: Demo = Demo()
        demo1: Demo = Demo()
        assert demo.demo_func(1, 2) == demo.demo_func(1, 3)
        assert demo1.demo_func(1, 4) == demo1.demo_func(1, 5)

        assert await demo.async_demo_func(2, 2) == await demo.async_demo_func(2, 3)
        assert await demo1.async_demo_func(2, 4) == await demo1.async_demo_func(2, 5)

        assert demo.demo_func(3, 1) != demo1.demo_func(3, 1)
        assert await demo.async_demo_func(3, 2) != await demo1.async_demo_func(3, 2)

    async def test_lazy_property_not_param(self) -> None:
        class Demo(object):
            @LazyPropertyNoParam
            def demo_func(self) -> float:
                return time.time()

            @LazyAsyncPropertyNoParam
            async def async_demo_func(self) -> float:
                return time.time()

        demo: Demo = Demo()
        demo1: Demo = Demo()

        assert demo.demo_func() == demo.demo_func()
        assert demo.demo_func() != demo1.demo_func()

        assert await demo.async_demo_func() == await demo.async_demo_func()
        assert await demo.async_demo_func() != await demo1.async_demo_func()
