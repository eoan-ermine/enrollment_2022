from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, TypeVar

if TYPE_CHECKING:
    from analyzer.db.core import Base


def model_to_dict(model: Base) -> Dict:
    result = dict(model.__dict__)
    result.pop("_sa_instance_state", None)
    return result


T = TypeVar("T")


def flatten(xss: List[List[T]]) -> List[T]:
    return [x for xs in xss for x in xs]


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text
