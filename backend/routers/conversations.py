import uuid
from fastapi import APIRouter, HTTPException, Request
from backend.database import get_db
from backend.schemas import (
    ConversationCreate,
    ConversationCreateResponse,
    ConversationOut,
    ConversationUpdate,
    ConversationDetail,
)

router = APIRouter(prefix="/api/conversations", tags=["대화"])


def _get_session_id(request: Request) -> str | None:
    return request.headers.get("x-session-id")


@router.post(
    "",
    response_model=ConversationCreateResponse,
    summary="새 대화 생성",
    description="사용자 모드(citizen/candidate)를 선택하여 새 대화 세션을 생성합니다. X-Session-Id 헤더 필요.",
)
async def create_conversation(body: ConversationCreate, request: Request):
    if body.mode not in ("citizen", "candidate"):
        raise HTTPException(400, "mode must be 'citizen' or 'candidate'")
    session_id = _get_session_id(request)
    if not session_id:
        raise HTTPException(400, "X-Session-Id header required")
    conv_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO conversations (id, mode, session_id) VALUES (?, ?, ?)",
            (conv_id, body.mode, session_id),
        )
        await db.commit()
        return {"id": conv_id, "mode": body.mode}
    finally:
        await db.close()


@router.get(
    "",
    response_model=list[ConversationOut],
    summary="대화 목록 조회",
    description="본인 세션의 대화 목록만 반환합니다. X-Session-Id 헤더 필요.",
)
async def list_conversations(request: Request):
    session_id = _get_session_id(request)
    if not session_id:
        return []
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, mode, pinned, folder, created_at, updated_at FROM conversations WHERE session_id = ? ORDER BY pinned DESC, updated_at DESC",
            (session_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@router.get(
    "/{conv_id}",
    response_model=ConversationDetail,
    summary="대화 상세 조회",
    description="특정 대화의 메타정보와 모든 메시지를 반환합니다. 본인 세션의 대화만 접근 가능합니다.",
)
async def get_conversation(conv_id: str, request: Request):
    session_id = _get_session_id(request)
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, mode, pinned, folder, created_at, updated_at FROM conversations WHERE id = ? AND (session_id = ? OR session_id IS NULL)",
            (conv_id, session_id),
        )
        conv = await cursor.fetchone()
        if not conv:
            raise HTTPException(404, "conversation not found")
        cursor = await db.execute(
            "SELECT id, role, content, risk_level, cited_articles, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at",
            (conv_id,),
        )
        messages = await cursor.fetchall()
        return {"conversation": dict(conv), "messages": [dict(m) for m in messages]}
    finally:
        await db.close()


@router.patch(
    "/{conv_id}",
    summary="대화 수정",
    description="대화를 상단 고정하거나 폴더에 넣습니다.",
)
async def update_conversation(conv_id: str, body: ConversationUpdate, request: Request):
    session_id = _get_session_id(request)
    db = await get_db()
    try:
        # 본인 세션 대화인지 확인
        cursor = await db.execute(
            "SELECT id FROM conversations WHERE id = ? AND (session_id = ? OR session_id IS NULL)",
            (conv_id, session_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(404, "conversation not found")

        updates = []
        params = []
        if body.pinned is not None:
            updates.append("pinned = ?")
            params.append(1 if body.pinned else 0)
        if body.folder is not None:
            updates.append("folder = ?")
            params.append(body.folder if body.folder else None)
        if not updates:
            raise HTTPException(400, "nothing to update")
        params.append(conv_id)
        await db.execute(
            f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.delete(
    "/{conv_id}",
    summary="대화 삭제",
    description="대화와 관련 메시지를 모두 삭제합니다. 본인 세션의 대화만 삭제 가능합니다.",
)
async def delete_conversation(conv_id: str, request: Request):
    session_id = _get_session_id(request)
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM conversations WHERE id = ? AND (session_id = ? OR session_id IS NULL)",
            (conv_id, session_id),
        )
        await db.commit()
        return {"deleted": True}
    finally:
        await db.close()
