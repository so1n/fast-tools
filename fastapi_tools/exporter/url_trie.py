from typing import Dict, List, Tuple, Union

from starlette.routing import Match, Route
from starlette.types import Scope


class UrlTrie:

    def __init__(self):
        self.root: Dict[str, Union['UrlTrie', dict, bool, List[Route]]] = {}
        self.end_flag: str = 'UrlTrie:end_flag'
        self.regex_flag: str = 'UrlTrie:regex_flag'
        self.route_dict: Dict['UrlTrie', List[Route]] = {}

    def insert(self, url_path: str, route: Route):
        cur_node = self.root
        if url_path == '/':
            cur_node['/'] = {}
            cur_node = cur_node['/']
        else:
            for url_node in url_path.split('/'):
                if not url_node:
                    continue
                elif '{' == url_node[0] and '}' == url_node[-1]:
                    if self.regex_flag not in cur_node:
                        cur_node[self.regex_flag] = []
                    cur_node[self.regex_flag].append(route)
                    break
                elif url_node not in cur_node:
                    cur_node[url_node] = {}
                cur_node = cur_node[url_node]
        cur_node[self.end_flag] = True

    def search(self, url_path: str, scope: Scope) -> Tuple[bool, str]:
        cur_node = self.root
        if url_path not in cur_node:
            for url_node in url_path.split('/'):
                if not url_node:
                    continue
                if url_node in cur_node:
                    cur_node = cur_node[url_node]
                elif self.regex_flag in cur_node:
                    for route in cur_node[self.regex_flag]:
                        match, child_scope = route.matches(scope)
                        if match == Match.FULL:
                            return True, route.path
                    return False, url_path
                else:
                    break
        else:
            cur_node = cur_node[url_path]
        if self.end_flag in cur_node:
            return True, url_path
        else:
            return False, url_path
