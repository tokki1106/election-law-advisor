# 선거법 자문 에이전트

한국 선거법(공직선거법, 정치자금법, 정당법)에 기반하여 특정 행위가 선거법에 저촉되는지 판단하고 조언하는 **대화형 웹서비스**입니다.

두 명의 AI 에이전트(보수적/관용적)가 **실시간으로 동시에 토론**하고, 합의를 도출하여 위험도 등급과 함께 답변합니다.

## 주요 기능

- **듀얼 에이전트 토론**: 보수적 해석(엄격)과 관용적 해석(유연)이 동시에 분석 후 합의 도출
- **위험도 등급**: 안전 / 주의 / 위반가능 3단계 판정
- **법률 RAG**: 공직선거법 등 선거 관련 법률 + 시행령/시행규칙을 Hybrid Retrieval(BM25 + 벡터)로 검색
- **사례 기반 답변**: 중앙선관위 사례예시집(838건) 반영
- **조문 상호참조**: "제93조 -> 제58조 참조" 자동 추적
- **실시간 스트리밍**: SSE 기반 토큰 단위 스트리밍
- **다크 모드**: 라이트/다크 테마 전환 지원
- **대화 이력**: SQLite 저장, 좌측 사이드바에서 열람
- **폴더 및 고정**: 대화를 폴더로 정리하고 상단 고정
- **피드백 수집**: 랜덤으로 응답 평가(좋아요/싫어요) 수집
- **위반 신고**: 위반가능 판정 시 중앙선관위 신고 페이지 바로가기
- **사용자 모드**: 일반 시민 / 후보자 및 선거운동원 맞춤 답변

## 기술 스택

| 구성 | 기술 |
|---|---|
| 프론트엔드 | SvelteKit (TypeScript) |
| 백엔드 | FastAPI (Python) |
| LLM | OpenRouter API - Gemini 3.1 Flash Lite |
| RAG | LangChain + ChromaDB + BM25 (rank_bm25) |
| 임베딩 | sentence-transformers (paraphrase-multilingual-MiniLM-L12-v2) |
| 데이터베이스 | SQLite (aiosqlite) |
| 법률 데이터 | [legalize-kr](https://github.com/legalize-kr/legalize-kr) |

## 빠른 시작

### 사전 요구사항

- Python 3.12+
- Node.js 20+
- [OpenRouter API 키](https://openrouter.ai/keys)

### 설치

```bash
git clone https://github.com/YOUR_USERNAME/legal.git
cd legal

# 1. 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 OPENROUTER_API_KEY에 본인 API 키 입력

# 2. Python 의존성 설치
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 3. 프론트엔드 설치
cd frontend && npm install && cd ..

# 4. 법률 데이터 클론 및 인덱싱
python3 scripts/index_laws.py

# 5. 프론트엔드 빌드
cd frontend && npm run build && cd ..

# 6. 서버 시작
./start.sh
```

브라우저에서 http://localhost:8000 접속

### 간편 실행 (설치 완료 후)

```bash
./start.sh
```

## 프로젝트 구조

```
legal/
  backend/
    main.py              # FastAPI 진입점
    database.py          # SQLite 스키마
    routers/
      chat.py            # SSE 스트리밍 채팅 API
      conversations.py   # 대화 CRUD API
      feedback.py        # 피드백 API
    agents/
      graph.py           # 듀얼 에이전트 워크플로우 (병렬 스트리밍)
      conservative.py    # 보수적 해석 프롬프트
      liberal.py         # 관용적 해석 프롬프트
      consensus.py       # 합의 도출 프롬프트
      query_analyzer.py  # 쿼리 분석
    rag/
      indexer.py         # 법률 데이터 청킹 및 인덱싱
      retriever.py       # Hybrid Retrieval (BM25 + 벡터 + RRF)
      cross_ref.py       # 조문 상호참조 파서
  frontend/
    src/
      lib/components/    # Svelte UI 컴포넌트
      lib/stores/        # 상태 관리 (대화, 테마)
      routes/            # 페이지 라우팅
  scripts/
    clone_laws.sh        # 법률 데이터 sparse checkout
    index_laws.py        # 인덱싱 실행 스크립트
  start.sh               # 서버 시작 스크립트
```

## 워크플로우

```
사용자 질문
  -> 쿼리 분석 및 법률 용어 변환
  -> Hybrid Retrieval (BM25 키워드 + 벡터 시맨틱)
  -> 조문 상호참조 확장
  -> 보수적 에이전트 + 관용적 에이전트 (동시 스트리밍)
  -> 합의 도출 에이전트
  -> 위험도 등급 + 근거 조문 + 최종 답변
```

## 지식 소스

| 소스 | 내용 | 출처 |
|---|---|---|
| 공직선거법 | 법률 + 시행령 + 시행규칙 | legalize-kr |
| 정치자금법 | 법률 + 시행령 + 시행규칙 | legalize-kr |
| 정당법 | 법률 + 시행령 + 시행규칙 | legalize-kr |
| 공직선거관리규칙 | 선거관리위원회 규칙 | legalize-kr |
| 사례예시집 | 838건의 허용/금지 사례 | 중앙선관위 |

## 위험도 등급

| 등급 | 의미 | 조건 |
|---|---|---|
| 안전 | 합법 | 두 에이전트 모두 합법 판단 |
| 주의 | 조건부 | 의견 갈림 또는 조건부 허용 |
| 위반가능 | 위법 소지 | 두 에이전트 모두 위반 가능성 인정 |

위반가능 판정 시 **중앙선관위 위반행위 신고** 버튼이 표시됩니다.

## 면책 조항

이 서비스는 **법률 자문을 대체하지 않습니다**. AI 기반 참고 자료로만 활용하시고, 정확한 법적 판단이 필요한 경우 반드시 관할 선거관리위원회(1390) 또는 법률 전문가에게 문의하세요.

## 라이선스

[MIT License](LICENSE)

법률 원문은 대한민국 공공저작물로 자유이용이 가능합니다.
