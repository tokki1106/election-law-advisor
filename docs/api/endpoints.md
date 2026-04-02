# API 레퍼런스

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
| POST | /api/feedback | 피드백 저장 |
| GET | /api/feedback | 피드백 목록 조회 |

---

## POST /api/chat

질문을 보내면 SSE로 에이전트 응답이 스트리밍됩니다.

**요청:**

```json
{
  "conversation_id": "uuid",
  "question": "선거일에 투표 독려 문자를 보내도 되나요?"
}
```

**SSE 이벤트:**

```
event: conservative_start
data: {}

event: conservative_token
data: {"token": "투표 독려 문자는..."}

event: liberal_start
data: {}

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
  "id": "uuid",
  "mode": "citizen"
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

## POST /api/feedback

**요청:**

```json
{
  "conversation_id": "uuid",
  "user_question": "원본 질문",
  "bot_response": "봇 응답 전체",
  "risk_level": "caution",
  "rating": "up"
}
```

rating: `up` (좋아요) 또는 `down` (싫어요)
