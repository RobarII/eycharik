"""One place where application errors become HTTP answers.

A use case raises a domain-shaped exception; only this module knows status codes. That keeps
``HTTPException`` out of the application layer and keeps the mapping consistent across routes.

Every answer carries three things: the human ``detail`` the cabinet already prints, a stable
machine ``code`` an integration can branch on, and the ``request_id`` the same request logged.
The code is part of the contract (``docs/contracts/admin-api.md``); the sentence is not.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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

# Status to the generic code. A handler may name something more precise; a status without an entry
# answers ``error`` so a new status code is never silently mistaken for a known one.
CODE_BY_STATUS: dict[int, str] = {
    status.HTTP_400_BAD_REQUEST: "bad_request",
    status.HTTP_401_UNAUTHORIZED: "unauthorized",
    status.HTTP_403_FORBIDDEN: "forbidden",
    status.HTTP_404_NOT_FOUND: "not_found",
    status.HTTP_405_METHOD_NOT_ALLOWED: "method_not_allowed",
    status.HTTP_409_CONFLICT: "conflict",
    status.HTTP_413_CONTENT_TOO_LARGE: "payload_too_large",
    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: "unsupported_media_type",
    status.HTTP_422_UNPROCESSABLE_ENTITY: "unprocessable",
    status.HTTP_429_TOO_MANY_REQUESTS: "rate_limited",
    status.HTTP_500_INTERNAL_SERVER_ERROR: "internal",
    status.HTTP_503_SERVICE_UNAVAILABLE: "unavailable",
}

REQUEST_ID_HEADER = "X-Request-ID"


def install(app: FastAPI) -> None:
    app.add_exception_handler(KnowledgeRejectedError, _knowledge)
    app.add_exception_handler(InboundError, _inbound)
    app.add_exception_handler(
        QuestionNotFoundError, _fixed("question_not_found", 404, "question not found")
    )
    app.add_exception_handler(
        QuestionAlreadyResolvedError,
        _fixed("question_already_resolved", 409, "question already resolved"),
    )
    app.add_exception_handler(
        UnknownAssigneeError, _fixed("unknown_assignee", 422, "assignee is not an admin")
    )
    app.add_exception_handler(
        EmployeeNotFoundError, _fixed("employee_not_found", 404, "employee not found")
    )
    # The framework's own failures answer in the same shape, so a client never has two parsers.
    app.add_exception_handler(StarletteHTTPException, _http)
    app.add_exception_handler(RequestValidationError, _validation)
    app.add_exception_handler(Exception, _internal)


async def _knowledge(_: Request, error: Exception) -> JSONResponse:
    if isinstance(error, UploadTooLargeError):
        code, status_code = "upload_too_large", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
    elif isinstance(error, UnsupportedMediaError):
        code, status_code = "unsupported_media_type", status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    else:
        code, status_code = "knowledge_rejected", status.HTTP_422_UNPROCESSABLE_ENTITY
    return _answer(_, status_code, code, str(error))


async def _inbound(_: Request, error: Exception) -> JSONResponse:
    if isinstance(error, BadSecretError):
        code, status_code = "bad_webhook_secret", status.HTTP_401_UNAUTHORIZED
    elif isinstance(error, UnknownChannelError):
        code, status_code = "unknown_channel", status.HTTP_404_NOT_FOUND
    elif isinstance(error, ChannelUnavailableError):
        code, status_code = "channel_unavailable", status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(error, InvalidBodyError):
        code, status_code = "invalid_body", status.HTTP_400_BAD_REQUEST
    else:
        code, status_code = "inbound_error", status.HTTP_400_BAD_REQUEST
    return _answer(_, status_code, code, str(error))


async def _http(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, StarletteHTTPException)
    raw: Any = error.detail
    code = CODE_BY_STATUS.get(error.status_code, "error")
    detail = raw if isinstance(raw, str) else code
    # A route may name a more precise code without owning a status-code table: it raises
    # ``HTTPException(401, detail={"code": ..., "message": ...})``.
    if isinstance(raw, dict):
        named = raw.get("code")
        if isinstance(named, str) and named:
            code = named
            message = raw.get("message")
            detail = message if isinstance(message, str) else named
    response = _answer(request, error.status_code, code, detail)
    for name, value in (error.headers or {}).items():
        response.headers[name] = value
    return response


async def _validation(request: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    problems: list[dict[str, Any]] = [
        {
            "loc": [str(part) for part in item.get("loc", ())],
            "message": str(item.get("msg", "")),
            "type": str(item.get("type", "")),
        }
        for item in error.errors()
    ]
    first: dict[str, Any] = (
        problems[0] if problems else {"loc": [], "message": "invalid request", "type": ""}
    )
    message = first.get("message")
    text = message if isinstance(message, str) and message else "invalid request"
    where = ".".join(str(part) for part in first.get("loc", ()))
    detail = f"{where}: {text}" if where else text
    return _answer(
        request,
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        "validation_failed",
        detail,
        extra={"errors": problems},
    )


async def _internal(request: Request, error: Exception) -> JSONResponse:
    """A crash answers with a code and a request id, never with the exception's text.

    The text may hold a token, a DSN, or a row. The log holds it; the client gets the id that finds
    the log line.
    """
    del error
    return _answer(
        request, status.HTTP_500_INTERNAL_SERVER_ERROR, "internal", "internal server error"
    )


def _answer(
    request: Request,
    status_code: int,
    code: str,
    detail: str,
    *,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "detail": detail,
        "code": code,
        "request_id": _request_id(request),
    }
    if extra:
        body.update(extra)
    response = JSONResponse(body, status_code=status_code)
    request_id = _request_id(request)
    if request_id is not None:
        response.headers[REQUEST_ID_HEADER] = request_id
    return response


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else None


def _fixed(
    code: str, status_code: int, detail: str
) -> Callable[[Request, Exception], Awaitable[JSONResponse]]:
    """A handler with a fixed sentence: an internal exception message never reaches a client."""

    async def handler(_: Request, __: Exception) -> JSONResponse:
        return _answer(_, status_code, code, detail)

    return handler
