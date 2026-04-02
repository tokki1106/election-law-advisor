"""Pydantic 응답 모델 — Swagger 문서용 예시 포함."""

from pydantic import BaseModel, Field


# ─── Conversations ───

class ConversationCreate(BaseModel):
    mode: str = Field(..., description="사용자 모드", examples=["citizen"])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"mode": "citizen"},
                {"mode": "candidate"},
            ]
        }
    }


class ConversationOut(BaseModel):
    id: str = Field(..., examples=["550e8400-e29b-41d4-a716-446655440000"])
    title: str | None = Field(None, examples=["선거일에 투표 독려 문자 보내도 되나요?"])
    mode: str = Field(..., examples=["citizen"])
    pinned: int = Field(0, examples=[0])
    folder: str | None = Field(None, examples=[None])
    created_at: str = Field(..., examples=["2026-04-02 10:30:00"])
    updated_at: str = Field(..., examples=["2026-04-02 10:35:00"])


class ConversationCreateResponse(BaseModel):
    id: str = Field(..., examples=["550e8400-e29b-41d4-a716-446655440000"])
    mode: str = Field(..., examples=["citizen"])


class ConversationUpdate(BaseModel):
    pinned: bool | None = Field(None, description="상단 고정 여부", examples=[True])
    folder: str | None = Field(None, description="폴더 이름", examples=["선거운동 관련"])


class MessageOut(BaseModel):
    id: str = Field(..., examples=["660e8400-e29b-41d4-a716-446655440001"])
    role: str = Field(..., description="메시지 역할", examples=["conservative"])
    content: str = Field(..., examples=["공직선거법 제58조에 따르면..."])
    risk_level: str | None = Field(None, examples=["caution"])
    cited_articles: str | None = Field(None, examples=['["공직선거법 제58조", "공직선거법 제93조"]'])
    created_at: str = Field(..., examples=["2026-04-02 10:31:00"])


class ConversationDetail(BaseModel):
    conversation: ConversationOut
    messages: list[MessageOut]


# ─── Chat ───

class ChatRequest(BaseModel):
    conversation_id: str = Field(..., description="대화 세션 ID", examples=["550e8400-e29b-41d4-a716-446655440000"])
    question: str = Field(..., description="선거법 관련 질문", examples=["선거일에 지인에게 투표 독려 문자를 보내도 되나요?"])


# ─── Feedback ───

class FeedbackCreate(BaseModel):
    conversation_id: str = Field(..., examples=["550e8400-e29b-41d4-a716-446655440000"])
    user_question: str = Field(..., examples=["선거일에 투표 독려 문자 보내도 되나요?"])
    bot_response: str = Field(..., examples=["[보수] 위험합니다... [관용] 가능합니다... [합의] 조건부 허용..."])
    risk_level: str | None = Field(None, examples=["caution"])
    rating: str = Field(..., description="평가", examples=["up"])


class FeedbackOut(BaseModel):
    id: str = Field(..., examples=["770e8400-e29b-41d4-a716-446655440002"])
    conversation_id: str = Field(..., examples=["550e8400-e29b-41d4-a716-446655440000"])
    user_question: str = Field(..., examples=["선거일에 투표 독려 문자 보내도 되나요?"])
    bot_response: str = Field(..., examples=["합의 결론 내용..."])
    risk_level: str | None = Field(None, examples=["caution"])
    rating: str = Field(..., examples=["up"])
    created_at: str = Field(..., examples=["2026-04-02 10:32:00"])


# ─── RAG Search ───

class RAGSearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리", examples=["기부행위 제한"])
    top_k: int = Field(10, description="검색 결과 수", examples=[5])
    expand_refs: bool = Field(True, description="상호참조 조문 확장 여부", examples=[True])


class RAGChunk(BaseModel):
    id: str = Field(..., examples=["공직선거법_법률__제112조"])
    text: str = Field(..., examples=["제112조 (기부행위의 정의) ① \"기부행위\"란 당해 선거구 안에 있는..."])
    metadata: dict = Field(..., examples=[{
        "law_name": "공직선거법_법률",
        "article": "제112조",
        "article_num": 112,
        "chapter": "제8장 선거비용",
        "type": "law",
        "source_file": "법률.md",
    }])


class RAGSearchResponse(BaseModel):
    query: str = Field(..., examples=["기부행위 제한"])
    total: int = Field(..., examples=[12])
    results: list[RAGChunk]


# ─── Health ───

class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
