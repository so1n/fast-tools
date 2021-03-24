import time

from fastapi import FastAPI

from fast_tools.task import background_task, stop_task

app: "FastAPI" = FastAPI()


@app.on_event("startup")
@background_task(seconds=10, max_retry=3)
def test_task() -> None:
    print(f"test.....{int(time.time())}")


app.on_event("shutdown")(stop_task)


if __name__ == "__main__":
    import uvicorn  # type: ignore

    uvicorn.run(app)
