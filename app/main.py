import uvicorn
from fastapi import FastAPI

app = FastAPI()

def start():
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
