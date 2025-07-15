from fastapi import FastAPI
from .api import artifacts_router
from .factory import get_factory


app = FastAPI(title="Griot and Grits API", description="Griot and Grits API")
app.include_router(artifacts_router)


@app.get("/")
def read_root():
    return {"message": "Hello World"}
