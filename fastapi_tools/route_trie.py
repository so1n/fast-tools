import logging

from typing import Dict, List, Union, Optional, Set

from starlette.routing import Match, Route
from starlette.types import ASGIApp, Scope


class RouteNode:

    def __init__(
            self,
            route_list: Optional[List[Route]] = None,
            node: Optional[Dict[str, 'RouteNode']] = None
    ):
        self.route_list = route_list if route_list else []
        self.node = node if node else {}


class RouteTrie:

    def __init__(self):
        self.root_node: 'RouteNode' = RouteNode()

        self.root: Dict[str, Union['RouteTrie', dict, Route, List[Route]]] = {}
        self.route_dict: Dict['RouteTrie', List[Route]] = {}

    def insert_by_app(self, app: ASGIApp):
        new_app = app
        while True:
            if hasattr(new_app, 'app'):
                new_app = new_app.app
            else:
                break
        for route in new_app.routes:
            url: str = route.path
            self.insert(url, route)

    def insert(self, url_path: str, route: Route):
        cur_node = self.root_node
        for url_node in url_path.strip().split('/'):
            url_node = url_node + '/'
            if '{' == url_node[0] and '}' == url_node[-2]:
                break
            elif url_node not in cur_node.node:
                cur_node.node[url_node] = RouteNode()
            cur_node = cur_node.node[url_node]
        cur_node.route_list.append(route)

    def search_by_scope(self, url_path: str, scope: Scope) -> Optional[Route]:
        cur_node = self.root_node
        for url_node in url_path.strip().split('/'):
            url_node = url_node + '/'
            if url_node in cur_node.node:
                cur_node = cur_node.node[url_node]
            else:
                break

        for route in cur_node.route_list:
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                return route

    def search(self, url_path: str) -> Optional[List[Route]]:
        cur_node = self.root_node
        for url_node in url_path.strip().split('/'):
            url_node = url_node + '/'
            if url_node in cur_node.node:
                cur_node = cur_node.node[url_node]
            else:
                break
        if cur_node.route_list:
            return cur_node.route_list
