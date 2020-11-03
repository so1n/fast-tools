from typing import List, Optional
from fastapi import FastAPI
from starlette.routing import Route
from fast_tools.base import RouteTrie

app: "FastAPI" = FastAPI()


@app.get("/")
async def root() -> dict:
    return {"Hello": "World"}


@app.get("/api/users/login")
async def user_login() -> str:
    return "ok"


route_trie: RouteTrie = RouteTrie()
route_trie.insert_by_app(app)


def print_route(route_list: Optional[List[Route]]):
    if route_list:
        for route in route_list:
            print(f"route:{route} url:{route.path}")
    else:
        print(f"route:{route_list} url: not found")


# regex url should use scope param, can learn more in exporter example
print_route(route_trie.search("/"))
print_route(route_trie.search("/api/users/login"))
