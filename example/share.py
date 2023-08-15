import asyncio
import time
from typing import Coroutine, List

from fast_tools.share import Share


async def delay_print(duration: int) -> int:
    sleep_time: int = duration
    if sleep_time > 1:
        sleep_time = 1
    await asyncio.sleep(sleep_time)
    return duration


async def run_do(share: "Share") -> None:
    task_list = [share.do("test_do", delay_print, args=[i]) for i in [1, 2, 3, 4, 5, 6, 7, 8, 9]]
    print("run do start", time.time())
    done, _ = await asyncio.wait(task_list)
    print("run do end", time.time())
    print("run do result", [future.result() for future in done])


async def cancel_in_aio(share: "Share") -> None:
    await asyncio.sleep(0.1)
    share.cancel()


async def run_cancel_in_aio(share: "Share") -> None:
    task_list: "List[Coroutine]" = [
        share.do("test_cancel_in_aio", delay_print, args=[i]) for i in [11, 12, 13, 14, 15, 16, 17, 18, 19]
    ]
    task_list.append(cancel_in_aio(share))
    print("run cancel in aio start", time.time())
    t_list = [asyncio.Task(t) for t in task_list]
    await asyncio.sleep(1)

    result = []
    for t in t_list:
        try:
            await t
            result.append(1)
        except asyncio.CancelledError:
            result.append(0)
    print("run cancel in aio end", result)


async def must_cancel_coro() -> None:
    await asyncio.sleep(0)
    raise asyncio.CancelledError("must cancel")


async def run_cancel(share: "Share") -> None:
    task_list = [share.do("test_cancel", must_cancel_coro) for _ in range(10)]
    print("run cancel start", time.time())
    t_list = [asyncio.Task(t) for t in task_list]
    await asyncio.sleep(1)
    result = []
    for t in t_list:
        try:
            await t
            result.append(1)
        except asyncio.CancelledError:
            result.append(0)
    print("run cancel end", result)


async def run_wapper_do(share: "Share") -> None:
    @share.wrapper_do()
    async def test_wapper_do(num: int) -> int:
        print(f"call wapper :{num}")
        return await delay_print(num)

    task_list = [test_wapper_do(i) for i in [21, 22, 23, 24, 25, 26, 27, 28, 29]]
    print("run wapper do start", time.time())
    done, _ = await asyncio.wait(task_list)
    print("run wapper do end", time.time())
    print("run wapper do result", [future.result() for future in done])


async def run_class_wapper_do(share: "Share") -> None:
    class TestClassWapperDo(object):
        @share.wrapper_do()
        async def delay_print(self, num: int) -> int:
            print(f"call class wapper :{num}")
            return await delay_print(num)

    test_class_wapper_do: "TestClassWapperDo" = TestClassWapperDo()
    print(test_class_wapper_do.delay_print.__qualname__)

    task_list = [test_class_wapper_do.delay_print(i) for i in [21, 22, 23, 24, 25, 26, 27, 28, 29]]
    print("run class wapper do start", time.time())
    done, _ = await asyncio.wait(task_list)
    print("run class wapper do end", time.time())
    print("run class wapper do result", [future.result() for future in done])


def main() -> None:
    share: "Share" = Share()

    loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
    # loop.run_until_complete(run_wapper_do(share))
    # loop.run_until_complete(run_do(share))
    # loop.run_until_complete(run_cancel(share))
    # loop.run_until_complete(run_cancel_in_aio(share))
    # loop.run_until_complete(run_wapper_do(share))
    loop.run_until_complete(run_class_wapper_do(share))


if __name__ == "__main__":
    main()
