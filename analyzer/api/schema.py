from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from pydantic.json import ENCODERS_BY_TYPE

from analyzer.db import schema

# Format of datetimes in unit_tests
ENCODERS_BY_TYPE[datetime] = lambda d: "%04d" % d.year + d.strftime("-%m-%dT%H:%M:%SZ")


class ShopUnitType(Enum):
    OFFER = "OFFER"
    CATEGORY = "CATEGORY"


class ShopUnit(BaseModel):
    id: UUID = Field(
        ...,
        description="Уникальный идентфикатор",
        example="3fa85f64-5717-4562-b3fc-2c963f66a333",
    )
    name: str = Field(..., description="Имя категории")
    date: datetime = Field(
        ...,
        description="Время последнего обновления элемента",
        example="2022-05-28T21:12:01.516Z",
    )
    parentId: Optional[UUID] = Field(
        None,
        description="UUID родительской категории",
        example="3fa85f64-5717-4562-b3fc-2c963f66a333",
    )
    type: ShopUnitType
    price: Optional[int] = Field(
        None,
        description="Целое число, для категории - это средняя цена всех дочерних товаров(включая товары подкатегорий). Если цена является не целым числом, округляется в меньшую сторону до целого числа. Если категория не содержит товаров цена равна null.",
    )
    children: Optional[List[ShopUnit]] = Field(
        None,
        description="Список всех дочерних товаров\\категорий. Для товаров поле равно null.",
    )

    @staticmethod
    def from_model(model: schema.ShopUnit, null_price=True):
        children = getattr(model, "children", None)
        return ShopUnit(
            id=UUID(model.id),
            name=model.name,
            date=model.last_update,
            parentId=UUID(model.parent_id) if model.parent_id else None,
            type=ShopUnitType.CATEGORY if model.is_category else ShopUnitType.OFFER,
            price=None if not children and model.is_category and null_price else model.price,
            children=[ShopUnit.from_model(child) for child in children] if model.is_category and children else None,
        )


class ShopUnitImport(BaseModel):
    id: UUID = Field(
        ...,
        description="Уникальный идентфикатор",
        example="3fa85f64-5717-4562-b3fc-2c963f66a333",
    )
    name: str = Field(..., description="Имя элемента.")
    parentId: Optional[UUID] = Field(
        None,
        description="UUID родительской категории",
        example="3fa85f64-5717-4562-b3fc-2c963f66a333",
    )
    type: ShopUnitType
    price: Optional[int] = Field(None, description="Целое число, для категорий поле должно содержать null.")


class ShopUnitImportRequest(BaseModel):
    items: List[ShopUnitImport] = Field(None, description="Импортируемые элементы")
    updateDate: datetime = Field(
        None,
        description="Время обновления добавляемых товаров/категорий.",
        example="2022-05-28T21:12:01.516Z",
    )


class ShopUnitStatisticUnit(BaseModel):
    id: UUID = Field(
        ...,
        description="Уникальный идентфикатор",
        example="3fa85f64-5717-4562-b3fc-2c963f66a333",
    )
    name: str = Field(..., description="Имя элемента")
    parentId: Optional[UUID] = Field(
        None,
        description="UUID родительской категории",
        example="3fa85f64-5717-4562-b3fc-2c963f66a333",
    )
    type: ShopUnitType
    price: Optional[int] = Field(
        None,
        description="Целое число, для категории - это средняя цена всех дочерних товаров(включая товары подкатегорий). Если цена является не целым числом, округляется в меньшую сторону до целого числа. Если категория не содержит товаров цена равна null.",
    )
    date: datetime = Field(..., description="Время последнего обновления элемента.")


class ShopUnitStatisticResponse(BaseModel):
    items: Optional[List[ShopUnitStatisticUnit]] = Field(None, description="История в произвольном порядке.")


class Error(BaseModel):
    code: int
    message: str
