import asyncio
import inspect
import logging
import json
from functools import wraps
from typing import Any, Callable, Awaitable, Dict, List, Optional, Type

from starlette.responses import Response, JSONResponse
from fast_tools.base import RedisHelper


def _check_typing_type(_type, origin_name: str) -> bool:
    try:
        return _type.__origin__ == origin_name
    except AttributeError:
        return False


async def cache_control(response: Response, backend: "RedisHelper", key: str):
    ttl = await backend.redis_pool.ttl(key)
    response.headers["Cache-Control"] = f"max-age={ttl}"


def cache(
    backend: "RedisHelper",
    expire: int = None,
    namespace: str = "fast-tools",
    json_response: Type[JSONResponse] = JSONResponse,
    after_cache_response_list: Optional[List[Callable[[Response, "RedisHelper", str], Awaitable]]] = None,
):
    def wrapper(func):
        @wraps(func)
        async def return_dict_handle(*args, **kwargs):
            key: str = f"{namespace}:{func.__name__}:{args}:{kwargs}"

            while True:
                ret: Dict[str, Any] = await backend.get_dict(key)
                if ret is not None:
                    response: Response = json_response(ret)
                    for after_cache_response in after_cache_response_list:
                        await after_cache_response(response, backend, key)
                    return response
                async with backend.lock(key + ":lock") as lock:
                    if not lock:
                        ret = await func(*args, **kwargs)
                        await backend.set_dict(key, ret, expire)
                        return json_response(ret)
                    else:
                        await asyncio.sleep(0.05)

        @wraps(func)
        async def return_response_handle(*args, **kwargs):
            key: str = f"{namespace}:{func.__name__}:{args}:{kwargs}"

            while True:
                ret: Dict[str, Any] = await backend.get_dict(key)
                if ret is not None:
                    response: Response = return_annotation(**ret)
                    for after_cache_response in after_cache_response_list:
                        await after_cache_response(response, backend, key)
                    return response

                async with backend.lock(key + ":lock") as lock:
                    if not lock:
                        resp: Response = await func(*args, **kwargs)
                        headers: dict = dict(resp.headers)
                        del headers["content-length"]
                        content: str = resp.body.decode()
                        try:
                            content = json.loads(content)
                        except json.JSONDecodeError:
                            pass

                        await backend.set_dict(
                            key,
                            {
                                "content": content,
                                "status_code": resp.status_code,
                                "headers": dict(headers),
                                "media_type": resp.media_type,
                            },
                            expire,
                        )
                        return resp
                    else:
                        await asyncio.sleep(0.05)

        @wraps(func)
        async def return_normal_handle(*args, **kwargs):
            return await func(*args, **kwargs)

        sig: "inspect.signature" = inspect.signature(func)
        return_annotation = sig.return_annotation
        if return_annotation is dict or _check_typing_type(return_annotation, "dict"):
            handle_func: Callable = return_dict_handle
        elif issubclass(return_annotation, Response):
            handle_func: Callable = return_response_handle
        else:
            if return_annotation is sig.empty:
                return_annotation = None

            logging.warning(
                f"func name:{func.__name__} return annotation:{return_annotation}."
                f" Can not use cache."
                f" Please check return annotation in ({dict}, {Dict}, {Response})"
            )
            return return_normal_handle
        logging.debug(
            f"func name:{func.__name__} return annotation:{return_annotation}."
            f" load cache handle {return_dict_handle} success"
        )
        return handle_func

    return wrapper
