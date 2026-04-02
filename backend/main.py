import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from backend.database import init_db
from backend.schemas import HealthResponse
from backend.auth import APIKeyMiddleware

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="선거법 자문 에이전트 API",
    description=(
        "한국 선거법(공직선거법, 정치자금법, 정당법) 기반 AI 자문 서비스 API.\n\n"
        "두 에이전트(보수적/관용적)가 동시에 분석하고 합의를 도출합니다.\n\n"
        "- **채팅**: SSE 스트리밍 기반 실시간 토론\n"
        "- **검색**: Hybrid RAG (BM25 + 벡터) 법률 검색\n"
        "- **대화**: 세션 관리, 폴더, 고정\n"
        "- **피드백**: 응답 평가 수집"
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(APIKeyMiddleware)

from backend.routers import chat, conversations, feedback, search

app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(feedback.router)
app.include_router(search.router)


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["시스템"],
    summary="서버 상태 확인",
)
async def health():
    return {"status": "ok"}


FRONTEND_BUILD = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "build"
)

if os.path.isdir(FRONTEND_BUILD):
    app.mount(
        "/", StaticFiles(directory=FRONTEND_BUILD, html=True), name="frontend"
    )
