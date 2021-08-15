from typing import Dict, List, Optional, Union

from starlette.routing import Match, Route
from starlette.types import ASGIApp, Scope


class RouteNode:
    def __init__(
        self,
        route_list: Optional[List[Route]] = None,
        node: Optional[Dict[str, "RouteNode"]] = None,
    ):
        self.route_list: List[Route] = route_list if route_list else []
        self.node: Dict[str, "RouteNode"] = node if node else dict()


class RouteTrie:
    def __init__(self) -> None:
        self.root_node: "RouteNode" = RouteNode()

        self.root: Dict[str, Union["RouteTrie", dict, Route, List[Route]]] = {}
        self.route_dict: Dict["RouteTrie", List[Route]] = {}

    def insert_by_app(self, app: ASGIApp) -> None:
        while True:
            sub_app: ASGIApp = getattr(app, "app", None)
            if not sub_app:
                break
            app = sub_app
        for route in app.routes:
            url: str = route.path
            self.insert(url, route)

    def insert(self, url_path: str, route: Route) -> None:
        cur_node: "RouteNode" = self.root_node
        for node_url in url_path.strip().split("/"):
            if node_url and "{" == node_url[0] and "}" == node_url[-1]:
                break
            elif node_url not in cur_node.node:
                cur_node.node[node_url] = RouteNode()
            cur_node = cur_node.node[node_url]
        cur_node.route_list.append(route)

    def _search_node(self, url_path: str) -> RouteNode:
        cur_node = self.root_node
        for url_node in url_path.strip().split("/"):
            if url_node in cur_node.node:
                cur_node = cur_node.node[url_node]
            else:
                break
        return cur_node

    def search_by_scope(self, url_path: str, scope: Scope) -> Optional[Route]:
        cur_node: "RouteNode" = self._search_node(url_path)
        route: Optional[Route] = None
        for route in cur_node.route_list:
            if route.path == url_path:
                break
            match, child_scope = route.matches(scope)
            if match == Match.FULL:
                break

        return route

    def search(self, url_path: str) -> Optional[List[Route]]:
        cur_node: "RouteNode" = self._search_node(url_path)
        if cur_node.route_list:
            return cur_node.route_list
        return None
