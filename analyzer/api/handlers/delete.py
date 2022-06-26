from __future__ import annotations

from typing import Union
from uuid import UUID

from fastapi import Depends
from sqlalchemy.orm import Session

from analyzer.api.schema import Error
from analyzer.db.dal import apply_updates, get_dal
from analyzer.utils.database import get_session

from . import router


@router.delete("/delete/{id}", response_model=None, responses={"400": {"model": Error}, "404": {"model": Error}})
async def delete_unit(id: UUID, session: Session = Depends(get_session)) -> Union[None, Error]:
    async with get_dal(session) as dal:
        unit_updates, hierarchy_updates = await dal.delete_unit(str(id))
    await apply_updates(session, unit_updates, hierarchy_updates)
