from __future__ import annotations

from datetime import datetime
from typing import Union

from fastapi import Depends
from sqlalchemy.orm import Session

from analyzer.api.schema import Error, ShopUnitStatisticResponse, ShopUnitStatisticUnit
from analyzer.utils.database import get_dal, get_session

from . import router


@router.get("/sales", response_model=ShopUnitStatisticResponse, responses={"400": {"model": Error}})
async def get_sales(date: datetime, session: Session = Depends(get_session)) -> Union[ShopUnitStatisticResponse, Error]:
    async with get_dal(session) as dal:
        units = await dal.get_sales(date)
    return ShopUnitStatisticResponse(items=[ShopUnitStatisticUnit.from_model(unit) for unit in units])
