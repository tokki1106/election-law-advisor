# 선거법 자문 에이전트 서비스 설계 문서

## 개요

한국 선거법(공직선거법, 정치자금법, 정당법)에 기반하여 특정 행위가 선거법에 저촉되는지 판단하고 조언하는 대화형 웹서비스. 두 명의 AI 에이전트(보수적/관용적)가 실시간으로 토론하고 합의를 도출하여 답변한다.

## 기술 스택

| 구성 | 기술 |
|---|---|
| 프론트엔드 | SvelteKit |
| 백엔드 | FastAPI (Python) |
| LLM | OpenRouter API → Gemini 3.1 Flash Lite |
| RAG 프레임워크 | LangChain + LangGraph |
| 벡터 DB | ChromaDB (로컬) |
| 키워드 검색 | BM25 (rank_bm25) |
| 임베딩 | sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (로컬) |
| 대화 저장 | SQLite |
| 배포 | 로컬 서버 (/home/ubuntu/legal) |
| 언어 | 한국어 전용 |

## 지식 소스

### 법률 데이터
- **출처**: https://github.com/legalize-kr/legalize-kr
- **범위**: 선거 관련 법률 + 시행령 + 시행규칙
  - 공직선거법 (법률.md, 시행령.md, 시행규칙.md)
  - 정치자금법 (법률.md, 시행령.md, 시행규칙.md)
  - 정당법 (법률.md, 시행령.md, 시행규칙.md)
  - 관련 선거관리규칙들

### 사례 데이터
- **파일**: /home/ubuntu/legal/정치관계법_사례예시집.md
- **내용**: 중앙선관위 발행 사례집 (6,816줄), 허용/금지 사례와 해설

## 아키텍처

```
┌─────────────────────────────────────────────────┐
│                SvelteKit (프론트엔드)               │
│  ┌──────────┐  ┌─────────────────────────────┐   │
│  │ 사이드바   │  │        대화 영역              │   │
│  │ 대화이력   │  │  [모드 선택: 시민/후보자]      │   │
│  │ 목록      │  │  [질문 입력]                  │   │
│  │          │  │  [보수 에이전트 스트리밍]       │   │
│  │          │  │  [관용 에이전트 스트리밍]       │   │
│  │          │  │  [합의 결론]                  │   │
│  └──────────┘  └─────────────────────────────┘   │
│                    ↕ SSE (Server-Sent Events)      │
└─────────────────────────────────────────────────┘
                         │
┌─────────────────────────────────────────────────┐
│              FastAPI (백엔드)                      │
│                                                   │
│  ┌─────────────────────────────────────────┐     │
│  │         LangGraph 워크플로우               │     │
│  │                                          │     │
│  │  질문 → 쿼리분석 → Hybrid Retrieval      │     │
│  │              ↓                           │     │
│  │      관련 조문 + 재귀참조 탐색             │     │
│  │         ↙          ↘                     │     │
│  │  보수 에이전트    관용 에이전트             │     │
│  │         ↘          ↙                     │     │
│  │        합의 도출 에이전트                  │     │
│  │              ↓                           │     │
│  │         최종 응답 (SSE)                   │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ ChromaDB │  │ BM25     │  │ SQLite       │   │
│  │ (벡터)    │  │ (키워드)  │  │ (대화이력)    │   │
│  └──────────┘  └──────────┘  └──────────────┘   │
│                                                   │
│  OpenRouter API → Gemini 3.1 Flash Lite           │
└─────────────────────────────────────────────────┘
```

## LangGraph 워크플로우

### 노드 구성

1. **쿼리 분석 & 재작성**: 사용자 모드(시민/후보자) + 질문 의도 파악, 애매한 질문을 명확한 법률 검색 쿼리로 변환
2. **Hybrid Retrieval**: BM25(법률 용어 정확 매칭) + 벡터(의미적 유사 조문), RRF(Reciprocal Rank Fusion)로 결과 병합
3. **관련성 평가 & 필터링**: 검색된 각 조문의 관련성을 LLM이 채점, 관련 없으면 쿼리 재작성 후 재검색 (최대 2회)
4. **조문 참조 확장**: "제93조 → 제58조 참조" 같은 상호참조 추적, 참조된 조문 추가 검색
5. **보수적 에이전트**: 법 조문의 문리적·엄격 해석, "의심되면 하지 마라" 관점 (SSE로 먼저 스트리밍)
6. **관용적 에이전트**: 법 취지와 판례 기반 합리적 해석, "명시적 금지가 아니면 허용 가능성 탐색" 관점 (보수 완료 후 스트리밍)
7. **합의 도출 에이전트**: 두 의견 종합 → 공통 합의점 + 견해 차이 + 최종 권고(위험도 등급)

**스트리밍 순서**: 보수 에이전트 → 관용 에이전트 → 합의 (순차). 백엔드에서는 두 에이전트를 병렬로 호출하되, SSE 전송은 사용자가 읽기 쉽도록 순차 전달한다.

### 에이전트 성격

| | 보수적 에이전트 | 관용적 에이전트 |
|---|---|---|
| 관점 | 법 조문의 문리적·엄격 해석 | 법 취지와 판례 기반 합리적 해석 |
| 성향 | "의심되면 하지 마라" | "법이 명시적으로 금지하지 않으면 허용 가능성 탐색" |
| 시민 모드 | 쉬운 말 + 강한 경고 | 쉬운 말 + 가능한 범위 안내 |
| 후보자 모드 | 조문 번호 명시 + 판례 참조 + 리스크 분석 | 조문 번호 명시 + 허용 범위와 조건 상세 |

### 위험도 등급
- 🟢 **안전**: 두 에이전트 모두 합법 판단
- 🟡 **주의**: 의견 갈림 또는 조건부 허용
- 🔴 **위반가능**: 두 에이전트 모두 위반 가능성 인정

## 청킹 전략

### 법률 텍스트 — 조문 단위 구조적 청킹

```
제58조 (정의)                → 1 chunk
  ├─ ① 항
  ├─ ② 항
  └─ 관련 호(1호, 2호...)

메타데이터:
  법률명: 공직선거법
  조번호: 58
  장: 제6장
  참조조문: [93, 254]
  type: law
```

### 사례예시집 — 사례 단위 청킹

```
사례 1개 = 1 chunk
  ├─ 질문/상황 설명
  ├─ ⭕/❌ 판단
  └─ 해설

메타데이터:
  관련조문: [58, 93]
  카테고리: 선거운동
  type: case_example
  판단: allowed / prohibited
```

### 상호참조 인덱스

각 조문에서 참조하는 다른 조문 번호를 정규식으로 파싱하여 인덱스 구축. Retrieval 시 관련 조문을 자동으로 함께 가져온다.

```python
cross_refs = {
    "공직선거법_제58조": ["공직선거법_제93조", "공직선거법_제254조"],
    ...
}
```

### 임베딩 모델

sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 (한국어 지원, 무료, 로컬 실행)

## 프론트엔드 UI

### 레이아웃
- **좌측 사이드바**: 날짜별 그룹핑된 대화 이력, 클릭 시 해당 대화 로드
- **모드 선택**: 대화 시작 시 카드형 선택 (👤 일반시민 / 🏛 후보자·선거운동원)
- **토론 영역**: 보수(⚖️) / 관용(🕊️) 각각 별도 박스, 실시간 SSE 스트리밍
- **합의 결론**: 위험도 뱃지 + 결론 + 근거 조문 + 유사 사례
- **신고 버튼**: 🔴 위반가능 판정 시에만 "중앙선관위에 위반행위 신고" 버튼 표시 → https://nec.go.kr/site/nec/01/10101020000002020040704.jsp 새 탭 연결
- **피드백 평가**: 랜덤 확률(약 30%)로 합의 결론 하단에 👍/👎 버튼 표시. 사용자가 응답 만족도를 평가하면 별도 DB에 저장
- **입력창**: 하단 고정, 엔터 또는 전송 버튼

### 디자인 색상 (Claude 브랜드 톤)

| 용도 | 색상 코드 |
|---|---|
| 배경 | #FAF9F6 (웜 화이트) |
| 사이드바 | #F0EDE8 (웜 베이지) |
| 포인트/액센트 | #DA7756 (코랄 오렌지) |
| 텍스트 | #2D2B28 (다크 차콜) |
| 보수 에이전트 박스 | #E8E0D8 (라이트 탄) |
| 관용 에이전트 박스 | #EDE7DF (크림) |
| 합의 결론 박스 | #DA7756 보더 + #FDF6F0 배경 |
| 🟢 안전 | #4A8C6F |
| 🟡 주의 | #C4952A |
| 🔴 위반가능 | #C4463A |

## 데이터베이스

### SQLite 스키마

```sql
-- 대화 세션
CREATE TABLE conversations (
  id          TEXT PRIMARY KEY,
  title       TEXT,
  mode        TEXT CHECK(mode IN ('citizen', 'candidate')),
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 메시지
CREATE TABLE messages (
  id              TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
  role            TEXT CHECK(role IN ('user', 'conservative', 'liberal', 'consensus')),
  content         TEXT,
  risk_level      TEXT CHECK(risk_level IN ('safe', 'caution', 'danger')),
  cited_articles  TEXT,  -- JSON array
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 응답 평가 (별도 테이블)
CREATE TABLE feedbacks (
  id              TEXT PRIMARY KEY,
  conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
  user_question   TEXT,           -- 사용자 원본 질문
  bot_response    TEXT,           -- 합의 결론 전체 (보수+관용+합의)
  risk_level      TEXT,           -- 해당 응답의 위험도
  rating          TEXT CHECK(rating IN ('up', 'down')),  -- 👍 or 👎
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | /api/chat | SSE 스트리밍 응답 (질문 → 토론 → 합의) |
| GET | /api/conversations | 대화 목록 (사이드바용) |
| GET | /api/conversations/:id | 특정 대화 메시지 조회 |
| DELETE | /api/conversations/:id | 대화 삭제 |
| POST | /api/conversations | 새 대화 생성 (모드 선택) |
| POST | /api/feedback | 응답 평가 저장 (👍/👎) |
| GET | /api/feedback | 평가 목록 조회 (관리용) |

### SSE 이벤트 형식

```
event: conservative_start
data: {}

event: conservative_token
data: {"token": "명함 배포는..."}

event: conservative_end
data: {"cited_articles": ["공직선거법_제93조"]}

event: liberal_start
data: {}

event: liberal_token
data: {"token": "선거운동기간 중..."}

event: liberal_end
data: {"cited_articles": ["공직선거법_제60조"]}

event: consensus
data: {"risk_level": "caution", "content": "...", "cited_articles": [...], "request_feedback": true}
```

`request_feedback: true`는 서버에서 랜덤(약 30% 확률)으로 결정. 프론트엔드는 이 플래그가 true일 때만 합의 결론 하단에 👍/👎 버튼을 렌더링한다.

## 프로젝트 디렉토리 구조

```
/home/ubuntu/legal/
├── .env                          # OPENROUTER_API_KEY
├── .gitignore
├── CLAUDE.md
├── 정치관계법_사례예시집.md
├── docs/
│   └── superpowers/specs/
│       └── 2026-04-02-election-law-advisor-design.md
├── backend/
│   ├── main.py                   # FastAPI 앱 진입점
│   ├── requirements.txt
│   ├── database.py               # SQLite 연결 및 스키마
│   ├── routers/
│   │   ├── chat.py               # /api/chat SSE 엔드포인트
│   │   ├── conversations.py      # 대화 CRUD 엔드포인트
│   │   └── feedback.py           # 피드백 저장 & 조회 엔드포인트
│   ├── rag/
│   │   ├── indexer.py            # 법률 데이터 청킹 & 인덱싱
│   │   ├── retriever.py          # Hybrid Retrieval (BM25 + 벡터)
│   │   └── cross_ref.py          # 조문 상호참조 인덱스
│   ├── agents/
│   │   ├── graph.py              # LangGraph 워크플로우 정의
│   │   ├── conservative.py       # 보수적 에이전트
│   │   ├── liberal.py            # 관용적 에이전트
│   │   ├── consensus.py          # 합의 도출 에이전트
│   │   └── query_analyzer.py     # 쿼리 분석 & 재작성
│   └── data/
│       ├── chroma_db/            # ChromaDB 벡터 저장소
│       ├── bm25_index/           # BM25 인덱스
│       └── legal.db              # SQLite DB
├── frontend/
│   ├── package.json
│   ├── svelte.config.js
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +layout.svelte    # 전체 레이아웃 (사이드바 + 메인)
│   │   │   └── +page.svelte      # 대화 페이지
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── Sidebar.svelte
│   │   │   │   ├── ModeSelector.svelte
│   │   │   │   ├── ChatMessage.svelte
│   │   │   │   ├── AgentBox.svelte
│   │   │   │   ├── ConsensusBox.svelte
│   │   │   │   ├── FeedbackButtons.svelte  # 👍/👎 평가 버튼
│   │   │   │   └── ReportButton.svelte
│   │   │   ├── stores/
│   │   │   │   ├── chat.ts       # 대화 상태 관리
│   │   │   │   └── conversations.ts
│   │   │   └── api.ts            # 백엔드 API 클라이언트
│   │   └── app.css               # 글로벌 스타일 (Claude 톤)
│   └── static/
└── scripts/
    ├── clone_laws.sh             # legalize-kr 레포 클론 & 필터링
    └── index_laws.py             # 법률 데이터 인덱싱 실행 스크립트
```
