"""API 키 인증 + Rate Limiting.

공개 경로 (docs, health 등)는 인증 없이 접근 가능.
그 외 API 엔드포인트는 X-API-Key 헤더 필요.
웹 프론트엔드(Same-Origin)에서의 접근은 Referer/Origin 기반으로 허용.
/api/chat은 IP당 1분 최대 2회 요청 제한.
"""

import os
import time
import secrets
from collections import defaultdict
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
    "/api/search",
}

# 프리픽스 기반 공개 경로 (정적 파일 등)
PUBLIC_PREFIXES = (
    "/_app/",
    "/favicon",
    "/robots",
    "/api-docs",
)

# Rate limit 설정: /api/chat → IP당 1분 2회
RATE_LIMIT_WINDOW = 60  # 초
RATE_LIMIT_MAX = 2  # 최대 요청 수
RATE_LIMITED_PATHS = {"/api/chat"}


class RateLimiter:
    """IP 기반 슬라이딩 윈도우 rate limiter."""

    def __init__(self, window: int = 60, max_requests: int = 2):
        self.window = window
        self.max_requests = max_requests
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, ip: str) -> tuple[bool, int]:
        """요청 허용 여부와 남은 시간(초)을 반환."""
        now = time.time()
        cutoff = now - self.window

        # 윈도우 밖의 오래된 기록 제거
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]

        if len(self._requests[ip]) >= self.max_requests:
            oldest = self._requests[ip][0]
            retry_after = int(oldest + self.window - now) + 1
            return False, retry_after

        self._requests[ip].append(now)
        return True, 0

    @property
    def remaining(self):
        """메모리 정리용 — 오래된 IP 엔트리 삭제."""
        now = time.time()
        cutoff = now - self.window * 2
        stale = [ip for ip, times in self._requests.items() if all(t < cutoff for t in times)]
        for ip in stale:
            del self._requests[ip]


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


def _get_client_ip(request: Request) -> str:
    """클라이언트 IP 추출 (프록시 뒤에서도 동작)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class APIKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.api_key = get_service_api_key()
        self.chat_limiter = RateLimiter(
            window=RATE_LIMIT_WINDOW,
            max_requests=RATE_LIMIT_MAX,
        )

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

        # Rate limit: /api/chat
        if path in RATE_LIMITED_PATHS and request.method == "POST":
            client_ip = _get_client_ip(request)
            allowed, retry_after = self.chat_limiter.is_allowed(client_ip)
            if not allowed:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"요청 제한: IP당 1분에 최대 {RATE_LIMIT_MAX}회 질문 가능합니다. {retry_after}초 후 다시 시도하세요.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

        # Same-Origin 요청 (웹 프론트엔드)
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
