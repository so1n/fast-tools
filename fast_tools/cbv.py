import inspect

from typing import Any, Callable, Dict, List, Optional, Set, Sequence, Type, Union, get_type_hints

from fastapi import APIRouter, Response, params, Depends
from fastapi.encoders import DictIntStrAny, SetIntStr
from fastapi.routing import APIRoute
from pydantic.typing import is_classvar


__all__ = ["Cbv", "cbv_decorator"]
METHOD_SET: Set[str] = {"get", "post", "head", "options", "put", "patch", "delete"}
ROUTE_ATTRIBUTES_DICT: Dict[str, Dict[str, Any]] = {}


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
) -> Callable:
    if response_model_exclude is None:
        response_model_exclude = set()
    kwargs: Dict[str, Any] = {
        "response_model": response_model,
        "status_code": status_code,
        "tags": tags,
        "dependencies": dependencies,
        "summary": summary,
        "description": description,
        "response_description": response_description,
        "responses": responses,
        "deprecated": deprecated,
        "methods": methods,
        "operation_id": operation_id,
        "response_model_include": response_model_include,
        "response_model_exclude": response_model_exclude,
        "response_model_by_alias": response_model_by_alias,
        "response_model_skip_defaults": response_model_skip_defaults,
        "response_model_exclude_unset": response_model_exclude_unset,
        "response_model_exclude_defaults": response_model_exclude_defaults,
        "response_model_exclude_none": response_model_exclude_none,
        "include_in_schema": include_in_schema,
        "response_class": response_class,
        "name": name,
        "route_class_override": route_class_override,
        "callbacks": callbacks,
    }

    def wrapper(func: Callable) -> Callable:
        ROUTE_ATTRIBUTES_DICT[func.__qualname__] = kwargs
        return func

    return wrapper


class Cbv(object):
    def __init__(self, obj, url: str = "/"):
        self._url: str = url
        self.router: APIRouter = APIRouter()
        self._obj: Type = obj

        self._init_obj()
        self._add_router()

    def _add_router(self):
        for _dir in dir(self._obj):
            if _dir not in METHOD_SET:
                continue

            func: Callable = getattr(self._obj, _dir)
            func_attributes: Dict[str, Any] = ROUTE_ATTRIBUTES_DICT.get(func.__qualname__, None)
            if func_attributes is not None:
                kwargs: Dict[str, Any] = func_attributes
            else:
                kwargs: Dict[str, Any] = {}
            kwargs["methods"] = [_dir.upper()]

            attributes: str = f"{self._obj.__name__}.{func.__name__}"
            name: Optional[str] = kwargs.get("name", None)
            if name is None:
                name = attributes
            else:
                name = name + f"({attributes})"
            kwargs["name"] = name

            self.router.add_api_route(self._url, self._init_cbv(func), **kwargs)

    def _init_cbv(self, func: Callable) -> Callable:
        """fork from https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/cbv.py#L89"""
        old_signature = inspect.signature(func)
        old_parameters: List[inspect.Parameter] = list(old_signature.parameters.values())
        self_param = old_parameters[0]
        new_self_param = self_param.replace(default=Depends(self._obj))
        new_parameters = [new_self_param] + [
            parameter.replace(kind=inspect.Parameter.KEYWORD_ONLY) for parameter in old_parameters[1:]
        ]
        new_signature = old_signature.replace(parameters=new_parameters)
        setattr(func, "__signature__", new_signature)
        return func

    def _init_obj(self) -> None:
        """fork from https://github.com/dmontagu/fastapi-utils/blob/master/fastapi_utils/cbv.py#L53"""
        cls = self._obj
        old_init: Callable[..., Any] = cls.__init__
        old_signature = inspect.signature(old_init)
        old_parameters = list(old_signature.parameters.values())[1:]  # drop `self` parameter
        new_parameters = [
            x for x in old_parameters if x.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        ]
        dependency_names: List[str] = []
        for name, hint in get_type_hints(cls).items():
            if is_classvar(hint):
                continue
            parameter_kwargs = {"default": getattr(cls, name, Ellipsis)}
            dependency_names.append(name)
            new_parameters.append(
                inspect.Parameter(name=name, kind=inspect.Parameter.KEYWORD_ONLY, annotation=hint, **parameter_kwargs)
            )
        new_signature = old_signature.replace(parameters=new_parameters)
        setattr(cls, "__signature__", new_signature)

        def new_init(_self: Any, *args: Any, **kwargs: Any) -> None:
            for dep_name in dependency_names:
                dep_value = kwargs.pop(dep_name)
                setattr(_self, dep_name, dep_value)
            old_init(_self, *args, **kwargs)

        setattr(cls, "__init__", new_init)
