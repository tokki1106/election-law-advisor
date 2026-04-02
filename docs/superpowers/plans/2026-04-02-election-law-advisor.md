# 선거법 자문 에이전트 서비스 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한국 선거법 기반 대화형 자문 웹서비스 — 두 에이전트(보수/관용)가 실시간 토론 후 합의를 도출

**Architecture:** SvelteKit 프론트엔드 + FastAPI 백엔드. LangGraph로 멀티 에이전트 워크플로우 구성. Hybrid Retrieval(BM25+ChromaDB)로 법률 조문 검색. OpenRouter API를 통해 Gemini 3.1 Flash Lite 모델 사용. SSE로 실시간 스트리밍.

**Tech Stack:** SvelteKit, FastAPI, LangChain, LangGraph, ChromaDB, rank_bm25, sentence-transformers, SQLite, OpenRouter API

---

## Phase 1: 백엔드 기반 (Tasks 1-5)

### Task 1: 프로젝트 초기화 & 의존성 설치

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/__init__.py`
- Create: `backend/main.py`
- Modify: `.gitignore`

- [ ] **Step 1: git 초기화**

```bash
cd /home/ubuntu/legal
git init
git add .env .gitignore CLAUDE.md 정치관계법_사례예시집.md docs/
git commit -m "chore: initial project setup with spec and design docs"
```

- [ ] **Step 2: .gitignore 보강**

`.gitignore`에 추가:

```
.env
node_modules/
__pycache__/
*.pyc
backend/data/chroma_db/
backend/data/bm25_index/
backend/data/legal.db
backend/data/laws/
.svelte-kit/
build/
venv/
```

- [ ] **Step 3: Python 가상환경 & 의존성**

```bash
cd /home/ubuntu/legal
python3 -m venv venv
source venv/bin/activate
```

`backend/requirements.txt`:

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
python-dotenv==1.1.0
langchain==0.3.25
langchain-community==0.3.24
langgraph==0.4.1
langchain-openai==0.3.18
chromadb==1.0.10
sentence-transformers==4.1.0
rank-bm25==0.2.2
aiosqlite==0.21.0
aiofiles==24.1.0
sse-starlette==2.3.3
pydantic==2.11.3
httpx==0.28.1
```

```bash
pip install -r backend/requirements.txt
```

- [ ] **Step 4: FastAPI 진입점 생성**

`backend/__init__.py`: 빈 파일

`backend/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="선거법 자문 서비스")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 서버 기동 테스트**

```bash
cd /home/ubuntu/legal
source venv/bin/activate
uvicorn backend.main:app --reload --port 8000 &
sleep 2
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
kill %1
```

- [ ] **Step 6: 커밋**

```bash
git add backend/ .gitignore
git commit -m "chore: backend project init with FastAPI and dependencies"
```

---

### Task 2: 데이터베이스 (SQLite)

**Files:**
- Create: `backend/database.py`

- [ ] **Step 1: database.py 작성**

```python
import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "legal.db")


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    db = await get_db()
    try:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                title       TEXT,
                mode        TEXT CHECK(mode IN ('citizen', 'candidate')),
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
                role            TEXT CHECK(role IN ('user', 'conservative', 'liberal', 'consensus')),
                content         TEXT,
                risk_level      TEXT CHECK(risk_level IN ('safe', 'caution', 'danger')),
                cited_articles  TEXT,
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS feedbacks (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT REFERENCES conversations(id) ON DELETE CASCADE,
                user_question   TEXT,
                bot_response    TEXT,
                risk_level      TEXT,
                rating          TEXT CHECK(rating IN ('up', 'down')),
                created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()
    finally:
        await db.close()
```

- [ ] **Step 2: main.py에 DB 초기화 연결**

`backend/main.py`에 lifespan 추가:

```python
from contextlib import asynccontextmanager
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="선거법 자문 서비스", lifespan=lifespan)
```

- [ ] **Step 3: DB 생성 테스트**

```bash
cd /home/ubuntu/legal
source venv/bin/activate
python3 -c "
import asyncio
from backend.database import init_db, get_db, DB_PATH
asyncio.run(init_db())
async def check():
    db = await get_db()
    cursor = await db.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
    tables = await cursor.fetchall()
    for t in tables:
        print(t[0])
    await db.close()
asyncio.run(check())
"
# Expected: conversations, messages, feedbacks
```

- [ ] **Step 4: 커밋**

```bash
git add backend/database.py backend/main.py
git commit -m "feat: SQLite database schema with conversations, messages, feedbacks"
```

---

### Task 3: API 라우터 — Conversations & Feedback

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/conversations.py`
- Create: `backend/routers/feedback.py`
- Modify: `backend/main.py`

- [ ] **Step 1: conversations.py 작성**

`backend/routers/__init__.py`: 빈 파일

```python
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.database import get_db

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    mode: str  # 'citizen' | 'candidate'


@router.post("")
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


@router.get("")
async def list_conversations():
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, mode, created_at, updated_at FROM conversations ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


@router.get("/{conv_id}")
async def get_conversation(conv_id: str):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, title, mode, created_at FROM conversations WHERE id = ?",
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


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str):
    db = await get_db()
    try:
        await db.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
        await db.commit()
        return {"deleted": True}
    finally:
        await db.close()
```

- [ ] **Step 2: feedback.py 작성**

```python
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
```

- [ ] **Step 3: main.py에 라우터 등록**

```python
from backend.routers import conversations, feedback

app.include_router(conversations.router)
app.include_router(feedback.router)
```

- [ ] **Step 4: API 테스트**

```bash
cd /home/ubuntu/legal && source venv/bin/activate
uvicorn backend.main:app --reload --port 8000 &
sleep 2

# Create conversation
curl -X POST http://localhost:8000/api/conversations -H "Content-Type: application/json" -d '{"mode":"citizen"}'
# Expected: {"id":"...","mode":"citizen"}

# List conversations
curl http://localhost:8000/api/conversations
# Expected: [{"id":"...","title":null,"mode":"citizen",...}]

kill %1
```

- [ ] **Step 5: 커밋**

```bash
git add backend/routers/
git commit -m "feat: REST API for conversations and feedback CRUD"
```

---

### Task 4: 법률 데이터 수집 & 청킹 파이프라인

**Files:**
- Create: `scripts/clone_laws.sh`
- Create: `backend/rag/__init__.py`
- Create: `backend/rag/indexer.py`
- Create: `backend/rag/cross_ref.py`

- [ ] **Step 1: clone_laws.sh 작성**

```bash
#!/bin/bash
set -e

DATA_DIR="/home/ubuntu/legal/backend/data/laws"
REPO_URL="https://github.com/legalize-kr/legalize-kr.git"

if [ -d "$DATA_DIR" ]; then
    echo "Laws directory already exists, skipping clone"
    exit 0
fi

mkdir -p "$DATA_DIR"

# Sparse checkout: only election-related laws
git clone --depth 1 --filter=blob:none --sparse "$REPO_URL" "$DATA_DIR/repo"
cd "$DATA_DIR/repo"
git sparse-checkout set \
    "kr/공직선거법" \
    "kr/정치자금법" \
    "kr/정당법" \
    "kr/공직선거관리규칙"

echo "Done. Laws cloned to $DATA_DIR/repo/kr/"
ls -la kr/
```

- [ ] **Step 2: clone 실행**

```bash
chmod +x /home/ubuntu/legal/scripts/clone_laws.sh
/home/ubuntu/legal/scripts/clone_laws.sh
```

- [ ] **Step 3: cross_ref.py 작성 — 조문 상호참조 파서**

`backend/rag/__init__.py`: 빈 파일

```python
import re


def extract_cross_references(law_name: str, text: str) -> dict[str, list[str]]:
    """조문 텍스트에서 다른 조문 참조를 추출한다.

    Returns:
        {"공직선거법_제58조": ["공직선거법_제93조", ...]}
    """
    refs: dict[str, list[str]] = {}
    current_article = None

    for line in text.split("\n"):
        # 현재 조문 번호 감지: "제58조", "제58조의2" 등
        article_match = re.match(r"^#+\s*(제\d+조(?:의\d+)?)", line)
        if article_match:
            current_article = f"{law_name}__{article_match.group(1)}"
            refs[current_article] = []

        if current_article:
            # "제93조", "제58조제1항" 등의 참조 패턴
            ref_matches = re.findall(r"제(\d+)조(?:의(\d+))?", line)
            for num, sub in ref_matches:
                ref_name = f"{law_name}__제{num}조"
                if sub:
                    ref_name += f"의{sub}"
                if ref_name != current_article and ref_name not in refs[current_article]:
                    refs[current_article].append(ref_name)

    return refs
```

- [ ] **Step 4: indexer.py 작성 — 법률 & 사례 청킹**

```python
import os
import re
import json
import pickle
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import chromadb
from backend.rag.cross_ref import extract_cross_references

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
LAWS_DIR = os.path.join(DATA_DIR, "laws", "repo", "kr")
CASE_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "정치관계법_사례예시집.md",
)
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
BM25_DIR = os.path.join(DATA_DIR, "bm25_index")

LAW_DIRS = ["공직선거법", "정치자금법", "정당법", "공직선거관리규칙"]
FILE_NAMES = ["법률.md", "시행령.md", "시행규칙.md", "대통령령.md"]


def chunk_law_file(law_name: str, file_path: str) -> list[dict]:
    """법률 파일을 조문 단위로 청킹한다."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = []
    current_chapter = ""
    # 조문 단위 분할: "## 제N조" 또는 "### 제N조" 패턴
    parts = re.split(r"((?:^|\n)#{1,4}\s*제\d+조(?:의\d+)?[^\n]*)", text)

    for i in range(1, len(parts), 2):
        header = parts[i].strip()
        body = parts[i + 1] if i + 1 < len(parts) else ""

        article_match = re.search(r"제(\d+)조(?:의(\d+))?", header)
        if not article_match:
            continue

        article_num = article_match.group(1)
        article_sub = article_match.group(2)
        article_id = f"제{article_num}조"
        if article_sub:
            article_id += f"의{article_sub}"

        # 장(chapter) 추적
        chapter_match = re.search(r"제(\d+)장\s+(.+)", header + body[:200])
        if chapter_match:
            current_chapter = (
                f"제{chapter_match.group(1)}장 {chapter_match.group(2).strip()}"
            )

        full_text = (header + body).strip()
        if len(full_text) < 10:
            continue

        chunks.append(
            {
                "id": f"{law_name}__{article_id}",
                "text": full_text,
                "metadata": {
                    "law_name": law_name,
                    "article": article_id,
                    "article_num": int(article_num),
                    "chapter": current_chapter,
                    "type": "law",
                    "source_file": os.path.basename(file_path),
                },
            }
        )

    return chunks


def chunk_case_examples(file_path: str) -> list[dict]:
    """사례예시집을 사례 단위로 청킹한다."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = []
    # 사례 분할: 섹션 헤더 기반
    sections = re.split(r"(### \d+\.\s+[^\n]+|#### 📖 사례 예시)", text)

    current_section = ""
    case_idx = 0

    for section in sections:
        if re.match(r"### \d+\.", section):
            current_section = section.strip().lstrip("#").strip()
            continue
        if "사례 예시" in section:
            continue

        # 허용/금지 사례 블록 분리
        sub_blocks = re.split(
            r"(\*\*⭕ 할 수 있는 사례\*\*|\*\*❌ 할 수 없는 사례\*\*)", section
        )
        current_judgment = ""
        for block in sub_blocks:
            if "할 수 있는 사례" in block:
                current_judgment = "allowed"
                continue
            elif "할 수 없는 사례" in block:
                current_judgment = "prohibited"
                continue

            # 개별 사례: "- ✅" 또는 "- ❌" 로 시작
            cases = re.split(r"\n(?=- [✅❌])", block)
            for case in cases:
                case = case.strip()
                if len(case) < 20:
                    continue

                # 관련 조문 추출
                refs = re.findall(r"[§법]\s*(\d+)[조①-⑳]?", case)
                judgment = current_judgment
                if "✅" in case:
                    judgment = "allowed"
                elif "❌" in case:
                    judgment = "prohibited"

                if not judgment:
                    continue

                case_idx += 1
                chunks.append(
                    {
                        "id": f"case__{case_idx:04d}",
                        "text": case,
                        "metadata": {
                            "category": current_section,
                            "related_articles": json.dumps(refs),
                            "judgment": judgment,
                            "type": "case_example",
                        },
                    }
                )

    return chunks


def build_index():
    """전체 인덱스 구축: ChromaDB + BM25 + 상호참조."""
    print("=== 인덱싱 시작 ===")

    all_chunks: list[dict] = []
    all_cross_refs: dict[str, list[str]] = {}

    # 1. 법률 파일 청킹
    for law_dir in LAW_DIRS:
        law_path = os.path.join(LAWS_DIR, law_dir)
        if not os.path.isdir(law_path):
            print(f"  [SKIP] {law_dir} 디렉토리 없음")
            continue

        for fname in FILE_NAMES:
            fpath = os.path.join(law_path, fname)
            if not os.path.isfile(fpath):
                continue

            law_label = f"{law_dir}_{fname.replace('.md', '')}"
            chunks = chunk_law_file(law_label, fpath)
            all_chunks.extend(chunks)
            print(f"  [LAW] {law_label}: {len(chunks)} chunks")

            with open(fpath, "r", encoding="utf-8") as f:
                cross = extract_cross_references(law_label, f.read())
                all_cross_refs.update(cross)

    # 2. 사례예시집 청킹
    if os.path.isfile(CASE_FILE):
        case_chunks = chunk_case_examples(CASE_FILE)
        all_chunks.extend(case_chunks)
        print(f"  [CASE] 사례예시집: {len(case_chunks)} chunks")

    print(f"\n  총 {len(all_chunks)} chunks")

    # 3. ChromaDB 벡터 인덱스
    print("\n=== ChromaDB 벡터 인덱싱 ===")
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # 기존 컬렉션 삭제 후 재생성
    try:
        client.delete_collection("election_law")
    except Exception:
        pass

    embedding_model = SentenceTransformer(
        "paraphrase-multilingual-MiniLM-L12-v2"
    )

    collection = client.create_collection(
        name="election_law",
        metadata={"hnsw:space": "cosine"},
    )

    # 배치로 임베딩 & 저장
    batch_size = 100
    for i in range(0, len(all_chunks), batch_size):
        batch = all_chunks[i : i + batch_size]
        texts = [c["text"] for c in batch]
        ids = [c["id"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        embeddings = embedding_model.encode(texts).tolist()

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        print(
            f"  ChromaDB: {min(i + batch_size, len(all_chunks))}/{len(all_chunks)}"
        )

    # 4. BM25 인덱스
    print("\n=== BM25 인덱싱 ===")
    os.makedirs(BM25_DIR, exist_ok=True)
    tokenized = [c["text"].split() for c in all_chunks]
    bm25 = BM25Okapi(tokenized)

    with open(os.path.join(BM25_DIR, "bm25.pkl"), "wb") as f:
        pickle.dump(bm25, f)
    with open(os.path.join(BM25_DIR, "chunks.pkl"), "wb") as f:
        pickle.dump(all_chunks, f)

    # 5. 상호참조 인덱스
    with open(
        os.path.join(BM25_DIR, "cross_refs.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(all_cross_refs, f, ensure_ascii=False, indent=2)

    print(f"\n=== 인덱싱 완료 ===")
    print(f"  ChromaDB: {CHROMA_DIR}")
    print(f"  BM25: {BM25_DIR}")
    print(f"  상호참조: {len(all_cross_refs)} entries")


if __name__ == "__main__":
    build_index()
```

- [ ] **Step 5: 인덱싱 실행**

```bash
cd /home/ubuntu/legal && source venv/bin/activate
python3 -m backend.rag.indexer
```

Expected: 각 법률 디렉토리별 chunk 수 출력, ChromaDB/BM25 인덱스 생성 확인.

- [ ] **Step 6: 커밋**

```bash
git add scripts/ backend/rag/
git commit -m "feat: law data collection, chunking pipeline, and index builder"
```

---

### Task 5: Hybrid Retriever

**Files:**
- Create: `backend/rag/retriever.py`

- [ ] **Step 1: retriever.py 작성**

```python
import os
import json
import pickle
from sentence_transformers import SentenceTransformer
import chromadb

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
BM25_DIR = os.path.join(DATA_DIR, "bm25_index")


class HybridRetriever:
    def __init__(self):
        self.embedding_model = SentenceTransformer(
            "paraphrase-multilingual-MiniLM-L12-v2"
        )

        self.chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = self.chroma_client.get_collection("election_law")

        with open(os.path.join(BM25_DIR, "bm25.pkl"), "rb") as f:
            self.bm25 = pickle.load(f)
        with open(os.path.join(BM25_DIR, "chunks.pkl"), "rb") as f:
            self.chunks: list[dict] = pickle.load(f)
        with open(
            os.path.join(BM25_DIR, "cross_refs.json"), "r", encoding="utf-8"
        ) as f:
            self.cross_refs: dict[str, list[str]] = json.load(f)

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Hybrid search: BM25 + vector, RRF merge."""
        # BM25
        tokenized_query = query.split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        bm25_ranked = sorted(
            range(len(bm25_scores)),
            key=lambda i: bm25_scores[i],
            reverse=True,
        )[: top_k * 2]

        # Vector search
        query_embedding = self.embedding_model.encode([query]).tolist()
        vector_results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=top_k * 2,
        )

        # RRF (Reciprocal Rank Fusion)
        rrf_scores: dict[str, float] = {}
        k = 60  # RRF constant

        for rank, idx in enumerate(bm25_ranked):
            doc_id = self.chunks[idx]["id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (k + rank + 1)

        if vector_results["ids"] and vector_results["ids"][0]:
            for rank, doc_id in enumerate(vector_results["ids"][0]):
                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + 1 / (
                    k + rank + 1
                )

        # Top-k selection
        sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[
            :top_k
        ]

        # Assemble chunk data
        chunk_map = {c["id"]: c for c in self.chunks}
        results = []
        for doc_id in sorted_ids:
            if doc_id in chunk_map:
                results.append(chunk_map[doc_id])

        return results

    def expand_cross_refs(
        self, results: list[dict], max_expand: int = 5
    ) -> list[dict]:
        """검색 결과의 상호참조 조문을 추가로 가져온다."""
        existing_ids = {r["id"] for r in results}
        chunk_map = {c["id"]: c for c in self.chunks}
        expanded = []

        for result in results:
            doc_id = result["id"]
            if doc_id in self.cross_refs:
                for ref_id in self.cross_refs[doc_id]:
                    if ref_id not in existing_ids and ref_id in chunk_map:
                        expanded.append(chunk_map[ref_id])
                        existing_ids.add(ref_id)
                        if len(expanded) >= max_expand:
                            return results + expanded

        return results + expanded


# Singleton
_retriever: HybridRetriever | None = None


def get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever
```

- [ ] **Step 2: retriever 테스트**

```bash
cd /home/ubuntu/legal && source venv/bin/activate
python3 -c "
from backend.rag.retriever import get_retriever
r = get_retriever()
results = r.search('선거운동 기부행위')
for doc in results[:3]:
    print(f\"[{doc['id']}] {doc['text'][:80]}...\")
print(f'Total: {len(results)}')
"
```

Expected: 관련 법 조문 검색 결과 출력.

- [ ] **Step 3: 커밋**

```bash
git add backend/rag/retriever.py
git commit -m "feat: hybrid retriever with BM25 + vector + cross-reference expansion"
```

---

## Phase 2: LangGraph 에이전트 (Tasks 6-8)

### Task 6: 쿼리 분석기 & 에이전트 프롬프트

**Files:**
- Create: `backend/agents/__init__.py`
- Create: `backend/agents/query_analyzer.py`
- Create: `backend/agents/conservative.py`
- Create: `backend/agents/liberal.py`
- Create: `backend/agents/consensus.py`

- [ ] **Step 1: LLM 클라이언트 설정**

`backend/agents/__init__.py`:

```python
import os
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="google/gemini-2.5-flash-lite-preview-06-18",
        openai_api_key=os.environ["OPENROUTER_API_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
        streaming=True,
    )
```

- [ ] **Step 2: query_analyzer.py 작성**

```python
from langchain_core.prompts import ChatPromptTemplate
from backend.agents import get_llm

QUERY_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """당신은 한국 선거법 전문 쿼리 분석기입니다.
사용자의 질문을 분석하여 법률 검색에 적합한 검색 쿼리로 변환하세요.

사용자 모드: {mode}
- citizen: 일반 시민이 쉬운 말로 질문합니다
- candidate: 후보자/선거운동원이 구체적인 상황을 질문합니다

작업:
1. 질문의 핵심 법률 키워드를 추출하세요
2. 관련될 수 있는 법률 용어(선거운동, 기부행위, 사전선거운동 등)를 추가하세요
3. 명확한 검색 쿼리를 한국어로 작성하세요

검색 쿼리만 출력하세요. 설명 없이 쿼리만.""",
        ),
        ("human", "{question}"),
    ]
)


async def analyze_query(question: str, mode: str) -> str:
    llm = get_llm()
    chain = QUERY_ANALYSIS_PROMPT | llm
    result = await chain.ainvoke({"question": question, "mode": mode})
    return result.content.strip()
```

- [ ] **Step 3: conservative.py 작성**

```python
from langchain_core.prompts import ChatPromptTemplate

CONSERVATIVE_SYSTEM = """당신은 한국 선거법을 **엄격하게 해석하는 법률 전문가**입니다.

## 원칙
- 법 조문의 문리적, 엄격 해석을 따릅니다
- "의심스러우면 하지 마라"가 기본 입장입니다
- 위반 가능성이 조금이라도 있으면 반드시 경고합니다
- 관련 법 조문 번호를 반드시 인용합니다

## 사용자 모드: {mode}
- citizen: 쉬운 말로 설명하되 위험성을 강하게 경고하세요
- candidate: 조문 번호 명시, 판례 참조, 구체적 리스크를 분석하세요

## 검색된 관련 법 조문
{context}

## 관련 사례
{cases}

위 법 조문과 사례를 근거로 사용자의 질문에 대해 **보수적 관점**에서 답변하세요.
인용한 조문 번호를 답변 끝에 별도로 나열하세요.
"""

CONSERVATIVE_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CONSERVATIVE_SYSTEM),
        ("human", "{question}"),
    ]
)
```

- [ ] **Step 4: liberal.py 작성**

```python
from langchain_core.prompts import ChatPromptTemplate

LIBERAL_SYSTEM = """당신은 한국 선거법을 **합리적, 유연하게 해석하는 법률 전문가**입니다.

## 원칙
- 법의 취지와 목적에 기반한 합리적 해석을 따릅니다
- "법이 명시적으로 금지하지 않는 한 허용 가능성을 탐색"합니다
- 허용되는 범위와 조건을 구체적으로 안내합니다
- 관련 법 조문 번호를 반드시 인용합니다

## 사용자 모드: {mode}
- citizen: 쉬운 말로 설명하되 가능한 범위를 안내하세요
- candidate: 조문 번호 명시, 허용 범위와 조건을 상세히 설명하세요

## 검색된 관련 법 조문
{context}

## 관련 사례
{cases}

위 법 조문과 사례를 근거로 사용자의 질문에 대해 **관용적 관점**에서 답변하세요.
인용한 조문 번호를 답변 끝에 별도로 나열하세요.
"""

LIBERAL_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", LIBERAL_SYSTEM),
        ("human", "{question}"),
    ]
)
```

- [ ] **Step 5: consensus.py 작성**

```python
from langchain_core.prompts import ChatPromptTemplate

CONSENSUS_SYSTEM = """당신은 두 법률 전문가의 의견을 종합하여 **합의 결론**을 도출하는 중재자입니다.

## 보수적 해석
{conservative_opinion}

## 관용적 해석
{liberal_opinion}

## 작업
1. 두 의견의 **공통 합의점**을 정리하세요
2. **견해 차이**가 있는 부분을 명시하세요
3. 최종 **위험도 등급**을 판정하세요:
   - safe: 두 전문가 모두 합법이라고 판단
   - caution: 의견이 갈리거나 조건부 허용
   - danger: 두 전문가 모두 위반 가능성을 인정
4. 사용자에게 **구체적인 행동 권고**를 하세요

## 사용자 모드: {mode}
- citizen: 결론을 쉽고 명확하게
- candidate: 법적 근거와 조건을 상세하게

반드시 답변 첫 줄에 위험도를 다음 형식으로 표시하세요:
[RISK:safe] 또는 [RISK:caution] 또는 [RISK:danger]

그 다음 줄부터 합의 결론을 작성하세요.
인용한 조문 번호를 답변 끝에 별도로 나열하세요.
"""

CONSENSUS_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CONSENSUS_SYSTEM),
        (
            "human",
            "다음 질문에 대한 두 전문가의 의견을 종합하여 합의 결론을 도출해주세요.\n\n질문: {question}",
        ),
    ]
)
```

- [ ] **Step 6: 커밋**

```bash
git add backend/agents/
git commit -m "feat: agent prompts for conservative, liberal, and consensus roles"
```

---

### Task 7: LangGraph 워크플로우

**Files:**
- Create: `backend/agents/graph.py`

- [ ] **Step 1: graph.py 작성**

```python
import re
import random
from typing import AsyncGenerator
from dataclasses import dataclass, field
from langchain_core.messages import AIMessageChunk
from backend.agents import get_llm
from backend.agents.query_analyzer import analyze_query
from backend.agents.conservative import CONSERVATIVE_PROMPT
from backend.agents.liberal import LIBERAL_PROMPT
from backend.agents.consensus import CONSENSUS_PROMPT
from backend.rag.retriever import get_retriever


@dataclass
class StreamEvent:
    event: str
    data: dict = field(default_factory=dict)


async def run_agent_workflow(
    question: str,
    mode: str,
    conversation_id: str,
) -> AsyncGenerator[StreamEvent, None]:
    """Agent workflow execution. Yields SSE events."""
    retriever = get_retriever()
    llm = get_llm()

    # 1. Query analysis and rewrite
    search_query = await analyze_query(question, mode)

    # 2. Hybrid Retrieval
    results = retriever.search(search_query, top_k=8)

    # 3. Cross-reference expansion
    results = retriever.expand_cross_refs(results, max_expand=4)

    # Separate context: law articles vs cases
    law_context = "\n\n---\n\n".join(
        f"[{r['id']}]\n{r['text']}"
        for r in results
        if r["metadata"].get("type") == "law"
    )
    case_context = "\n\n---\n\n".join(
        f"[{r['metadata'].get('judgment', '')}] {r['text']}"
        for r in results
        if r["metadata"].get("type") == "case_example"
    )

    if not law_context:
        law_context = "(관련 법 조문을 찾지 못했습니다)"
    if not case_context:
        case_context = "(관련 사례를 찾지 못했습니다)"

    # 4. Conservative agent (streaming)
    yield StreamEvent(event="conservative_start")
    conservative_full = ""
    conservative_chain = CONSERVATIVE_PROMPT | llm
    async for chunk in conservative_chain.astream(
        {
            "question": question,
            "mode": mode,
            "context": law_context,
            "cases": case_context,
        }
    ):
        token = (
            chunk.content if isinstance(chunk, AIMessageChunk) else str(chunk)
        )
        if token:
            conservative_full += token
            yield StreamEvent(
                event="conservative_token", data={"token": token}
            )

    conservative_articles = _extract_articles(conservative_full)
    yield StreamEvent(
        event="conservative_end",
        data={"cited_articles": conservative_articles},
    )

    # 5. Liberal agent (streaming)
    yield StreamEvent(event="liberal_start")
    liberal_full = ""
    liberal_chain = LIBERAL_PROMPT | llm
    async for chunk in liberal_chain.astream(
        {
            "question": question,
            "mode": mode,
            "context": law_context,
            "cases": case_context,
        }
    ):
        token = (
            chunk.content if isinstance(chunk, AIMessageChunk) else str(chunk)
        )
        if token:
            liberal_full += token
            yield StreamEvent(
                event="liberal_token", data={"token": token}
            )

    liberal_articles = _extract_articles(liberal_full)
    yield StreamEvent(
        event="liberal_end", data={"cited_articles": liberal_articles}
    )

    # 6. Consensus agent
    consensus_chain = CONSENSUS_PROMPT | llm
    consensus_full = ""
    async for chunk in consensus_chain.astream(
        {
            "question": question,
            "mode": mode,
            "conservative_opinion": conservative_full,
            "liberal_opinion": liberal_full,
        }
    ):
        token = (
            chunk.content if isinstance(chunk, AIMessageChunk) else str(chunk)
        )
        if token:
            consensus_full += token

    # Parse risk level
    risk_level = "caution"
    risk_match = re.search(r"\[RISK:(safe|caution|danger)\]", consensus_full)
    if risk_match:
        risk_level = risk_match.group(1)
        consensus_full = consensus_full.replace(
            risk_match.group(0), ""
        ).strip()

    consensus_articles = _extract_articles(consensus_full)
    all_articles = list(
        set(conservative_articles + liberal_articles + consensus_articles)
    )

    request_feedback = random.random() < 0.3

    yield StreamEvent(
        event="consensus",
        data={
            "content": consensus_full,
            "risk_level": risk_level,
            "cited_articles": all_articles,
            "request_feedback": request_feedback,
        },
    )


def _extract_articles(text: str) -> list[str]:
    """텍스트에서 인용된 법 조문 번호를 추출한다."""
    patterns = [
        r"(공직선거법|정치자금법|정당법)\s*제(\d+)조(?:의(\d+))?",
        r"법\s*제(\d+)조(?:의(\d+))?",
        r"§(\d+)(?:[①-⑳])?",
    ]
    articles = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            groups = match.groups()
            if len(groups) == 3 and groups[0]:
                article = f"{groups[0]} 제{groups[1]}조"
                if groups[2]:
                    article += f"의{groups[2]}"
                articles.append(article)
            elif len(groups) == 2:
                articles.append(f"제{groups[0]}조")
            elif len(groups) == 1:
                articles.append(f"제{groups[0]}조")

    return list(set(articles))
```

- [ ] **Step 2: 워크플로우 단독 테스트**

```bash
cd /home/ubuntu/legal && source venv/bin/activate
python3 -c "
import asyncio
from backend.agents.graph import run_agent_workflow

async def test():
    async for event in run_agent_workflow('선거운동 기간에 지인에게 명함을 돌려도 되나요?', 'citizen', 'test'):
        print(f'[{event.event}] {str(event.data)[:100]}')

asyncio.run(test())
"
```

Expected: conservative_start, token들, conservative_end, liberal_start, ..., consensus 이벤트 출력.

- [ ] **Step 3: 커밋**

```bash
git add backend/agents/graph.py
git commit -m "feat: LangGraph agent workflow with streaming dual-agent debate"
```

---

### Task 8: Chat SSE 엔드포인트

**Files:**
- Create: `backend/routers/chat.py`
- Modify: `backend/main.py`

- [ ] **Step 1: chat.py 작성**

```python
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
```

- [ ] **Step 2: main.py에 chat 라우터 등록**

```python
from backend.routers import chat, conversations, feedback

app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(feedback.router)
```

- [ ] **Step 3: SSE 엔드투엔드 테스트**

```bash
cd /home/ubuntu/legal && source venv/bin/activate
uvicorn backend.main:app --reload --port 8000 &
sleep 3

# Create conversation
CONV_ID=$(curl -s -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"mode":"citizen"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

echo "Conv ID: $CONV_ID"

# SSE chat test
curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\":\"$CONV_ID\",\"question\":\"선거 때 지인에게 밥을 사줘도 되나요?\"}" \
  --max-time 60

kill %1
```

Expected: SSE event stream (conservative_start, conservative_token, ..., consensus).

- [ ] **Step 4: 커밋**

```bash
git add backend/routers/chat.py backend/main.py
git commit -m "feat: SSE chat endpoint with agent workflow streaming"
```

---

## Phase 3: 프론트엔드 (Tasks 9-12)

### Task 9: SvelteKit 프로젝트 초기화

**Files:**
- Create: `frontend/` (SvelteKit scaffold)
- Modify: `frontend/svelte.config.js`
- Create: `frontend/src/app.css`

- [ ] **Step 1: SvelteKit 프로젝트 생성**

```bash
cd /home/ubuntu/legal
npx sv create frontend --template minimal --types ts --no-add-ons --no-install
cd frontend
npm install
npm install -D @sveltejs/adapter-static
```

- [ ] **Step 2: svelte.config.js 수정 (static adapter)**

```javascript
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    adapter: adapter({
      pages: 'build',
      assets: 'build',
      fallback: 'index.html',
    }),
  },
};

export default config;
```

- [ ] **Step 3: vite.config.ts 백엔드 프록시 설정**

```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [sveltekit()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 4: 글로벌 스타일 (Claude 톤)**

`frontend/src/app.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

:root {
  --bg: #FAF9F6;
  --sidebar-bg: #F0EDE8;
  --accent: #DA7756;
  --accent-light: #FDF6F0;
  --text: #2D2B28;
  --text-muted: #8A8580;
  --conservative-bg: #E8E0D8;
  --liberal-bg: #EDE7DF;
  --consensus-border: #DA7756;
  --consensus-bg: #FDF6F0;
  --safe: #4A8C6F;
  --caution: #C4952A;
  --danger: #C4463A;
  --border: #E0DCD7;
  --hover: #E8E3DD;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: 'Noto Sans KR', sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 15px;
  line-height: 1.6;
}

button {
  cursor: pointer;
  border: none;
  background: none;
  font-family: inherit;
  font-size: inherit;
  color: inherit;
}

input, textarea {
  font-family: inherit;
  font-size: inherit;
  color: var(--text);
}
```

- [ ] **Step 5: 빌드 테스트**

```bash
cd /home/ubuntu/legal/frontend
npm run build 2>&1 | tail -5
# Expected: build success
```

- [ ] **Step 6: 커밋**

```bash
cd /home/ubuntu/legal
git add frontend/
git commit -m "feat: SvelteKit project init with Claude-themed styling"
```

---

### Task 10: API 클라이언트 & 스토어

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/stores/conversations.ts`
- Create: `frontend/src/lib/stores/chat.ts`

- [ ] **Step 1: api.ts 작성**

```typescript
const BASE = '';

export interface Conversation {
  id: string;
  title: string | null;
  mode: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'conservative' | 'liberal' | 'consensus';
  content: string;
  risk_level?: string;
  cited_articles?: string;
  created_at: string;
}

export async function createConversation(mode: string): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/api/conversations`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode }),
  });
  return res.json();
}

export async function listConversations(): Promise<Conversation[]> {
  const res = await fetch(`${BASE}/api/conversations`);
  return res.json();
}

export async function getConversation(
  id: string
): Promise<{ conversation: Conversation; messages: Message[] }> {
  const res = await fetch(`${BASE}/api/conversations/${id}`);
  return res.json();
}

export async function deleteConversation(id: string): Promise<void> {
  await fetch(`${BASE}/api/conversations/${id}`, { method: 'DELETE' });
}

export async function submitFeedback(data: {
  conversation_id: string;
  user_question: string;
  bot_response: string;
  risk_level: string | null;
  rating: 'up' | 'down';
}): Promise<void> {
  await fetch(`${BASE}/api/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

export interface SSECallbacks {
  onConservativeStart: () => void;
  onConservativeToken: (token: string) => void;
  onConservativeEnd: (data: { cited_articles: string[] }) => void;
  onLiberalStart: () => void;
  onLiberalToken: (token: string) => void;
  onLiberalEnd: (data: { cited_articles: string[] }) => void;
  onConsensus: (data: {
    content: string;
    risk_level: string;
    cited_articles: string[];
    request_feedback: boolean;
  }) => void;
}

export function streamChat(
  conversationId: string,
  question: string,
  callbacks: SSECallbacks
): AbortController {
  const controller = new AbortController();

  fetch(`${BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ conversation_id: conversationId, question }),
    signal: controller.signal,
  }).then(async (response) => {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      let currentEvent = '';
      for (const line of lines) {
        if (line.startsWith('event:')) {
          currentEvent = line.slice(6).trim();
        } else if (line.startsWith('data:')) {
          const dataStr = line.slice(5).trim();
          if (!dataStr) continue;
          try {
            const data = JSON.parse(dataStr);
            switch (currentEvent) {
              case 'conservative_start':
                callbacks.onConservativeStart();
                break;
              case 'conservative_token':
                callbacks.onConservativeToken(data.token);
                break;
              case 'conservative_end':
                callbacks.onConservativeEnd(data);
                break;
              case 'liberal_start':
                callbacks.onLiberalStart();
                break;
              case 'liberal_token':
                callbacks.onLiberalToken(data.token);
                break;
              case 'liberal_end':
                callbacks.onLiberalEnd(data);
                break;
              case 'consensus':
                callbacks.onConsensus(data);
                break;
            }
          } catch {
            // skip malformed JSON
          }
          currentEvent = '';
        }
      }
    }
  });

  return controller;
}
```

- [ ] **Step 2: conversations.ts 스토어 작성**

```typescript
import { writable } from 'svelte/store';
import type { Conversation } from '$lib/api';
import { listConversations } from '$lib/api';

export const conversations = writable<Conversation[]>([]);
export const activeConversationId = writable<string | null>(null);

export async function refreshConversations() {
  const list = await listConversations();
  conversations.set(list);
}
```

- [ ] **Step 3: chat.ts 스토어 작성**

```typescript
import { writable } from 'svelte/store';

export interface ChatTurn {
  question: string;
  conservative: string;
  conservativeCited: string[];
  liberal: string;
  liberalCited: string[];
  consensus: string;
  consensusCited: string[];
  riskLevel: string;
  requestFeedback: boolean;
  feedbackGiven: 'up' | 'down' | null;
}

export const chatHistory = writable<ChatTurn[]>([]);
export const currentTurn = writable<ChatTurn | null>(null);
export const isStreaming = writable(false);
export const activePhase = writable<
  'idle' | 'conservative' | 'liberal' | 'consensus'
>('idle');
export const conversationMode = writable<string | null>(null);

export function resetChat() {
  chatHistory.set([]);
  currentTurn.set(null);
  isStreaming.set(false);
  activePhase.set('idle');
  conversationMode.set(null);
}
```

- [ ] **Step 4: 커밋**

```bash
cd /home/ubuntu/legal
git add frontend/src/lib/
git commit -m "feat: API client, conversation store, and chat state management"
```

---

### Task 11: UI 컴포넌트

**Files:**
- Create: `frontend/src/lib/components/Sidebar.svelte`
- Create: `frontend/src/lib/components/ModeSelector.svelte`
- Create: `frontend/src/lib/components/AgentBox.svelte`
- Create: `frontend/src/lib/components/ConsensusBox.svelte`
- Create: `frontend/src/lib/components/FeedbackButtons.svelte`
- Create: `frontend/src/lib/components/ChatMessage.svelte`

각 컴포넌트의 코드는 Task 12의 메인 페이지와 함께 작동한다. 자세한 구현은 각 Step에서 제공.

- [ ] **Step 1: Sidebar.svelte 작성**

사이드바 컴포넌트. 날짜별 그룹핑, 대화 선택, 삭제 기능.

props: `onSelectConversation: (id: string) => void`, `onNewChat: () => void`

구현 사항:
- `groupByDate()` 함수로 오늘/어제/지난 7일/지난 30일/이전 분류
- 각 대화 항목에 hover 시 삭제 버튼 (x) 표시
- active 상태 하이라이트
- 상단에 "+ 새 대화" 버튼 (accent 색상)

스타일: sidebar-bg 배경, 260px 고정 너비, 스크롤 가능 히스토리 영역.

- [ ] **Step 2: ModeSelector.svelte 작성**

모드 선택 화면. 대화 시작 전 표시.

props: `onSelect: (mode: string) => void`

구현 사항:
- 중앙 정렬 2개 카드: "일반 시민" / "후보자/선거운동원"
- hover 시 accent 보더 + accent-light 배경
- 각 카드에 아이콘, 제목, 설명 텍스트

- [ ] **Step 3: AgentBox.svelte 작성**

에이전트 응답 박스. 보수적/관용적 공용.

props: `type: 'conservative' | 'liberal'`, `content: string`, `isActive: boolean`, `citedArticles: string[]`

구현 사항:
- type에 따라 아이콘(보수: 칭량기, 관용: 비둘기), 라벨, 배경색 변경
- isActive 일 때 펄스 애니메이션 dot 표시
- citedArticles를 태그 형태로 하단에 표시

- [ ] **Step 4: ConsensusBox.svelte 작성**

합의 결론 박스.

props: `content: string`, `riskLevel: string`, `citedArticles: string[]`

구현 사항:
- riskLevel에 따라 뱃지 색상/아이콘 변경 (safe/caution/danger)
- accent 보더 + consensus-bg 배경
- danger일 때만 "중앙선관위에 위반행위 신고" 버튼 표시 (외부 링크, 새 탭)
- 인용 조문 태그 표시

- [ ] **Step 5: FeedbackButtons.svelte 작성**

평가 버튼 컴포넌트.

props: `conversationId`, `userQuestion`, `botResponse`, `riskLevel`, `onFeedback: (rating) => void`

구현 사항:
- thumbs up/down 버튼 2개
- 클릭 시 API 호출 후 submitted 상태로 전환
- 제출 후 "감사합니다!" 텍스트 표시, 버튼 비활성화

- [ ] **Step 6: ChatMessage.svelte 작성**

한 턴의 대화를 표시하는 컴포넌트.

props: `turn: ChatTurn`, `conversationId: string`, `conservativeActive: boolean`, `liberalActive: boolean`

구현 사항:
- 사용자 질문 (흰 배경 박스)
- AgentBox 2개 (보수/관용)
- ConsensusBox (합의 결론이 있을 때만)
- FeedbackButtons (requestFeedback && feedbackGiven === null 일 때만)

- [ ] **Step 7: 커밋**

```bash
cd /home/ubuntu/legal
git add frontend/src/lib/components/
git commit -m "feat: UI components - Sidebar, ModeSelector, AgentBox, ConsensusBox, Feedback"
```

---

### Task 12: 메인 페이지 레이아웃

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`
- Modify: `frontend/src/routes/+page.svelte`

- [ ] **Step 1: +layout.svelte 작성**

```svelte
<script lang="ts">
  import '../app.css';
</script>

<slot />
```

- [ ] **Step 2: +page.svelte 작성**

메인 페이지. 전체 앱 로직이 여기에 집중.

구현 사항:
- 좌측: Sidebar (대화 이력)
- 우측: 모드 선택 OR 대화 영역
- 대화 영역: chatHistory 루프 (ChatMessage), currentTurn 스트리밍 표시
- 하단 입력창: textarea + 전송 버튼, Enter로 전송, Shift+Enter 줄바꿈
- `streamChat()` API 콜백으로 스트리밍 상태 관리
- 대화 이력 로드 시 messages를 ChatTurn으로 그룹화 (user -> conservative -> liberal -> consensus)
- 첫 메시지 시 자동 제목 설정
- onMount에서 refreshConversations()

스타일: flex 레이아웃, 100vh, 대화 영역 스크롤, 입력창 하단 고정.

- [ ] **Step 3: 프론트엔드 빌드 확인**

```bash
cd /home/ubuntu/legal/frontend
npm run build 2>&1 | tail -5
# Expected: build success
```

- [ ] **Step 4: 커밋**

```bash
cd /home/ubuntu/legal
git add frontend/src/routes/
git commit -m "feat: main page layout with chat, sidebar, and mode selection"
```

---

## Phase 4: 통합 & 완성 (Tasks 13-14)

### Task 13: FastAPI 정적 파일 서빙 통합

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: 프론트엔드 빌드 파일을 FastAPI에서 서빙**

`backend/main.py`에 추가:

```python
import os
from fastapi.staticfiles import StaticFiles

FRONTEND_BUILD = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "frontend", "build"
)

# Add after router registration, at the very end:
if os.path.isdir(FRONTEND_BUILD):
    app.mount(
        "/", StaticFiles(directory=FRONTEND_BUILD, html=True), name="frontend"
    )
```

- [ ] **Step 2: 통합 실행 테스트**

```bash
cd /home/ubuntu/legal/frontend && npm run build
cd /home/ubuntu/legal
source venv/bin/activate
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
sleep 2
curl -s http://localhost:8000/ | head -5
# Expected: HTML page output
curl -s http://localhost:8000/api/health
# Expected: {"status":"ok"}
kill %1
```

- [ ] **Step 3: 커밋**

```bash
git add backend/main.py
git commit -m "feat: serve SvelteKit build from FastAPI for single-port deployment"
```

---

### Task 14: 실행 스크립트 & 최종 확인

**Files:**
- Create: `scripts/index_laws.py`
- Create: `start.sh`

- [ ] **Step 1: index_laws.py 래퍼**

```python
#!/usr/bin/env python3
"""법률 데이터 인덱싱 실행 스크립트."""
import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 1. Clone laws
print("=== 법률 데이터 클론 ===")
subprocess.run(
    ["bash", os.path.join(ROOT, "scripts", "clone_laws.sh")], check=True
)

# 2. Index
print("\n=== 인덱싱 ===")
os.chdir(ROOT)
subprocess.run([sys.executable, "-m", "backend.rag.indexer"], check=True)

print("\n=== 완료 ===")
```

- [ ] **Step 2: start.sh 작성**

```bash
#!/bin/bash
set -e

cd /home/ubuntu/legal

# Activate venv
source venv/bin/activate

# Build frontend if needed
if [ ! -d "frontend/build" ] || [ "frontend/src" -nt "frontend/build" ]; then
    echo "=== 프론트엔드 빌드 ==="
    cd frontend && npm run build && cd ..
fi

echo "=== 서버 시작 (http://localhost:8000) ==="
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 3: 실행 권한 부여**

```bash
chmod +x /home/ubuntu/legal/scripts/index_laws.py
chmod +x /home/ubuntu/legal/start.sh
```

- [ ] **Step 4: 엔드투엔드 테스트**

```bash
cd /home/ubuntu/legal
source venv/bin/activate

# 1. Indexing (if not done)
python3 scripts/index_laws.py

# 2. Frontend build
cd frontend && npm run build && cd ..

# 3. Start server
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
sleep 3

# 4. Health check
curl -s http://localhost:8000/api/health

# 5. Create conversation, ask question
CONV_ID=$(curl -s -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"mode":"citizen"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -N -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"conversation_id\":\"$CONV_ID\",\"question\":\"선거일에 지인에게 투표 독려 문자를 보내도 되나요?\"}" \
  --max-time 60

# 6. Check conversation history
curl -s "http://localhost:8000/api/conversations/$CONV_ID" | python3 -m json.tool | head -30

kill %1
```

- [ ] **Step 5: 최종 커밋**

```bash
cd /home/ubuntu/legal
git add scripts/ start.sh
git commit -m "feat: startup script and end-to-end integration"
```
