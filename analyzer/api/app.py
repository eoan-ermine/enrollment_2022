from __future__ import annotations

import typer
import uvicorn
from fastapi import FastAPI

from .handlers import router
from .middleware import add_exception_handling

app = FastAPI(
    description="Вступительное задание в Летнюю Школу Бэкенд Разработки Яндекса 2022",
    title="Mega Market Open API",
    version="1.0",
)
add_exception_handling(app)
app.include_router(router)


def main(host: str = "127.0.0.1", port: int = 80, debug: bool = False) -> None:
    uvicorn.run("analyzer.api.app:app", host=host, port=port, reload=debug)


def start() -> None:
    typer.run(main)
