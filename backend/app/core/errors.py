from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.request_context import get_request_id


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        status_code: int = 400,
    ):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        super().__init__(message)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        request_id = get_request_id(request)

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "request_id": request_id,
                    "retryable": exc.retryable,
                }
            },
        )
