from __future__ import annotations

from datetime import datetime
from typing import Generator, List, Union

from fastapi import Depends
from sqlalchemy.orm import Session

from analyzer.api.schema import Error, ShopUnitImport, ShopUnitImportRequest
from analyzer.db.dal import apply_updates
from analyzer.utils.database import get_dal, get_session
from analyzer.utils.misc import nameddict

from . import router


def make_units_table_rows(units: List[ShopUnitImport], last_update: datetime) -> Generator:
    for unit in units:
        yield nameddict(unit.to_database_row(last_update))


@router.post("/imports", response_model=None, status_code=200, responses={"400": {"model": Error}})
async def import_units(body: ShopUnitImportRequest, session: Session = Depends(get_session)) -> Union[None, Error]:
    last_update = body.updateDate

    async with get_dal(session) as dal:
        unit_updates, hierarchy_updates = await dal.add_units(
            make_units_table_rows(body.items, last_update), last_update
        )

    # Апдейты должны выполняться после строго после создания всех юнитов
    await apply_updates(session, unit_updates, hierarchy_updates, last_update)
