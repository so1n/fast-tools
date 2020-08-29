from typing import Set
from fastapi import APIRouter


class Cbv(object):
    _method_set: Set[str] = {'get', 'post', 'head', 'options', 'put', 'patch', 'delete'}

    def __init__(self, url: str = '/'):
        self._url = url
        self.router: APIRouter = APIRouter()

        self._add_router()

    def _add_router(self):
        for _dir in self.__dir__():
            if _dir in self._method_set:
                self.router.add_api_route(self._url, getattr(self, _dir), methods=[_dir.upper()])
