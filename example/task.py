import time
from fastapi import FastAPI
from fastapi_tools.task import background_task
from fastapi_tools.task import stop_task

app: 'FastAPI' = FastAPI()


@app.on_event("startup")
@background_task(seconds=10)
def test_task() -> None:
    print(f'test.....{int(time.time())}')


app.on_event("shutdown")(stop_task)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app)
