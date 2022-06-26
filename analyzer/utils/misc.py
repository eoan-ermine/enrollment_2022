from __future__ import annotations

from typing import List, TypeVar

T = TypeVar("T")


def flatten(xss: List[List[T]]) -> List[T]:
    return [x for xs in xss for x in xs]


def remove_prefix(text, prefix):
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


# Класс-обертка, устраняющий необходимость в изменении кода, опирающегося на обращение к аттрибутам
class nameddict(dict):
    __getattr__ = dict.__getitem__
