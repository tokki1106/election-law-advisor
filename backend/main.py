import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from backend.database import init_db

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="선거법 자문 서비스", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


from backend.routers import chat, conversations, feedback

app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(feedback.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


FRONTEND_BUILD = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "build"
)

# This must be the LAST mount — it catches all non-API routes
if os.path.isdir(FRONTEND_BUILD):
    app.mount(
        "/", StaticFiles(directory=FRONTEND_BUILD, html=True), name="frontend"
    )
