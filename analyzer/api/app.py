from __future__ import annotations

from datetime import datetime
from typing import Optional, Union
from uuid import UUID

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm.exc import NoResultFound

from analyzer.db import schema
from analyzer.db.core import SessionLocal
from analyzer.db.crud import ShopUnitCRUD

from .schema import (
    Error,
    ShopUnit,
    ShopUnitImportRequest,
    ShopUnitStatisticResponse,
    ShopUnitType,
)

app = FastAPI(
    description="Вступительное задание в Летнюю Школу Бэкенд Разработки Яндекса 2022",
    title="Mega Market Open API",
    version="1.0",
)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content=jsonable_encoder(Error(code=400, message="Validation Failed")))


@app.exception_handler(NoResultFound)
def not_found_exception_handler(_: Request, _1: NoResultFound):
    return JSONResponse(status_code=404, content=jsonable_encoder(Error(code=404, message="Item not found")))


@app.delete(
    "/delete/{id}",
    response_model=None,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
def delete_delete_id(id: UUID) -> Union[None, Error]:
    with SessionLocal.begin() as session:
        session.query(schema.ShopUnit).filter(schema.ShopUnit.id == str(id)).delete(synchronize_session=False)


@app.post("/imports", response_model=None, status_code=200, responses={"400": {"model": Error}})
def post_imports(body: ShopUnitImportRequest) -> Union[None, Error]:
    updateDate = body.updateDate

    with SessionLocal.begin() as session:
        for unit in body.items:
            unit_id = str(unit.id)
            parent = str(unit.parentId) if unit.parentId else None

            unit = schema.ShopUnit(
                id=unit_id,
                name=unit.name,
                parent_id=parent,
                price=unit.price if unit.price else 0,
                is_category=unit.type == ShopUnitType.CATEGORY,
                last_update=updateDate,
            )
            session.merge(unit)

            price_update = schema.PriceUpdate(unit_id=unit_id, price=unit.price, date=updateDate)
            session.add(price_update)

    with SessionLocal.begin() as session:
        hierarchy_data = (
            session.query(schema.UnitHierarchy)
            .filter(schema.UnitHierarchy.id.in_([str(unit.id) for unit in body.items]))
            .all()
        )
        ShopUnitCRUD.update_prices(session, [unit.parent_id for unit in hierarchy_data])


@app.get(
    "/node/{id}/statistic",
    response_model=ShopUnitStatisticResponse,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
def get_node_id_statistic(
    id: UUID,
    date_start: Optional[datetime] = Query(None, alias="dateStart"),
    date_end: Optional[datetime] = Query(None, alias="dateEnd"),
) -> Union[ShopUnitStatisticResponse, Error]:
    pass


@app.get(
    "/nodes/{id}",
    response_model=ShopUnit,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
def get_nodes_id(id: UUID) -> Union[ShopUnit, Error]:
    with SessionLocal() as session:
        item = ShopUnitCRUD.get_item(session, str(id))

    return ShopUnit.from_model(item)


@app.get(
    "/sales",
    response_model=ShopUnitStatisticResponse,
    responses={"400": {"model": Error}},
)
def get_sales(date: datetime) -> Union[ShopUnitStatisticResponse, Error]:
    pass


def start():
    uvicorn.run("analyzer.api.app:app", host="127.0.0.1", port=8080, reload=True)
