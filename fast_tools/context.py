import logging
import traceback
from contextvars import ContextVar, Token
from typing import Any, Callable, Coroutine, Dict, NoReturn, Optional, Set, Type, get_type_hints

from starlette.datastructures import Headers
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from fast_tools.base.utils import NAMESPACE

_CAN_JSON_TYPE_SET: Set[type] = {bool, dict, float, int, list, str, tuple, type(None)}
_CONTEXT_KEY_SET: Set[str] = set()
_CONTEXT_DICT_TYPE = Dict[str, Any]
_FAST_TOOLS_CONTEXT: ContextVar[Dict[str, Any]] = ContextVar(f"{NAMESPACE}_context", default={})
_MISS_OBJECT: object = object()
_REQUEST_KEY: str = f"{NAMESPACE}_request"


class BaseContextHelper(object):
    """context object encapsulation"""

    def __init__(self, key: str):
        self._key: str = key
        key = f"{self.__class__.__name__}:{key}"
        if key in _CONTEXT_KEY_SET:
            # key must be globally unique
            raise RuntimeError(f"key:{key} already exists")
        _CONTEXT_KEY_SET.add(key)

    def _get_context(self) -> Any:
        """get value by key"""
        ctx_dict: _CONTEXT_DICT_TYPE = _FAST_TOOLS_CONTEXT.get()
        return ctx_dict.get(self._key, _MISS_OBJECT)

    def _set_context(self, value: Any) -> None:
        """set value by key"""
        ctx_dict: _CONTEXT_DICT_TYPE = _FAST_TOOLS_CONTEXT.get()
        ctx_dict[self._key] = value

    def __set__(self, instance: "ContextBaseModel", value: Any) -> Any:
        self._set_context(value)

    def __get__(self, instance: "ContextBaseModel", owner: "Type[ContextBaseModel]") -> Any:
        return self._get_context()

    @classmethod
    def i(cls, key: str) -> Any:
        return cls(key)


class HeaderHelper(BaseContextHelper):
    def __init__(self, key: str, default_func: Optional[Callable] = None):
        self._default_func: Optional[Callable] = default_func
        super().__init__(key)

    def __set__(self, instance: "ContextBaseModel", value: Any) -> NoReturn:
        raise NotImplementedError(f"{self.__class__.__name__} not support __set__")

    def __get__(self, instance: "ContextBaseModel", owner: "Type[ContextBaseModel]") -> Any:
        # get value from context
        value: Any = self._get_context()
        if value is not _MISS_OBJECT:
            return value

        # get request obj from context
        ctx_dict: _CONTEXT_DICT_TYPE = _FAST_TOOLS_CONTEXT.get()
        request: Request = ctx_dict[_REQUEST_KEY]

        # get header value from request
        headers: Headers = request.headers
        if self._key != self._key.lower():
            value = headers.get(self._key) or headers.get(self._key.lower())
        else:
            value = headers.get(self._key)

        if not value and self._default_func is not None:
            value = self._default_func(request)

        # set header value to context
        self._set_context(value)
        return value

    @classmethod
    def i(cls, key: str, default_func: Optional[Callable] = None) -> Any:
        return cls(key, default_func)


class CustomHelper(BaseContextHelper):
    ...


class ContextBaseModel(object):
    @classmethod
    def to_dict(cls, is_safe_return: bool = False) -> Dict[str, Any]:
        _dict: _CONTEXT_DICT_TYPE = {}
        for key, annotation in get_type_hints(cls).items():
            value = getattr(cls, key)
            if is_safe_return and type(value) not in _CAN_JSON_TYPE_SET:
                continue
            _dict[key] = value
        return _dict

    async def before_request(self, request: Request) -> None:
        """Execute before processing the request, usually to initialize the instance"""
        pass

    async def after_response(self, request: Request, response: Response) -> None:
        """Execute after processing the response (if the execution is abnormal, it will not be executed)"""
        pass

    async def before_reset_context(self, request: Request, response: Optional[Response]) -> None:
        """between after response and before reset context execution
        (regardless of whether the response is an exception)"""
        pass


class ContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, context_model: ContextBaseModel, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.context_model: ContextBaseModel = context_model

    @staticmethod
    async def _safe_context_life_handle(corn: Coroutine) -> None:
        try:
            await corn
        except Exception as e:
            logging.error(f"{corn.__name__} error:{e} traceback info:{traceback.format_exc()}")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        context_dict: _CONTEXT_DICT_TYPE = {_REQUEST_KEY: request}
        token: Token = _FAST_TOOLS_CONTEXT.set(context_dict)

        await self._safe_context_life_handle(self.context_model.before_request(request))

        response: Optional[Response] = None
        try:
            response = await call_next(request)
            await self._safe_context_life_handle(self.context_model.after_response(request, response))
            return response
        finally:
            await self._safe_context_life_handle(self.context_model.before_reset_context(request, response))
            _FAST_TOOLS_CONTEXT.reset(token)
