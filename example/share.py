import asyncio
import time
from fastapi_tools.share import Share


async def delay_print(duration: int) -> int:
    await asyncio.sleep(duration)
    return duration


async def run_do(share: 'Share'):
    task_list = [
        share.do('test_do', delay_print, args=[i])
        for i in range(10)
    ]
    print('start', time.time())
    done, _ = await asyncio.wait(task_list)
    print('end', time.time())
    for future in done:
        print(future.result())


async def cancel_in_aio(share: 'Share'):
    await asyncio.sleep(0.1)
    share.cancel()


async def run_cancel(share: 'Share'):
    task_list = [
        share.do('test_cancel', delay_print, args=[i])
        for i in range(10)
    ]
    task_list.append(cancel_in_aio(share))
    print('start', time.time())
    done, _ = await asyncio.wait(task_list)
    print('end', time.time())
    for future in done:
        print(future.result())


def main():
    share: 'Share' = Share()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_do(share))
    loop.run_until_complete(run_cancel(share))


if __name__ == '__main__':
    main()
