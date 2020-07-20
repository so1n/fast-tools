from typing import Optional

from fastapi import FastAPI
from fastapi_tools.route_trie import RouteTrie

app = FastAPI()


@app.get("/")
async def root():
    return {"Hello": "World"}


@app.get("/api/users/{user_id}/items/{item_id}")
async def read_user_item(
    user_id: int, item_id: str, q: Optional[str] = None, short: bool = False
):
    """
    copy from:https://fastapi.tiangolo.com/tutorial/query-params/#multiple-path-and-query-parameters
    """
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update(
            {"description": "This is an amazing item that has a long description"}
        )
    return item


@app.get("/api/users/login")
async def user_login():
    return 'ok'


route_trie: RouteTrie = RouteTrie()
route_trie.insert_by_app(app, block_url_set={'/'})


def print_route(route):
    if route:
        print(f'route:{route} url:{route.path}')
    else:
        print(f'route:{route} url: not found')


# regex url should use scope param, can learn more in exporter example
print_route(route_trie.search('/'))
print_route(route_trie.search('/api/users/login'))
