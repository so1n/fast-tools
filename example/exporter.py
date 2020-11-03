from typing import Optional

from fastapi import FastAPI
from fast_tools.exporter import get_metrics, PrometheusMiddleware
from fast_tools.base import RouteTrie


app: "FastAPI" = FastAPI()
route_trie: "RouteTrie" = RouteTrie()

app.add_middleware(PrometheusMiddleware, route_trie=route_trie, block_url_set={"/metrics"})

app.add_route("/metrics", get_metrics)


@app.on_event("startup")
async def startup_event():
    route_trie.insert_by_app(app)


@app.get("/")
async def root():
    return {"Hello": "World"}


@app.get("/api/users/{user_id}/items/{item_id}")
async def read_user_item(user_id: int, item_id: str, q: Optional[str] = None, short: bool = False):
    """
    copy from:https://fastapi.tiangolo.com/tutorial/query-params/#multiple-path-and-query-parameters
    """
    item = {"item_id": item_id, "owner_id": user_id}
    if q:
        item.update({"q": q})
    if not short:
        item.update({"description": "This is an amazing item that has a long description"})
    return item


@app.get("/api/users/login")
async def user_login():
    return "ok"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
