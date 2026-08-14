from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.core.rate_limit import limiter
from app.core.request_context import (
    get_client_ip,
    get_request_id,
    get_user_agent,
)
from app.services.audit import audit_service


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
    )

    install_exception_handlers(app)

    app.state.limiter = limiter

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next,
    ):
        request_id = get_request_id(request)

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(
        request: Request,
        exc: RateLimitExceeded,
    ) -> JSONResponse:
        request_id = get_request_id(request)
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        try:
            await audit_service.log_in_new_transaction(
                action="RATE_LIMITED",
                actor_user_id=None,
                resource_type="HTTP_ENDPOINT",
                resource_id=None,
                success=False,
                status_code=429,
                request_id=request_id,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata={
                    "method": request.method,
                    "path": request.url.path,
                },
            )
        except Exception:
            # Rate limiting itself must continue to work even if
            # audit persistence temporarily fails.
            pass

        return JSONResponse(
            status_code=429,
            headers={
                "Retry-After": "60",
                "X-Request-ID": request_id,
            },
            content={
                "error": {
                    "code": "RATE_LIMITED",
                    "message": (
                        str(exc.detail)
                        if exc.detail
                        else "请求过于频繁，请稍后再试"
                    ),
                    "request_id": request_id,
                    "retryable": True,
                }
            },
        )

    app.add_middleware(
        SlowAPIMiddleware,
    )

    app.include_router(api_router)

    return app


app = create_app()
