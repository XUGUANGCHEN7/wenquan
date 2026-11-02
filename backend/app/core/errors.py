import re
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(request: Request, status: int, code: str, message: str) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message, "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


def install_error_handling(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        candidate = request.headers.get("X-Request-ID", "")
        request.state.request_id = candidate if _REQUEST_ID.fullmatch(candidate) else uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError):
        return error_response(request, exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return error_response(request, 422, "VALIDATION_ERROR", "Request parameters are invalid")

    @app.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        codes = {401: "AUTH_REQUIRED", 403: "RESOURCE_FORBIDDEN", 404: "NOT_FOUND"}
        return error_response(request, exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail))
