from typing import Optional

from fastapi import FastAPI
from fastapi_tools.statsd_middleware import StatsdClient, StatsdMiddleware
from fastapi_tools.route_trie import RouteTrie


app = FastAPI()
client = StatsdClient()
route_trie = RouteTrie()

app.add_middleware(
    StatsdMiddleware,
    client=client,
    route_trie=route_trie,
    url_replace_handle=lambda url: url.replace('/', '_')
)
app.on_event("shutdown")(client.close)


@app.on_event("startup")
async def startup_event():
    await client.connect()


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


# Note: The insert_by_app must be called after the all route added
route_trie.insert_by_app(app)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
