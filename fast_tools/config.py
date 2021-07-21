import json
import logging
import os
import sys
import typing
from collections.abc import MutableMapping
from configparser import ConfigParser
from typing import Any, Dict, ForwardRef, Optional, Tuple, Type, Union

import yaml
from pydantic import BaseModel, create_model
from pydantic.fields import FieldInfo, NoArgAnyCallable, Undefined

__all__ = ["Config", "Environ", "EnvironError", "Json"]


class EnvironError(Exception):
    pass


class Environ(MutableMapping):
    """
    copy from starlette
    """

    def __init__(self, _environ: typing.MutableMapping = os.environ):
        self._environ = _environ
        self._has_been_read_set = set()  # type: typing.Set[typing.Any]

    def __getitem__(self, key: typing.Any) -> typing.Any:
        self._has_been_read_set.add(key)
        return self._environ.__getitem__(key)

    def __setitem__(self, key: typing.Any, value: typing.Any) -> None:
        if key in self._has_been_read_set:
            raise EnvironError(f"Attempting to set environ['{key}'], but the value has already been read.")
        self._environ.__setitem__(key, value)

    def __delitem__(self, key: typing.Any) -> None:
        if key in self._has_been_read_set:
            raise EnvironError(f"Attempting to delete environ['{key}'], but the value has already been read.")
        self._environ.__delitem__(key)

    def __iter__(self) -> typing.Iterator:
        return iter(self._environ)

    def __len__(self) -> int:
        return len(self._environ)


environ = Environ()


class BaseField(FieldInfo):
    def __init__(
        self,
        default: Any = Undefined,
        *,
        default_factory: Optional[NoArgAnyCallable] = None,
        alias: str = None,
        title: str = None,
        description: str = None,
        const: bool = None,
        gt: float = None,
        ge: float = None,
        lt: float = None,
        le: float = None,
        multiple_of: float = None,
        min_items: int = None,
        max_items: int = None,
        min_length: int = None,
        max_length: int = None,
        regex: str = None,
        **extra: Any,
    ):
        if self.__class__.__mro__[2] != FieldInfo:
            raise RuntimeError("Only classes that inherit BaseField can be used")
        super().__init__(
            default,
            default_factory=default_factory,
            alias=alias,
            title=title,
            description=description,
            const=const,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            multiple_of=multiple_of,
            min_items=min_items,
            max_items=max_items,
            min_length=min_length,
            max_length=max_length,
            regex=regex,
            **extra,
        )

    @classmethod
    def i(
        cls,
        default: Any = Undefined,
        *,
        default_factory: Optional[NoArgAnyCallable] = None,
        alias: str = None,
        title: str = None,
        description: str = None,
        const: bool = None,
        gt: float = None,
        ge: float = None,
        lt: float = None,
        le: float = None,
        multiple_of: float = None,
        min_items: int = None,
        max_items: int = None,
        min_length: int = None,
        max_length: int = None,
        regex: str = None,
        **extra: Any,
    ) -> Any:
        """ignore mypy tip"""
        return cls(
            default,
            default_factory=default_factory,
            alias=alias,
            title=title,
            description=description,
            const=const,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            multiple_of=multiple_of,
            min_items=min_items,
            max_items=max_items,
            min_length=min_length,
            max_length=max_length,
            regex=regex,
            **extra,
        )


class Json(BaseField):
    ...


class Config:
    def __init__(
        self,
        config_file: Optional[str] = None,
        group: Optional[str] = None,
        global_key: str = "global",
        loan_env_file: bool = False,
    ) -> None:
        if loan_env_file:
            try:
                from environs import Env

                Env().read_env()
            except ImportError as e:
                logging.warn("read .env fail, please run `pip install environs`")
                raise e

        self._config_dict: Dict[str, Any] = {}
        self._model: Optional[BaseModel] = None
        if group:
            self._group = group
        elif "group" in environ:
            self._group = environ["group"]
        else:
            raise RuntimeError("Miss param `group` in __init__ or env")
        self._global_key = global_key

        if config_file is not None and os.path.isfile(config_file):
            self._read_file(config_file)
        else:
            self._config_dict = {key: value for key, value in environ.items()}
        self._init_obj()

    def _init_obj(self) -> None:
        annotation_dict: Dict[str, Tuple[Any, ...]] = {}
        for _class in self.__class__.mro():
            for key in getattr(_class, "__annotations__", []):
                if key != key.upper():
                    class_name: str = _class.__name__
                    raise KeyError(f"key: {class_name}.{key} must like {class_name}.{key.upper()}")

                default_value: Any = getattr(self, key, ...)
                annotation: Union[str, Type] = _class.__annotations__[key]
                if isinstance(annotation, str):
                    value: ForwardRef = ForwardRef(annotation, is_argument=False)
                    annotation = value._evaluate(sys.modules[self.__module__].__dict__, None)  # type: ignore

                if isinstance(default_value, Json) and key in self._config_dict:
                    self._config_dict[key] = json.loads(self._config_dict[key])

                if key not in self._config_dict:
                    self._config_dict[key] = default_value

                annotation_dict[key] = (annotation, ... if not isinstance(default_value, FieldInfo) else default_value)

        dynamic_model: Type[BaseModel] = create_model(
            "DynamicModel",
            __config__=None,
            __base__=None,
            __module__="pydantic.main",
            __validators__=None,
            **annotation_dict,
        )
        self._model = dynamic_model(**self._config_dict)
        self.__dict__.update(self._model.dict())

    @property
    def model(self) -> BaseModel:
        if not self._model:
            raise ValueError("Can not found model")
        return self._model

    def _read_file(self, file_name: str) -> None:
        if file_name.endswith(".yml"):
            with open(file_name) as input_file:
                _dict: Dict[str, Dict[str, Any]] = yaml.load(input_file, Loader=yaml.FullLoader)
                self._config_dict = _dict[self._global_key]
                self._config_dict.update(_dict[self._group])
        elif file_name.endswith(".ini"):
            cf: "ConfigParser" = ConfigParser()
            cf.read(file_name)
            self._config_dict = {key.upper(): value for key, value in cf.items(self._global_key)}
            self._config_dict.update({key.upper(): value for key, value in cf.items(self._group)})
        else:
            try:
                name, suffix = file_name.split(".")
            except Exception:
                raise RuntimeError(f"Not support {file_name}")
            raise RuntimeError(f"Not support {suffix}")

    def __str__(self) -> str:
        return str(
            [
                {"name": key, "value": self.__dict__[key], "type": str(type(self.__dict__[key]))}
                for key in self._config_dict.keys()
            ]
        )
