from __future__ import annotations

from datetime import datetime
from typing import Optional, Union
from uuid import UUID

import typer
import uvicorn
from fastapi import Depends, FastAPI, Query
from sqlalchemy.orm import Session

from analyzer.db import schema
from analyzer.utils.database import get_dal, get_session

from .middleware import add_exception_handling
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
add_exception_handling(app)


@app.delete(
    "/delete/{id}",
    response_model=None,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
async def delete_unit(id: UUID, session: Session = Depends(get_session)) -> Union[None, Error]:
    async with get_dal(session) as dal:
        await dal.delete_unit(str(id))


@app.post("/imports", response_model=None, status_code=200, responses={"400": {"model": Error}})
async def import_units(body: ShopUnitImportRequest, session: Session = Depends(get_session)) -> Union[None, Error]:
    last_update = body.updateDate

    updates = []
    async with get_dal(session) as dal:
        updates = await dal.add_units(
            [schema.ShopUnit.from_model(item, last_update=last_update) for item in body.items], last_update
        )

    # Апдейты должны выполняться после строго после создания всех юнитов и иерархии
    async with get_dal(session) as dal:
        await dal.apply_updates(updates, last_update)


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


def start():
    typer.run(main)
