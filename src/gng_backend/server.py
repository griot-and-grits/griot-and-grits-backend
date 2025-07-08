from fastapi import FastAPI


app = FastAPI(title="Griot and Grits API", description="Griot and Grits API")


@app.get("/")
def read_root():
    return {"message": "Hello World"}
