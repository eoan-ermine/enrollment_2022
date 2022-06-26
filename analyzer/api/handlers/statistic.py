from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Union
from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from analyzer.api.schema import (
    Error,
    ShopUnitStatisticRequest,
    ShopUnitStatisticResponse,
    ShopUnitStatisticUnit,
)
from analyzer.db.dal import get_dal
from analyzer.utils.database import get_session

from . import router


@router.get(
    "/node/{id}/statistic",
    response_model=ShopUnitStatisticResponse,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
async def get_node_statistic(
    id: UUID,
    date_start: Optional[datetime] = Query(default=datetime.min.replace(tzinfo=timezone.utc), alias="dateStart"),
    date_end: Optional[datetime] = Query(default=datetime.max.replace(tzinfo=timezone.utc), alias="dateEnd"),
    session: Session = Depends(get_session),
) -> Union[ShopUnitStatisticResponse, Error]:
    ShopUnitStatisticRequest(id=id, date_start=date_start, date_end=date_end)  # Validate date range
    async with get_dal(session) as dal:
        statistic_units = await dal.get_node_statistic(str(id), date_start, date_end)
    return ShopUnitStatisticResponse(items=[ShopUnitStatisticUnit.from_model(unit) for unit in statistic_units])
