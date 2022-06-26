from __future__ import annotations

from typing import Union

from fastapi import Depends
from sqlalchemy.orm import Session

from analyzer.api.schema import Error, ShopUnitImportRequest
from analyzer.db.dal import apply_updates
from analyzer.db.schema import ShopUnit
from analyzer.utils.database import get_dal, get_session

from . import router


@router.post("/imports", response_model=None, status_code=200, responses={"400": {"model": Error}})
async def import_units(body: ShopUnitImportRequest, session: Session = Depends(get_session)) -> Union[None, Error]:
    last_update = body.updateDate

    async with get_dal(session) as dal:
        unit_updates, hierarchy_updates = await dal.add_units(
            [ShopUnit.from_model(item, last_update=last_update) for item in body.items], last_update
        )

    # Апдейты должны выполняться после строго после создания всех юнитов
    await apply_updates(session, unit_updates, hierarchy_updates, last_update)
