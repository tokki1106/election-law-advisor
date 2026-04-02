import uuid
from fastapi import APIRouter
from backend.database import get_db
from backend.schemas import FeedbackCreate, FeedbackOut

router = APIRouter(prefix="/api/feedback", tags=["피드백"])


@router.post(
    "",
    summary="응답 평가 저장",
    description="사용자가 봇 응답에 대해 좋아요/싫어요 평가를 제출합니다.",
)
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


@router.get(
    "",
    response_model=list[FeedbackOut],
    summary="피드백 목록 조회",
    description="수집된 모든 피드백을 최신순으로 반환합니다. 관리/분석용 엔드포인트입니다.",
)
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
