import uuid
from fastapi import APIRouter, HTTPException
from backend.database import get_db
from backend.schemas import (
    ConversationCreate,
    ConversationCreateResponse,
    ConversationOut,
    ConversationUpdate,
    ConversationDetail,
)

router = APIRouter(prefix="/api/conversations", tags=["대화"])


@router.post(
    "",
    response_model=ConversationCreateResponse,
    summary="새 대화 생성",
    description="사용자 모드(citizen/candidate)를 선택하여 새 대화 세션을 생성합니다.",
)
async def create_conversation(body: ConversationCreate):
    if body.mode not in ("citizen", "candidate"):
        raise HTTPException(400, "mode must be 'citizen' or 'candidate'")
    conv_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO conversations (id, mode) VALUES (?, ?)",
            (conv_id, body.mode),
        )
        await db.commit()
        return {"id": conv_id, "mode": body.mode}
    finally:
        await db.close()


@router.get(
    "",
    response_model=list[ConversationOut],
    summary="대화 목록 조회",
    description="모든 대화 목록을 반환합니다. 고정된 대화가 먼저, 이후 최근 업데이트 순으로 정렬됩니다.",
)
async def list_conversations():
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, mode, pinned, folder, created_at, updated_at FROM conversations ORDER BY pinned DESC, updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@router.get(
    "/{conv_id}",
    response_model=ConversationDetail,
    summary="대화 상세 조회",
    description="특정 대화의 메타정보와 모든 메시지(user, conservative, liberal, consensus)를 반환합니다.",
)
async def get_conversation(conv_id: str):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, mode, pinned, folder, created_at, updated_at FROM conversations WHERE id = ?",
            (conv_id,),
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
async def update_conversation(conv_id: str, body: ConversationUpdate):
    db = await get_db()
    try:
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
    description="대화와 관련 메시지를 모두 삭제합니다.",
)
async def delete_conversation(conv_id: str):
    db = await get_db()
    try:
        await db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        await db.commit()
        return {"deleted": True}
    finally:
        await db.close()
