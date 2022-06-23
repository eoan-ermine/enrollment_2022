from typing import Union

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm.exc import NoResultFound

from analyzer.db.dal import ForbiddenOperation

from .schema import Error


def add_exception_handling(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    @app.exception_handler(RequestValidationError)
    @app.exception_handler(ForbiddenOperation)
    async def validation_exception_handler(
        _: Request, _1: Union[ValidationError, RequestValidationError, ForbiddenOperation]
    ):
        return JSONResponse(status_code=400, content=jsonable_encoder(Error(code=400, message="Validation Failed")))

    @app.exception_handler(NoResultFound)
    async def not_found_exception_handler(_: Request, _1: NoResultFound):
        return JSONResponse(status_code=404, content=jsonable_encoder(Error(code=404, message="Item not found")))
