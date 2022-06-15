from enum import Enum

from sqlalchemy import and_


class IntervalType(Enum):
    OPENED = lambda x, start, end: and_(x > start, x < end)
    CLOSED = lambda x, start, end: and_(x >= start, x <= end)
