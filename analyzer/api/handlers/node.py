from __future__ import annotations

from typing import Union
from uuid import UUID

from fastapi import Depends

from analyzer.api.schema import Error, ShopUnit
from analyzer.utils.database import get_dal, get_session

from . import router


@router.get(
    "/nodes/{id}",
    response_model=ShopUnit,
    responses={"400": {"model": Error}, "404": {"model": Error}},
)
async def get_node(id: UUID, session=Depends(get_session)) -> Union[ShopUnit, Error]:
    async with get_dal(session) as dal:
        unit = await dal.get_node(str(id))
    return ShopUnit.from_model(unit)
