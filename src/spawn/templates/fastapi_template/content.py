FASTAPI_MAIN_CONTENT = """\
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {{"message": "Hello from {project_name}!"}}
"""
