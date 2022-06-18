from enum import Enum

from sqlalchemy import and_


class IntervalType(Enum):
    OPENED = lambda x, start, end: and_(x > start, x < end)
    CLOSED = lambda x, start, end: and_(x >= start, x <= end)


def model_to_dict(model):
    result = dict(model.__dict__)
    result.pop("_sa_instance_state", None)
    return result
