import logging
import traceback
from contextvars import ContextVar, Token
from typing import Any, Callable, Dict, Optional, Set, Type, get_type_hints

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


_CAN_JSON_TYPE_SET: Set[type] = {bool, dict, float, int, list, str, tuple, type(None)}
_FASTAPI_TOOLS_CONTEXT: ContextVar[Dict[str, Any]] = ContextVar("fastapi_tools_context", default={})
_NAMESPACE: str = 'fastapi_tools'
_MISS_OBJECT: object = object()
_REQUEST_KEY: str = _NAMESPACE + ':request'


class BaseContextHelper(object):
    _set: set = set()

    def __init__(self, key: str):
        self._key: key = key
        cls: 'Type[BaseContextHelper]' = self.__class__
        key: str = f'{cls.__name__}:{key}'
        if key in cls._set:
            # key must be globally unique
            raise RuntimeError(f'key:{key} already exists')
        cls._set.add(key)

    def _get_context(self):
        ctx_dict: dict = _FASTAPI_TOOLS_CONTEXT.get()
        return ctx_dict.get(self._key, _MISS_OBJECT)

    def _set_context(self, value):
        ctx_dict: dict = _FASTAPI_TOOLS_CONTEXT.get()
        ctx_dict[self._key] = value

    def __set__(self, instance: 'ContextBaseModel', value: Any):
        self._set_context(value)

    def __get__(self, instance: 'ContextBaseModel', owner: 'Type[ContextBaseModel]'):
        return self._get_context()


class HeaderHelper(BaseContextHelper):
    def __init__(self, key: str, default_func: Optional[Callable] = None):
        self._default_func: Optional[Callable] = default_func

        super().__init__(key)

    def __set__(self, instance: 'ContextBaseModel', value: Any):
        raise NotImplementedError(f'{self.__class__.__name__} not support __set__')

    def __get__(self, instance: 'ContextBaseModel', owner: 'Type[ContextBaseModel]'):
        value = self._get_context()
        if value is not _MISS_OBJECT:
            return value

        ctx_dict: dict = _FASTAPI_TOOLS_CONTEXT.get()
        request: Request = ctx_dict[_NAMESPACE + ':request']
        headers: Headers = request.headers
        if self._key != self._key.lower():
            value: Any = headers.get(self._key) or headers.get(self._key.lower())
        else:
            value: Any = headers.get(self._key)

        if not value and self._default_func is not None:
            value: Any = self._default_func(request)
        self._set_context(value)
        return value


class CustomHelper(BaseContextHelper):
    ...


class ContextBaseModel(object):
    @classmethod
    def to_dict(cls, is_safe_return: bool = False) -> Dict[str, Any]:
        _dict: dict = {}
        for key, value in get_type_hints(cls).items():
            value = getattr(cls, key)
            if is_safe_return and type(value) not in _CAN_JSON_TYPE_SET:
                continue
            _dict[key] = value
        return _dict

    async def before_request(self, request: Request):
        pass

    async def before_reset_context(self, request: Request, response: Response):
        pass


class ContextMiddleware(BaseHTTPMiddleware):

    def __init__(self, context_model: ContextBaseModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_model: ContextBaseModel = context_model

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        context_dict: dict = {_REQUEST_KEY: request}
        token: Token = _FASTAPI_TOOLS_CONTEXT.set(context_dict)
        try:
            await self.context_model.before_request(request)
        except Exception as e:
            logging.error(f'before_request error:{e} traceback info:{traceback.format_exc()}')

        response: Optional[Response] = None
        try:
            response = await call_next(request)
            return response
        finally:
            try:
                await self.context_model.before_reset_context(request, response)
            except Exception as e:
                logging.error(f'before_reset_context error:{e} traceback info:{traceback.format_exc()}')
            _FASTAPI_TOOLS_CONTEXT.reset(token)
