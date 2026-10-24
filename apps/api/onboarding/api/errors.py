"""One place where application errors become HTTP answers.

A use case raises a domain-shaped exception; only this module knows status codes. That keeps
``HTTPException`` out of the application layer and keeps the mapping consistent across routes.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from onboarding.app.admin.actions import (
    EmployeeNotFoundError,
    QuestionAlreadyResolvedError,
    QuestionNotFoundError,
    UnknownAssigneeError,
)
from onboarding.app.use_cases.inbound import (
    BadSecretError,
    ChannelUnavailableError,
    InboundError,
    InvalidBodyError,
    UnknownChannelError,
)
from onboarding.app.use_cases.knowledge import (
    KnowledgeRejectedError,
    UnsupportedMediaError,
    UploadTooLargeError,
)


def install(app: FastAPI) -> None:
    app.add_exception_handler(KnowledgeRejectedError, _knowledge)
    app.add_exception_handler(InboundError, _inbound)
    app.add_exception_handler(QuestionNotFoundError, _not_found("question not found"))
    app.add_exception_handler(
        QuestionAlreadyResolvedError, _conflict("question already resolved")
    )
    app.add_exception_handler(UnknownAssigneeError, _unprocessable("assignee is not an admin"))
    app.add_exception_handler(EmployeeNotFoundError, _not_found("employee not found"))


async def _knowledge(_: Request, error: Exception) -> JSONResponse:
    if isinstance(error, UploadTooLargeError):
        code = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif isinstance(error, UnsupportedMediaError):
        code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    else:
        code = status.HTTP_422_UNPROCESSABLE_ENTITY
    return JSONResponse({"detail": str(error)}, status_code=code)


async def _inbound(_: Request, error: Exception) -> JSONResponse:
    if isinstance(error, BadSecretError):
        code = status.HTTP_401_UNAUTHORIZED
    elif isinstance(error, UnknownChannelError):
        code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ChannelUnavailableError):
        code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, InvalidBodyError):
        code = status.HTTP_400_BAD_REQUEST
    else:
        code = status.HTTP_400_BAD_REQUEST
    return JSONResponse({"detail": str(error)}, status_code=code)


def _not_found(detail: str) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse({"detail": detail}, status_code=status.HTTP_404_NOT_FOUND)

    return handler


def _conflict(detail: str) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse({"detail": detail}, status_code=status.HTTP_409_CONFLICT)

    return handler


def _unprocessable(detail: str) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    async def handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            {"detail": detail}, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
        )

    return handler
