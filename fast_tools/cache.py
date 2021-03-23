import inspect
import json
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type

from starlette.responses import JSONResponse, Response

from fast_tools.base import NAMESPACE, RedisHelper


def _check_typing_type(_type: Type, origin_name: str) -> bool:
    try:
        return _type.__origin__ == origin_name
    except AttributeError:
        return False


async def cache_control(response: Response, backend: "RedisHelper", key: str) -> None:
    """add ttl in response header"""
    ttl = await backend.client.ttl(key)
    response.headers["Cache-Control"] = f"max-age={ttl}"


def cache(
    backend: "RedisHelper",
    expire: Optional[int] = None,
    namespace: str = NAMESPACE,
    json_response: Type[JSONResponse] = JSONResponse,
    after_cache_response_list: Optional[List[Callable[[Response, "RedisHelper", str], Awaitable]]] = None,
) -> Callable:
    """
    backend: now only support `RedisHelper`
    expire: cache expiration time
    namespace: key namespace
    json_response: response like `JSONResponse` or `UJSONResponse`
    after_cache_response:list: cache response data handle
    """

    def wrapper(func: Callable) -> Callable:
        @wraps(func)
        async def return_dict_handle(*args: Any, **kwargs: Any) -> Response:
            key: str = f"{namespace}:{func.__name__}:{args}:{kwargs}"

            async def _cache_response_handle(_ret: Dict[str, Any]) -> Response:
                response: Response = json_response(_ret)
                if after_cache_response_list:
                    for after_cache_response in after_cache_response_list:
                        await after_cache_response(response, backend, key)
                return response

            # get cache response data
            ret: Dict[str, Any] = await backend.get_dict(key)
            if ret:
                return await _cache_response_handle(ret)
            else:
                lock = backend.lock(key + ":lock")
                async with lock:
                    # get lock
                    ret = await backend.get_dict(key)
                    # check cache response data
                    if ret:
                        return await _cache_response_handle(ret)
                    else:
                        ret = await func(*args, **kwargs)
                        await backend.set_dict(key, ret, expire)
                        return json_response(ret)

        @wraps(func)
        async def return_response_handle(*args: Any, **kwargs: Any) -> Callable:
            key: str = f"{namespace}:{func.__name__}:{args}:{kwargs}"

            async def _cache_response_handle(_ret: Dict[str, Any]) -> Response:
                response: Response = return_annotation(**_ret)
                if after_cache_response_list:
                    for after_cache_response in after_cache_response_list:
                        await after_cache_response(response, backend, key)
                return response

            ret: Dict[str, Any] = await backend.get_dict(key)
            if ret:
                return await _cache_response_handle(ret)

            lock = backend.lock(key + ":lock")
            async with lock:
                ret = await backend.get_dict(key)
                if ret:
                    return await _cache_response_handle(ret)
                else:
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

        @wraps(func)
        async def return_normal_handle(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        sig: inspect.Signature = inspect.signature(func)
        return_annotation = sig.return_annotation
        if return_annotation is dict or _check_typing_type(return_annotation, "dict"):
            handle_func: Callable = return_dict_handle
        elif issubclass(return_annotation, Response):
            handle_func = return_response_handle
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
