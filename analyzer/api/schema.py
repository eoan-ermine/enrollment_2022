from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


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
