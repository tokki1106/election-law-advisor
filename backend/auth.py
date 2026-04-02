"""API 키 인증 — 외부 접근 보호.

공개 경로 (docs, health 등)는 인증 없이 접근 가능.
그 외 API 엔드포인트는 X-API-Key 헤더 필요.
웹 프론트엔드(Same-Origin)에서의 접근은 Referer/Origin 기반으로 허용.
"""

import os
import json
import secrets
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# 인증 없이 접근 가능한 경로
PUBLIC_PATHS = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/health",
    "/api/search/stats",
}

# 프리픽스 기반 공개 경로 (정적 파일 등)
PUBLIC_PREFIXES = (
    "/_app/",
    "/favicon",
    "/robots",
)


def get_service_api_key() -> str:
    """환경 변수에서 SERVICE_API_KEY를 가져오거나 자동 생성."""
    key = os.environ.get("SERVICE_API_KEY", "").strip()
    if not key:
        key = secrets.token_urlsafe(32)
        os.environ["SERVICE_API_KEY"] = key
        print(f"\n{'='*50}")
        print(f"  자동 생성된 SERVICE_API_KEY:")
        print(f"  {key}")
        print(f"{'='*50}\n")
    return key


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.api_key = get_service_api_key()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 공개 경로는 통과
        if path in PUBLIC_PATHS:
            return await call_next(request)

        for prefix in PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # 정적 파일 (프론트엔드) — /api 가 아닌 경로
        if not path.startswith("/api"):
            return await call_next(request)

        # Same-Origin 요청 (웹 프론트엔드) — Origin 또는 Referer 확인
        origin = request.headers.get("origin", "")
        referer = request.headers.get("referer", "")
        host = request.headers.get("host", "")

        is_same_origin = False
        if host:
            if origin and (host in origin):
                is_same_origin = True
            elif referer and (host in referer):
                is_same_origin = True

        if is_same_origin:
            return await call_next(request)

        # 외부 API 호출 — X-API-Key 헤더 확인
        provided_key = request.headers.get("x-api-key", "")
        if provided_key == self.api_key:
            return await call_next(request)

        return JSONResponse(
            status_code=401,
            content={"detail": "인증 필요: X-API-Key 헤더에 유효한 API 키를 포함하세요"},
        )
