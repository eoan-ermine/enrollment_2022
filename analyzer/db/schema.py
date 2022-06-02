from sqlalchemy import MetaData, Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declared_attr

from .core import Base


class ShopUnit(object):
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    
    @declared_attr
    def parent(cls):
        return Column(Integer, ForeignKey("categories.id"), nullable=True)


class Category(Base, ShopUnit):
    __tablename__ = "categories"


class Item(Base, ShopUnit):
    __tablename__ = "items"

    price = Column(Integer)
