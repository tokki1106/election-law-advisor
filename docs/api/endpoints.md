# API 레퍼런스

## Swagger UI

서버 실행 후 아래 URL에서 인터랙티브 API 문서를 확인할 수 있습니다:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## 엔드포인트 목록

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | /api/health | 서버 상태 확인 |
| POST | /api/chat | SSE 스트리밍 채팅 |
| GET | /api/conversations | 대화 목록 조회 |
| POST | /api/conversations | 새 대화 생성 |
| GET | /api/conversations/:id | 대화 상세 조회 |
| PATCH | /api/conversations/:id | 대화 수정 (고정/폴더) |
| DELETE | /api/conversations/:id | 대화 삭제 |
| POST | /api/search | RAG 법률/사례 검색 |
| GET | /api/search/stats | 인덱스 통계 |
| POST | /api/feedback | 피드백 저장 |
| GET | /api/feedback | 피드백 목록 조회 |

---

## POST /api/chat

질문을 보내면 두 에이전트(보수/관용)가 **동시에** SSE로 응답을 스트리밍합니다.

**요청:**

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "question": "선거일에 투표 독려 문자를 보내도 되나요?"
}
```

**SSE 이벤트 (병렬 스트리밍):**

두 에이전트의 토큰이 교차로 전송됩니다.

```
event: conservative_start
data: {}

event: liberal_start
data: {}

event: conservative_token
data: {"token": "투표 독려 문자는..."}

event: liberal_token
data: {"token": "네, 가능합니다..."}

event: conservative_end
data: {"cited_articles": ["공직선거법 제57조의3"]}

event: liberal_end
data: {"cited_articles": ["공직선거법 제60조"]}

event: consensus
data: {
  "content": "합의 결론...",
  "risk_level": "caution",
  "cited_articles": ["공직선거법 제57조의3", "공직선거법 제60조"],
  "request_feedback": true
}
```

!!! note "위험도 등급"
    `risk_level` 값: `safe`(안전), `caution`(주의), `danger`(위반가능)

---

## POST /api/conversations

**요청:**

```json
{
  "mode": "citizen"
}
```

mode: `citizen` (일반 시민) 또는 `candidate` (후보자/선거운동원)

**응답:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "mode": "citizen"
}
```

---

## GET /api/conversations/:id

대화 메타정보와 모든 메시지를 반환합니다.

**응답:**

```json
{
  "conversation": {
    "id": "550e8400-...",
    "title": "선거일에 투표 독려 문자 보내도 되나요?",
    "mode": "citizen",
    "pinned": 0,
    "folder": null,
    "created_at": "2026-04-02 10:30:00",
    "updated_at": "2026-04-02 10:35:00"
  },
  "messages": [
    {
      "id": "660e8400-...",
      "role": "user",
      "content": "선거일에 투표 독려 문자 보내도 되나요?",
      "risk_level": null,
      "cited_articles": null,
      "created_at": "2026-04-02 10:30:00"
    },
    {
      "id": "770e8400-...",
      "role": "conservative",
      "content": "선거일 당일의 투표 독려 문자는 매우 위험합니다...",
      "risk_level": null,
      "cited_articles": "[\"공직선거법 제57조의3\"]",
      "created_at": "2026-04-02 10:31:00"
    }
  ]
}
```

---

## PATCH /api/conversations/:id

대화를 고정하거나 폴더에 넣습니다.

**요청:**

```json
{
  "pinned": true,
  "folder": "선거운동 관련"
}
```

---

## POST /api/search

Hybrid RAG 검색 (BM25 + 벡터 + RRF 병합 + 상호참조 확장)

**요청:**

```json
{
  "query": "기부행위 제한",
  "top_k": 5,
  "expand_refs": true
}
```

**응답:**

```json
{
  "query": "기부행위 제한",
  "total": 7,
  "results": [
    {
      "id": "공직선거법_법률__제112조",
      "text": "제112조 (기부행위의 정의) ...",
      "metadata": {
        "law_name": "공직선거법_법률",
        "article": "제112조",
        "type": "law"
      }
    },
    {
      "id": "case__0497",
      "text": "- 예비후보자가 군청, 경찰서 등의 다수의 사무실을 방문하여...",
      "metadata": {
        "category": "기부행위",
        "judgment": "prohibited",
        "type": "case_example"
      }
    }
  ]
}
```

---

## GET /api/search/stats

인덱스 통계를 반환합니다.

**응답:**

```json
{
  "total_chunks": 1877,
  "law_chunks": 1039,
  "case_example_chunks": 838,
  "cross_references": 724
}
```

---

## POST /api/feedback

**요청:**

```json
{
  "conversation_id": "550e8400-...",
  "user_question": "선거일에 투표 독려 문자 보내도 되나요?",
  "bot_response": "[보수] 위험합니다... [관용] 가능합니다... [합의] 조건부 허용...",
  "risk_level": "caution",
  "rating": "up"
}
```

rating: `up` (좋아요) 또는 `down` (싫어요)
