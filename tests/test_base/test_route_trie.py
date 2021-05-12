from typing import List, Optional

from starlette.routing import Route

from example.route_trie import root, route_trie


class TestRouteTrie:
    def test(self) -> None:
        route_list: Optional[List[Route]] = route_trie.search("/")
        assert route_list
        assert route_list[0].endpoint == root
        assert not route_trie.search("/not_found")
        assert not route_trie.search_by_scope("/not_found", {})
