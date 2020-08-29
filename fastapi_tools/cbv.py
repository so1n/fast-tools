from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Sequence,
    Type,
    Union
)

from fastapi import APIRouter, Response, params
from fastapi.encoders import (DictIntStrAny, SetIntStr)
from fastapi.routing import APIRoute


__all__ = ['Cbv', 'cbv_decorator']
METHOD_SET: Set[str] = {'get', 'post', 'head', 'options', 'put', 'patch', 'delete'}


class CbvModel(object):
    def __init__(self, func: Callable, kwargs: Dict):
        self.func = func
        self.kwargs = kwargs


def cbv_decorator(
    response_model: Type[Any] = None,
    status_code: int = 200,
    tags: List[str] = None,
    dependencies: Sequence[params.Depends] = None,
    summary: str = None,
    description: str = None,
    response_description: str = "Successful Response",
    responses: Dict[Union[int, str], Dict[str, Any]] = None,
    deprecated: bool = None,
    methods: Optional[Union[Set[str], List[str]]] = None,
    operation_id: str = None,
    response_model_include: Union[SetIntStr, DictIntStrAny] = None,
    response_model_exclude: Union[SetIntStr, DictIntStrAny] = None,
    response_model_by_alias: bool = True,
    response_model_skip_defaults: bool = None,
    response_model_exclude_unset: bool = False,
    response_model_exclude_defaults: bool = False,
    response_model_exclude_none: bool = False,
    include_in_schema: bool = True,
    response_class: Type[Response] = None,
    name: str = None,
    route_class_override: Optional[Type[APIRoute]] = None,
    callbacks: List[APIRoute] = None,
):
    if response_model_exclude is None:
        response_model_exclude = set()
    kwargs = {
        'response_model': response_model,
        'status_code': status_code,
        'tags': tags,
        'dependencies': dependencies,
        'summary': summary,
        'description': description,
        'response_description': response_description,
        'responses': responses,
        'deprecated': deprecated,
        'methods': methods,
        'operation_id': operation_id,
        'response_model_include': response_model_include,
        'response_model_exclude': response_model_exclude,
        'response_model_by_alias': response_model_by_alias,
        'response_model_skip_defaults': response_model_skip_defaults,
        'response_model_exclude_unset': response_model_exclude_unset,
        'response_model_exclude_defaults': response_model_exclude_defaults,
        'response_model_exclude_none': response_model_exclude_none,
        'include_in_schema': include_in_schema,
        'response_class': response_class,
        'name': name,
        'route_class_override': route_class_override,
        'callbacks': callbacks,
    }

    def wrapper(func: Callable):
        return CbvModel(func, kwargs)
    return wrapper


class Cbv(object):

    def __init__(self, url: str = '/'):
        self._url = url
        self.router: APIRouter = APIRouter()

        self._add_router()

    def _add_router(self):
        for _dir in self.__dir__():
            if _dir in METHOD_SET:
                cbv_method = getattr(self, _dir)
                if isinstance(cbv_method, CbvModel):
                    cbv_method.kwargs['methods'] = [_dir.upper()]
                    self.router.add_api_route(self._url, cbv_method.func, **cbv_method.kwargs)
                else:
                    self.router.add_api_route(self._url, cbv_method, methods=[_dir.upper()])
