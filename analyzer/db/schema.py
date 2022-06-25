from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import backref, relationship
from sqlalchemy.types import TIMESTAMP, Boolean, Integer, String

from analyzer.api import schema

from .core import Base


class ShopUnit(Base):
    __tablename__ = "shop_units"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(String, index=True)

    price = Column(Integer)
    is_category = Column(Boolean)

    last_update = Column(type_=TIMESTAMP(timezone=True))

    @staticmethod
    def from_model(model: schema.ShopUnit, last_update: int):
        return ShopUnit(
            id=str(model.id),
            name=model.name,
            parent_id=str(model.parentId) if model.parentId else None,
            price=model.price,
            is_category=model.type == schema.ShopUnitType.CATEGORY,
            last_update=last_update,
        )


class PriceUpdate(Base):
    __tablename__ = "price_updates"

    id = Column(Integer, primary_key=True, index=True)

    unit_id = Column(String, ForeignKey("shop_units.id", ondelete="CASCADE"), index=True)
    unit = relationship("ShopUnit", backref=backref("price_updates", passive_deletes=True))

    price = Column(Integer)
    date = Column(type_=TIMESTAMP(timezone=True))


class UnitHierarchy(Base):
    __tablename__ = "units_hierarchy"

    parent_id = Column(String, primary_key=True, index=True, nullable=False)
    id = Column(String, primary_key=True, index=True, nullable=False)


class CategoryInfo(Base):
    __tablename__ = "category_info"

    id = Column(String, ForeignKey("shop_units.id", ondelete="CASCADE"), primary_key=True, index=True, nullable=False)
    id_rel = relationship("ShopUnit", passive_deletes=True)

    sum = Column(Integer, nullable=False)
    count = Column(Integer, nullable=False)
