from fastapi import FastAPI
from .api import routers
from .factory import get_factory


app = FastAPI(title="Griot and Grits API", description="Griot and Grits API")
# Include all routers
for router in routers:
    app.include_router(router)


@app.get("/")
def read_root():
    return {"message": "Hello World"}
