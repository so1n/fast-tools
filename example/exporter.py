from fastapi import FastAPI
from fastapi_tools.exporter import PrometheusMiddleware, get_metrics

app = FastAPI()
app.add_route("/metrics", get_metrics)


@app.get("/")
async def root():
    return {"Hello": "World"}


# Note: The middleware must be added after the route
app.add_middleware(
    PrometheusMiddleware,
    block_url_set={"/metrics"}
)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
