from typing import Optional

from fastapi import FastAPI
from fastapi_tools.route_trie import RouteTrie

app = FastAPI()


@app.get("/")
async def root():
    return {"Hello": "World"}


@app.get("/api/users/login")
async def user_login():
    return 'ok'


route_trie: RouteTrie = RouteTrie()
route_trie.insert_by_app(app)


def print_route(route_list):
    if route_list:
        for route in route_list:
            print(f'route:{route} url:{route.path}')
    else:
        print(f'route:{route_list} url: not found')


# regex url should use scope param, can learn more in exporter example
print_route(route_trie.search('/'))
print_route(route_trie.search('/api/users/login'))
