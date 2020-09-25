import asyncio
import inspect
import logging
import json
from functools import wraps
from typing import Any, Dict, Type

from starlette.responses import Response, JSONResponse
from fastapi_tools.base import RedisHelper


def _check_typing_type(_type, origin_name: str) -> bool:
    try:
        return _type.__origin__ == origin_name
    except AttributeError:
        return False


def cache(
    backend: 'RedisHelper',
    expire: int = None,
    namespace: str = "fastapi-tools",
    json_response: Type[JSONResponse] = JSONResponse
):
    def wrapper(func):
        @wraps(func)
        async def return_dict_handle(*args, **kwargs):
            key: str = f'{namespace}:{func.__name__}:{args}:{kwargs}'
            ret: Dict[str, Any] = await backend.get_dict(key)
            if ret is not None:
                return json_response(ret)

            # TODO replace `share`
            while True:
                async with backend.lock(key+':lock') as lock:
                    if not lock:
                        ret = await func(*args, **kwargs)
                        await backend.set_dict(key, ret, expire)
                        return json_response(ret)
                    else:
                        await asyncio.sleep(0.05)

        @wraps(func)
        async def return_response_handle(*args, **kwargs):
            key: str = f'{namespace}:{func.__name__}:{args}:{kwargs}'
            ret: Dict[str, Any] = await backend.get_dict(key)
            if ret is not None:
                return return_annotation(**ret)

            # TODO replace `share`
            while True:
                async with backend.lock(key + ':lock') as lock:
                    if not lock:
                        resp: Response = await func(*args, **kwargs)
                        headers: dict = dict(resp.headers)
                        del headers['content-length']
                        content: str = resp.body.decode()
                        try:
                            content = json.loads(content)
                        except json.JSONDecodeError:
                            pass

                        await backend.set_dict(
                            key,
                            {
                                'content': content,
                                'status_code': resp.status_code,
                                'headers': dict(headers),
                                'media_type': resp.media_type
                            },
                            expire
                        )
                        return resp
                    else:
                        await asyncio.sleep(0.05)

        @wraps(func)
        async def return_normal_handle(*args, **kwargs):
            return await func(*args, **kwargs)

        return_annotation = inspect.signature(func).return_annotation
        if return_annotation is dict or _check_typing_type(return_annotation, 'dict'):
            return return_dict_handle
        elif issubclass(return_annotation, Response):
            return return_response_handle
        else:
            logging.warning(f'{func.__name__} not use cache')
            return return_normal_handle

    return wrapper

