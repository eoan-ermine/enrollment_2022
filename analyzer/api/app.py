from __future__ import annotations

from datetime import datetime
from typing import Optional, Union
from uuid import UUID

import uvicorn
from fastapi import FastAPI, Request, Query
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .schema import Error, ShopUnit, ShopUnitType, ShopUnitImportRequest, ShopUnitStatisticResponse
from analyzer.db.schema import Base
from analyzer.db import schema
from analyzer.db.core import SessionLocal, engine

from sqlalchemy.dialects.sqlite import insert

app = FastAPI(
    description='Вступительное задание в Летнюю Школу Бэкенд Разработки Яндекса 2022',
    title='Mega Market Open API',
    version='1.0',
)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content=jsonable_encoder(Error(code=400, message="Validation Failed"))
    )


@app.delete(
    '/delete/{id}',
    response_model=None,
    responses={'400': {'model': Error}, '404': {'model': Error}},
)
def delete_delete_id(id: UUID) -> Union[None, Error]:
    pass


@app.post('/imports', response_model=None, status_code=200, responses={'400': {'model': Error}})
def post_imports(body: ShopUnitImportRequest) -> Union[None, Error]:
    updateDate = body.updateDate
    with SessionLocal.begin() as session:
        for unit in body.items:
            unit = schema.ShopUnit(
                id=str(unit.id), name=unit.name, parent=str(unit.parentId), price=unit.price, is_category=unit.type == ShopUnitType.CATEGORY
            )
            session.merge(unit)

            price_update = schema.PriceUpdate(
                unit_id=str(unit.id), price=unit.price, date=updateDate
            )
            session.add(price_update)


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
    uvicorn.run("analyzer.api.app:app", host="127.0.0.1", port=8080, reload=True)
