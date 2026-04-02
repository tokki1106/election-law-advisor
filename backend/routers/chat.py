import uuid
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from backend.database import get_db
from backend.agents.graph import run_agent_workflow

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    conversation_id: str
    question: str


@router.post("/chat")
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

        async for event in run_agent_workflow(
            body.question, mode, body.conversation_id
        ):
            # Collect tokens
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

        # Save responses to DB
        db = await get_db()
        try:
            cited_json = json.dumps(
                consensus_data.get("cited_articles", []),
                ensure_ascii=False,
            )
            await db.execute(
                "INSERT INTO messages (id, conversation_id, role, content, cited_articles) VALUES (?, ?, 'conservative', ?, ?)",
                (
                    str(uuid.uuid4()),
                    body.conversation_id,
                    conservative_full,
                    cited_json,
                ),
            )
            await db.execute(
                "INSERT INTO messages (id, conversation_id, role, content, cited_articles) VALUES (?, ?, 'liberal', ?, ?)",
                (
                    str(uuid.uuid4()),
                    body.conversation_id,
                    liberal_full,
                    cited_json,
                ),
            )
            await db.execute(
                "INSERT INTO messages (id, conversation_id, role, content, risk_level, cited_articles) VALUES (?, ?, 'consensus', ?, ?, ?)",
                (
                    str(uuid.uuid4()),
                    body.conversation_id,
                    consensus_data.get("content", ""),
                    consensus_data.get("risk_level", "caution"),
                    cited_json,
                ),
            )
            await db.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (body.conversation_id,),
            )
            await db.commit()
        finally:
            await db.close()

    return EventSourceResponse(event_generator())
