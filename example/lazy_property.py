import asyncio
from fast_tools.lazy_property import LazyProperty


class Demo(object):
    @LazyProperty()
    def demo1_func(self, a: int, b: int) -> int:
        return a + b

    @LazyProperty()
    async def demo2_func(self, a: int, b: int) -> int:
        return a + b


demo: Demo = Demo()
print(demo.demo1_func(1, 2))
print(demo.demo1_func(1, 3))
print(asyncio.run(demo.demo2_func(2, 2)))
print(asyncio.run(demo.demo2_func(2, 3)))
