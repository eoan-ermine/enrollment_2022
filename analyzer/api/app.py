from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Union
from uuid import UUID

import typer
import uvicorn
from fastapi import Depends, FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from analyzer.db import schema
from analyzer.db.core import SessionLocal, sync_engine
from analyzer.db.dal import DAL

from .schema import (
    Error,
    ShopUnit,
    ShopUnitImportRequest,
    ShopUnitStatisticResponse,
    ShopUnitStatisticUnit,
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


async def get_session():
    async with SessionLocal() as session:
        yield session


@asynccontextmanager
async def get_dal(session):
    client = DAL(session)
    try:
        await session.begin()
        yield client
    finally:
        await session.commit()


@app.delete(
    "/delete/{id}",
    response_model=None,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
async def delete_unit(id: UUID, session: Session = Depends(get_session)) -> Union[None, Error]:
    ident = str(id)

    async with get_dal(session) as dal:
        parents = await dal.get_parents_ids([ident])
        await dal.delete_unit(ident)
        await dal.update_categories(parents)


@app.post("/imports", response_model=None, status_code=200, responses={"400": {"model": Error}})
async def import_units(body: ShopUnitImportRequest, session: Session = Depends(get_session)) -> Union[None, Error]:
    last_update = body.updateDate
    contains_unit_with_parent = False
    offers_ids = []

    units = []
    for item in body.items:
        unit = schema.ShopUnit.from_model(item, last_update=last_update)
        if unit.parent_id:
            contains_unit_with_parent = True
        if not unit.is_category:
            offers_ids.append(unit.id)
        units.append(unit)

    async with get_dal(session) as dal:
        await dal.add_units(units, last_update)

    # Следующий код должен выполняться лишь после обработки триггеров на вставку ShopUnit
    if contains_unit_with_parent:
        async with get_dal(session) as dal:
            parents = await dal.get_parents_ids(offers_ids)
            await dal.update_categories(parents, last_update)


@app.get(
    "/node/{id}/statistic",
    response_model=ShopUnitStatisticResponse,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
async def get_node_statistic(
    id: UUID,
    date_start: Optional[datetime] = Query(default=datetime.min, alias="dateStart"),
    date_end: Optional[datetime] = Query(default=datetime.max, alias="dateEnd"),
    session=Depends(get_session),
) -> Union[ShopUnitStatisticResponse, Error]:
    async with get_dal(session) as dal:
        statistic_units = await dal.get_node_statistic(str(id), date_start, date_end)
    return ShopUnitStatisticResponse(items=[ShopUnitStatisticUnit.from_model(unit) for unit in statistic_units])


@app.get(
    "/nodes/{id}",
    response_model=ShopUnit,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
async def get_node(id: UUID, session=Depends(get_session)) -> Union[ShopUnit, Error]:
    async with get_dal(session) as dal:
        unit = await dal.get_node(str(id))
    return ShopUnit.from_model(unit)


@app.get(
    "/sales",
    response_model=ShopUnitStatisticResponse,
    responses={"400": {"model": Error}},
)
async def get_sales(date: datetime, session: Session = Depends(get_session)) -> Union[ShopUnitStatisticResponse, Error]:
    async with get_dal(session) as dal:
        units = await dal.get_sales(date)
    return ShopUnitStatisticResponse(items=[ShopUnitStatisticUnit.from_model(unit) for unit in units])


def main(host: str = "127.0.0.1", port: int = 80, debug: bool = False):
    uvicorn.run("analyzer.api.app:app", host=host, port=port, reload=debug)
    with sync_engine.connect() as connection:
        connection.execute("pragma vacuum")
        connection.execute("pragma optimize")


def start():
    typer.run(main)
