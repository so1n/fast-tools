import asyncio
import logging
from functools import wraps
from traceback import format_exception
from typing import Any, Callable, Coroutine, Dict, Optional, Union

from starlette.concurrency import run_in_threadpool

__all__ = ["stop_task", "background_task"]

FuncT = Callable[[], None]
AsyncFuncT = Callable[[], Coroutine[Any, Any, None]]


future_dict: Dict[str, asyncio.Future] = {}


def background_task(
    *,
    seconds: Optional[float] = None,
    key: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
    raise_exceptions: bool = False,
    max_retry: Optional[int] = None,
) -> Callable[[Union[FuncT, AsyncFuncT]], AsyncFuncT]:
    def decorator(func: Union[AsyncFuncT, FuncT]) -> AsyncFuncT:
        @wraps(func)
        async def wrapped():
            nonlocal key
            if key is None:
                key = func.__name__

            async def job():
                retry_cnt = 0
                while max_retry is None or retry_cnt < max_retry:
                    try:
                        if asyncio.iscoroutinefunction(func):
                            await func()
                        else:
                            await run_in_threadpool(func)
                        break
                    except Exception as e:
                        if raise_exceptions:
                            raise e
                        else:
                            retry_cnt += 1
                            future = future_dict.get(key, None)
                            if future:
                                future.set_exception(e)
                    await asyncio.sleep(retry_cnt * retry_cnt)

                future = future_dict.get(key, None)
                if future and future.done():
                    result = future.result()
                    if isinstance(result, Exception):
                        format_e = "".join(format_exception(type(result), result, result.__traceback__))
                        if logger is not None:
                            logger.error(format_e)
                        else:
                            logging.error(format_e)

            async def task_loop():
                while True:
                    future = future_dict.get(key, None)
                    if future is not None:
                        if future.cancelled():
                            break
                        elif not future.done():
                            await asyncio.sleep(1)
                    future = asyncio.ensure_future(job())
                    future_dict[key] = future
                    if seconds:
                        await asyncio.sleep(seconds)
                    else:
                        break

            asyncio.ensure_future(task_loop())

        return wrapped

    return decorator


def _stop_task(key: str, future: asyncio.Future):
    if not future.cancelled():
        future.cancel()
        logging.info(f"cancel task:{key}")
    else:
        logging.warning(f"task:{key} already cancel")


def stop_task(key: Optional[str] = None):
    if key and key in future_dict:
        future = future_dict[key]
        _stop_task(key, future)
    else:
        for key, future in future_dict.items():
            _stop_task(key, future)
