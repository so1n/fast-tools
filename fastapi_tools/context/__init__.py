import abc
from contextvars import ContextVar
from contextvars import copy_context
from contextvars import Token
from typing import Any, Callable, Dict, KeysView, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response


_fastapi_tools_context: ContextVar[Dict[str, Any]] = ContextVar(
    "fastapi_tools_context", default={}
)


class BaseContextQuery(metaclass=abc.ABCMeta):
    _set: set = set()

    def __init__(self, key: str):
        self._key = key
        cls = self.__class__
        key: str = f'{cls.__name__}:{key}'
        if key in cls._set:
            # var must be globally unique
            raise RuntimeError(f'key:{key} already exists')
        cls._set.add(key)

    def __get__(self, instance, owner):
        ctx_dict: dict = _fastapi_tools_context.get()
        return ctx_dict[self._key]

    def __set__(self, instance, request: Request):
        pass

    def _set_cache(self, instance, value):
        getattr(instance, '_cache_dict')[self._key] = value


class HeaderQuery(BaseContextQuery):
    def __init__(self, key: str, default_func: Optional[Callable] = None):
        self._default_func = default_func
        super().__init__(key)

    def __set__(self, instance, request: Request):
        if self._key != self._key.lower():
            headers = request.headers
            value = headers.get(self._key) or headers.get(self._key.lower())
        else:
            value = request.headers.get(self._key)

        if not value and self._default_func is not None:
            value = self._default_func(request)
        # TODO check type hint
        self._set_cache(instance, value)


class CustomQuery(BaseContextQuery):
    def __init__(self, value):
        self._value = value
        super().__init__('custom:' + str(id(value)))

    def __set__(self, instance, request: Request):
        self._set_cache(instance, self._value)


class ContextBaseModel(object):
    def __init__(self):
        self._cache_dict: dict = {}

    @staticmethod
    def exists() -> bool:
        return _fastapi_tools_context in copy_context()

    def _get_var(self) -> KeysView[str]:
        return self.__annotations__.keys()

    def set_context(self, request: Request) -> Token:
        self._cache_dict = {}
        for key in self._get_var():
            setattr(self, key, request)
        return _fastapi_tools_context.set(self._cache_dict)

    @staticmethod
    def to_dict() -> Dict[str, Any]:
        return _fastapi_tools_context.get()


class ContextMiddleware(BaseHTTPMiddleware):

    def __init__(self, context_model: ContextBaseModel, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context_model: ContextBaseModel = context_model

    async def dispatch(
            self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        context_token: Token = self.context_model.set_context(request)
        try:
            response = await call_next(request)
        finally:
            _fastapi_tools_context.reset(context_token)
        return response
