import inspect
import logging
from functools import wraps
from typing import Any, Awaitable, Callable, Dict, List, Optional, Type

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from fast_tools.base import NAMESPACE, json, redis_helper


def _check_typing_type(_type: Type, origin_name: str) -> bool:
    try:
        return _type.__origin__ == origin_name  # type: ignore
    except AttributeError:
        return False


async def cache_control(response: Response, backend: "redis_helper.RedisHelper", key: str) -> None:
    """add ttl in response header"""
    ttl = await backend.client.ttl(key)
    response.headers["Cache-Control"] = f"max-age={ttl}"


def cache(
    backend: "redis_helper.RedisHelper",
    expire: Optional[int] = None,
    namespace: str = NAMESPACE,
    alias: Optional[str] = None,
    json_response: Type[JSONResponse] = JSONResponse,
    get_key_func: Optional[Callable[[Request], Awaitable[str]]] = None,
    after_cache_response_list: Optional[List[Callable[[Response, "redis_helper.RedisHelper", str], Awaitable]]] = None,
) -> Callable:
    """
    backend: now only support `RedisHelper`
    expire: cache expiration time
    namespace: key namespace
    alias: func alias name
    json_response: response like `JSONResponse` or `UJSONResponse`
    get_key_func:
    after_cache_response:list: cache response data handle
    """

    def wrapper(func: Callable) -> Callable:
        prefix: str = f"{namespace}:{alias or func.__name__}"

        async def _get_key(args: Any, kwargs: Any) -> str:
            if get_key_func:
                for arg in kwargs.values():
                    if isinstance(arg, Request):
                        request: Request = arg
                        break
                else:
                    raise ValueError("Can not found request param")
                key: str = f"{prefix}:{await get_key_func(request)}"
            else:
                key = f"{prefix}:{args}:{kwargs}"
            return key

        async def _cache_response_handle(response: Response, key: str) -> Response:
            if after_cache_response_list:
                for after_cache_response in after_cache_response_list:
                    await after_cache_response(response, backend, key)
            return response

        @wraps(func)
        async def return_dict_handle(*args: Any, **kwargs: Any) -> Response:
            key: str = await _get_key(args, kwargs)

            # get cache response data
            ret: Dict[str, Any] = await backend.get_dict(key)
            if ret:
                return await _cache_response_handle(json_response(ret), key)

            async with backend.lock(key + ":lock"):
                # get lock
                ret = await backend.get_dict(key)
                # check cache response data
                if ret:
                    return await _cache_response_handle(json_response(ret), key)
                else:
                    ret = await func(*args, **kwargs)
                    await backend.set_dict(key, ret, expire)
            return json_response(ret)

        @wraps(func)
        async def return_response_handle(*args: Any, **kwargs: Any) -> Callable:
            key: str = await _get_key(args, kwargs)
            ret: Dict[str, Any] = await backend.get_dict(key)
            if ret:
                return await _cache_response_handle(return_annotation(**ret), key)

            async with backend.lock(key + ":lock"):
                ret = await backend.get_dict(key)
                if ret:
                    return await _cache_response_handle(return_annotation(**ret), key)
                else:
                    resp: Response = await func(*args, **kwargs)
                    headers: dict = dict(resp.headers)
                    del headers["content-length"]
                    content: str = resp.body.decode()
                    try:
                        content = json.loads(content)
                    except json.JSONDecodeError as e:
                        logging.exception(e)
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
