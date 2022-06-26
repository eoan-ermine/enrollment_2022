from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator
from pydantic.json import ENCODERS_BY_TYPE

from analyzer.utils.misc import nameddict

if TYPE_CHECKING:
    from analyzer.db import schema


# Поправляем форматирование дат на форматирование, требуемое спецификацией
ENCODERS_BY_TYPE[datetime] = lambda d: "%04d" % d.year + d.strftime("-%m-%dT%H:%M:%S.000Z")


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
    def from_model(model: schema.ShopUnit):
        return ShopUnit(
            id=UUID(model.id),
            name=model.name,
            date=model.last_update,
            parentId=UUID(model.parent_id) if model.parent_id else None,
            type=ShopUnitType.CATEGORY if model.is_category else ShopUnitType.OFFER,
            price=model.price,
            children=[ShopUnit.from_model(child) for child in model.children] if model.is_category else None,
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

    def to_database_row(self, last_update: datetime) -> nameddict:
        return nameddict(
            id=str(self.id),
            name=self.name,
            parent_id=str(self.parentId) if self.parentId else None,
            is_category=self.type == ShopUnitType.CATEGORY,
            price=self.price,
            last_update=last_update,
        )

    @validator("price")
    def category_price_null(cls, v, values, **kwargs):
        # Поле type могло не пройти валидацию, поэтому мы проверяем, есть ли оно в values
        if "type" in values and values["type"] == ShopUnitType.CATEGORY:
            if v is not None:
                raise ValueError("Price of category must be None")
        return v


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

    @staticmethod
    def from_model(model: schema.ShopUnit):
        return ShopUnit(
            id=UUID(model.id),
            name=model.name,
            date=model.date,
            parentId=UUID(model.parent_id) if model.parent_id else None,
            type=ShopUnitType.CATEGORY if model.is_category else ShopUnitType.OFFER,
            price=model.price,
        )


class ShopUnitStatisticResponse(BaseModel):
    items: Optional[List[ShopUnitStatisticUnit]] = Field(None, description="История в произвольном порядке.")


class Error(BaseModel):
    code: int
    message: str


class ShopUnitStatisticRequest(BaseModel):
    id: UUID
    date_start: datetime
    date_end: datetime

    @validator("date_end")
    def validate_range(cls, value, values, **kwargs):
        # date_start точно прошло валидацию, т.к. изначально прошло валидацию в обработчике эндпоинта
        # date_start не должно быть больше или равно date_end, так как интервал определен как [date_start; date_end)

        if values["date_start"] >= value:
            raise ValueError(
                f"{values['date_start']} and {value} must define valid half-opened interval [date_start; date_end)"
            )
        return value
