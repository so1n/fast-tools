import logging
import os
import sys
import typing
from collections.abc import MutableMapping
from configparser import ConfigParser
from typing import Any, Dict, ForwardRef, Optional, Tuple, Type, Union

import yaml
from pydantic import BaseModel, create_model

__all__ = ["Config"]


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
        for key in self.__annotations__:
            if key != key.upper():
                class_name: str = self.__class__.__name__
                raise KeyError(f"key: {class_name}.{key} must like {class_name}.{key.upper()}")
            if key not in self._config_dict:
                self._config_dict[key] = getattr(self, key, ...)
            annotation: Union[str, Type] = self.__annotations__[key]
            if isinstance(annotation, str):
                value: ForwardRef = ForwardRef(annotation, is_argument=False)
                annotation = value._evaluate(sys.modules[self.__module__].__dict__, None)  # type: ignore
            annotation_dict[key] = (annotation, ...)

        dynamic_model: Type[BaseModel] = create_model(
            "DynamicModel",
            __config__=None,
            __base__=None,
            __module__="pydantic.main",
            __validators__=None,
            **annotation_dict,
        )
        self.__dict__.update(dynamic_model(**self._config_dict).dict())

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
