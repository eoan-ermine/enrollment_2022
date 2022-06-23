from typing import Dict, List, TypeVar

from analyzer.db.core import Base


def model_to_dict(model: Base) -> Dict:
    result = dict(model.__dict__)
    result.pop("_sa_instance_state", None)
    return result


T = TypeVar("T")


def flatten(xss: List[List[T]]) -> List[T]:
    return [x for xs in xss for x in xs]
