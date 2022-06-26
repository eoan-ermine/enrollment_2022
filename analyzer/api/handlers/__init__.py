import os
from importlib import import_module

from fastapi import APIRouter

router = APIRouter()


# Функция, устраняющая необходимость в ручном импорте функций всех эндпоинтов
def import_all_in_dir(path, pkg=__package__):
    for entry in os.scandir(path):
        if entry.is_dir():
            import_all_in_dir(os.path.join(path, entry.name), pkg=f"{pkg}.{entry.name}")
        ext = os.path.splitext(entry.name)
        if len(ext) < 2:
            # no extension, not importable, skip it
            continue
        *name, ext = ext
        name = "".join(name)
        if (
            entry.is_file() and ext == ".py" and "__init__" not in name
        ):  # skip __init__, because we are running in __init__
            import_module(f".{name}", package=pkg)


import_all_in_dir(os.path.dirname(__file__))
