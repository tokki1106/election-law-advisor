import uuid
import json
import asyncio
from fastapi import APIRouter, HTTPException
from backend.schemas import ChatRequest
from sse_starlette.sse import EventSourceResponse
from backend.database import get_db
from backend.agents.graph import run_agent_workflow

router = APIRouter(prefix="/api", tags=["채팅"])


async def _save_responses(
    conversation_id: str,
    conservative_full: str,
    liberal_full: str,
    consensus_data: dict,
):
    """Save agent responses to DB after streaming completes."""
    db = await get_db()
    try:
        cited_json = json.dumps(
            consensus_data.get("cited_articles", []),
            ensure_ascii=False,
        )
        await db.execute(
            "INSERT INTO messages (id, conversation_id, role, content, cited_articles) VALUES (?, ?, 'conservative', ?, ?)",
            (str(uuid.uuid4()), conversation_id, conservative_full, cited_json),
        )
        await db.execute(
            "INSERT INTO messages (id, conversation_id, role, content, cited_articles) VALUES (?, ?, 'liberal', ?, ?)",
            (str(uuid.uuid4()), conversation_id, liberal_full, cited_json),
        )
        await db.execute(
            "INSERT INTO messages (id, conversation_id, role, content, risk_level, cited_articles) VALUES (?, ?, 'consensus', ?, ?, ?)",
            (
                str(uuid.uuid4()),
                conversation_id,
                consensus_data.get("content", ""),
                consensus_data.get("risk_level", "caution"),
                cited_json,
            ),
        )
        await db.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        await db.commit()
    except Exception as e:
        print(f"[chat] DB save error: {e}")
    finally:
        await db.close()


@router.post(
    "/chat",
    summary="선거법 자문 (SSE 스트리밍)",
    description=(
        "질문을 보내면 두 에이전트(보수/관용)가 동시에 분석하고 합의를 도출합니다.\n\n"
        "응답은 Server-Sent Events(SSE)로 스트리밍됩니다.\n\n"
        "**SSE 이벤트 종류:**\n"
        "- `conservative_start` / `liberal_start` — 에이전트 분석 시작\n"
        "- `conservative_token` / `liberal_token` — 토큰 단위 스트리밍 `{token: '...'}`\n"
        "- `conservative_end` / `liberal_end` — 분석 완료 `{cited_articles: [...]}`\n"
        "- `consensus` — 합의 결론 `{content, risk_level, cited_articles, request_feedback}`\n\n"
        "**위험도 등급:** safe(안전) / caution(주의) / danger(위반가능)"
    ),
)
async def chat(body: ChatRequest):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT mode FROM conversations WHERE id = ?",
            (body.conversation_id,),
        )
        conv = await cursor.fetchone()
        if not conv:
            raise HTTPException(404, "conversation not found")
        mode = conv[0]

        # Save user message
        await db.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, 'user', ?)",
            (str(uuid.uuid4()), body.conversation_id, body.question),
        )

        # Set conversation title on first message
        cursor = await db.execute(
            "SELECT title FROM conversations WHERE id = ?",
            (body.conversation_id,),
        )
        row = await cursor.fetchone()
        if row and not row[0]:
            title = body.question[:50] + (
                "..." if len(body.question) > 50 else ""
            )
            await db.execute(
                "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (title, body.conversation_id),
            )

        await db.commit()
    finally:
        await db.close()

    async def event_generator():
        conservative_full = ""
        liberal_full = ""
        consensus_data = {}

        try:
            async for event in run_agent_workflow(
                body.question, mode, body.conversation_id
            ):
                if event.event == "conservative_token":
                    conservative_full += event.data.get("token", "")
                elif event.event == "liberal_token":
                    liberal_full += event.data.get("token", "")
                elif event.event == "consensus":
                    consensus_data = event.data

                yield {
                    "event": event.event,
                    "data": json.dumps(event.data, ensure_ascii=False),
                }
        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"error": str(e)}, ensure_ascii=False),
            }

        # Save to DB in background after stream ends
        asyncio.create_task(
            _save_responses(
                body.conversation_id,
                conservative_full,
                liberal_full,
                consensus_data,
            )
        )

    return EventSourceResponse(event_generator())
