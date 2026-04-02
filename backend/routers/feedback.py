import uuid
from fastapi import APIRouter
from pydantic import BaseModel
from backend.database import get_db

router = APIRouter(prefix="/api/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    conversation_id: str
    user_question: str
    bot_response: str
    risk_level: str | None = None
    rating: str  # 'up' | 'down'


@router.post("")
async def create_feedback(body: FeedbackCreate):
    fb_id = str(uuid.uuid4())
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO feedbacks (id, conversation_id, user_question, bot_response, risk_level, rating) VALUES (?, ?, ?, ?, ?, ?)",
            (fb_id, body.conversation_id, body.user_question, body.bot_response, body.risk_level, body.rating),
        )
        await db.commit()
        return {"id": fb_id}
    finally:
        await db.close()


@router.get("")
async def list_feedbacks():
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, conversation_id, user_question, bot_response, risk_level, rating, created_at FROM feedbacks ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()
