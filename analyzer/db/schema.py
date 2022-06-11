from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Boolean, DateTime, Integer, String

from .core import Base


class ShopUnit(Base):
    __tablename__ = "shop_units"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    parent = Column(Integer, ForeignKey("shop_units.id", ondelete="CASCADE"))
    price = Column(Integer)
    is_category = Column(Boolean)


class PriceUpdate(Base):
    __tablename__ = "price_updates"

    id = Column(Integer, primary_key=True, index=True)
    unit_id = Column(Integer, ForeignKey("price_updates.id", ondelete="CASCADE"))
    price = Column(Integer)
    date = Column(DateTime)
