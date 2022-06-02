
from __future__ import annotations

from datetime import datetime
from typing import Optional, Union
from uuid import UUID

import uvicorn
from fastapi import FastAPI, Query

from .models import Error, ShopUnit, ShopUnitImportRequest, ShopUnitStatisticResponse

app = FastAPI(
    description='Вступительное задание в Летнюю Школу Бэкенд Разработки Яндекса 2022',
    title='Mega Market Open API',
    version='1.0',
)


@app.delete(
    '/delete/{id}',
    response_model=None,
    responses={'400': {'model': Error}, '404': {'model': Error}},
)
def delete_delete_id(id: UUID) -> Union[None, Error]:
    pass


@app.post('/imports', response_model=None, responses={'400': {'model': Error}})
def post_imports(body: ShopUnitImportRequest = None) -> Union[None, Error]:
    pass


@app.get(
    '/node/{id}/statistic',
    response_model=ShopUnitStatisticResponse,
    responses={'400': {'model': Error}, '404': {'model': Error}},
)
def get_node_id_statistic(
    id: UUID,
    date_start: Optional[datetime] = Query(None, alias='dateStart'),
    date_end: Optional[datetime] = Query(None, alias='dateEnd'),
) -> Union[ShopUnitStatisticResponse, Error]:
    pass


@app.get(
    '/nodes/{id}',
    response_model=ShopUnit,
    responses={'400': {'model': Error}, '404': {'model': Error}},
)
def get_nodes_id(id: UUID) -> Union[ShopUnit, Error]:
    pass


@app.get(
    '/sales',
    response_model=ShopUnitStatisticResponse,
    responses={'400': {'model': Error}},
)
def get_sales(date: datetime) -> Union[ShopUnitStatisticResponse, Error]:
    pass


def start():
    uvicorn.run("app.main:app", host="127.0.0.1", port=8080, reload=True)
