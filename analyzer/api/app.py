from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Union
from uuid import UUID

import typer
import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import delete
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound

from analyzer.db import schema
from analyzer.db.core import SessionLocal, sync_engine
from analyzer.db.crud import ShopUnitCRUD
from analyzer.db.utils import IntervalType, model_to_dict

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
async def delete_delete_id(id: UUID) -> Union[None, Error]:
    ident = str(id)

    async with SessionLocal.begin() as session:
        parents = await ShopUnitCRUD.get_parents_ids(session, [ident])
        rows_deleted = await session.execute(
            delete(schema.ShopUnit).where(schema.ShopUnit.id == ident).execution_options(synchronize_session=False)
        )

        if rows_deleted == 0:
            raise NoResultFound()

        await ShopUnitCRUD.update_categories(session, parents)


@app.post("/imports", response_model=None, status_code=200, responses={"400": {"model": Error}})
async def post_imports(body: ShopUnitImportRequest) -> Union[None, Error]:
    updateDate = body.updateDate

    contains_unit_with_parent = False
    offers_ids = []

    async with SessionLocal.begin() as session:
        for unit in body.items:
            unit_id = str(unit.id)

            parent = str(unit.parentId) if unit.parentId else None
            if parent:
                contains_unit_with_parent = True

            unit = schema.ShopUnit(
                id=unit_id,
                name=unit.name,
                parent_id=parent,
                price=unit.price if unit.price else 0,
                is_category=unit.type == ShopUnitType.CATEGORY,
                last_update=updateDate,
            )
            await session.merge(unit)

            if not unit.is_category:
                offers_ids.append(unit_id)
                price_update = schema.PriceUpdate(unit_id=unit_id, price=unit.price, date=updateDate)
                session.add(price_update)

    # Следующий код должен выполняться лишь после обработки триггеров на вставку ShopUnit
    if contains_unit_with_parent:
        async with SessionLocal.begin() as session:
            parents = await ShopUnitCRUD.get_parents_ids(session, offers_ids)
            await ShopUnitCRUD.update_categories(session, parents, updateDate)


@app.get(
    "/node/{id}/statistic",
    response_model=ShopUnitStatisticResponse,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
async def get_node_id_statistic(
    id: UUID,
    date_start: Optional[datetime] = Query(default=datetime.min, alias="dateStart"),
    date_end: Optional[datetime] = Query(default=datetime.max, alias="dateEnd"),
) -> Union[ShopUnitStatisticResponse, Error]:
    ident = str(id)

    async with SessionLocal() as session:
        q = await session.execute(select(schema.ShopUnit).where(schema.ShopUnit.id == ident))
        unit = q.scalars().one()

        q = await session.execute(
            select(schema.PriceUpdate.price, schema.PriceUpdate.date)
            .where(schema.PriceUpdate.unit_id == ident)
            .where(IntervalType.OPENED(schema.PriceUpdate.date, date_start, date_end))
        )
        updates = q.all()

        return ShopUnitStatisticResponse(
            items=[
                ShopUnit.from_model(
                    schema.ShopUnit(**{**model_to_dict(unit), "price": price, "last_update": date}), null_price=False
                )
                for price, date in updates
            ]
        )


@app.get(
    "/nodes/{id}",
    response_model=ShopUnit,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
async def get_nodes_id(id: UUID) -> Union[ShopUnit, Error]:
    async with SessionLocal() as session:
        item = await ShopUnitCRUD.get_item(session, str(id))

    return ShopUnit.from_model(item)


@app.get(
    "/sales",
    response_model=ShopUnitStatisticResponse,
    responses={"400": {"model": Error}},
)
async def get_sales(date: datetime) -> Union[ShopUnitStatisticResponse, Error]:
    async with SessionLocal() as session:
        q = await session.scalars(
            select(schema.ShopUnit)
            .select_from(schema.ShopUnit)
            .where(schema.ShopUnit.is_category == False)
            .where(IntervalType.CLOSED(schema.PriceUpdate.date, date - timedelta(days=1), date))
            .join(schema.PriceUpdate, schema.ShopUnit.id == schema.PriceUpdate.unit_id)
        )
        return ShopUnitStatisticResponse(items=[ShopUnit.from_model(unit) for unit in q.all()])


def main(host: str = "127.0.0.1", port: int = 80, debug: bool = False):
    uvicorn.run("analyzer.api.app:app", host=host, port=port, reload=debug)
    with sync_engine.connect() as connection:
        connection.execute("pragma vacuum")
        connection.execute("pragma optimize")


def start():
    typer.run(main)
