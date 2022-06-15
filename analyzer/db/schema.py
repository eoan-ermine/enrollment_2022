from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import backref, relationship
from sqlalchemy.types import Boolean, DateTime, Integer, String

from .core import Base


class ShopUnit(Base):
    __tablename__ = "shop_units"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

    parent_id = Column(Integer, ForeignKey("shop_units.id", ondelete="CASCADE"), index=True)
    parent = relationship(lambda: ShopUnit, remote_side=id, backref=backref("shop_units", passive_deletes=True))

    price = Column(Integer)
    is_category = Column(Boolean)

    last_update = Column(DateTime)


class PriceUpdate(Base):
    __tablename__ = "price_updates"

    id = Column(Integer, primary_key=True, index=True)

    unit_id = Column(Integer, ForeignKey("shop_units.id", ondelete="CASCADE"), index=True)
    unit = relationship("ShopUnit", backref=backref("price_updates", passive_deletes=True))

    price = Column(Integer)
    date = Column(DateTime)


class UnitHierarchy(Base):
    __tablename__ = "units_hierarchy"

    parent_id = Column(Integer, primary_key=True, index=True, nullable=False)
    id = Column(Integer, primary_key=True, index=True, nullable=False)
