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
CASE_FILE = os.path.join(DATA_DIR, "정치관계법_사례예시집.md")
CHROMA_DIR = os.path.join(DATA_DIR, "chroma_db")
BM25_DIR = os.path.join(DATA_DIR, "bm25_index")

LAW_DIRS = ["공직선거법", "정치자금법", "정당법", "공직선거관리규칙"]
FILE_NAMES = [
    "법률.md",
    "시행령.md",
    "시행규칙.md",
    "대통령령.md",
    "선거관리위원회규칙.md",
    "중앙선거관리위원회규칙.md",
]


def chunk_law_file(law_name: str, file_path: str) -> list[dict]:
    """법률 파일을 조문 단위로 청킹한다."""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    chunks = []
    current_chapter = ""
    seen_ids: dict[str, int] = {}
    parts = re.split(r"((?:^|\n)#{1,6}\s*제\d+조(?:의\d+)?[^\n]*)", text)

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

        chapter_match = re.search(r"제(\d+)장\s+(.+)", header + body[:200])
        if chapter_match:
            current_chapter = (
                f"제{chapter_match.group(1)}장 {chapter_match.group(2).strip()}"
            )

        full_text = (header + body).strip()
        if len(full_text) < 10:
            continue

        # Handle duplicate article IDs within same law file
        base_id = f"{law_name}__{article_id}"
        if base_id in seen_ids:
            seen_ids[base_id] += 1
            chunk_id = f"{base_id}_{seen_ids[base_id]}"
        else:
            seen_ids[base_id] = 0
            chunk_id = base_id

        chunks.append(
            {
                "id": chunk_id,
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
    sections = re.split(r"(### \d+\.\s+[^\n]+|#### 📖 사례 예시)", text)

    current_section = ""
    case_idx = 0

    for section in sections:
        if re.match(r"### \d+\.", section):
            current_section = section.strip().lstrip("#").strip()
            continue
        if "사례 예시" in section:
            continue

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

            cases = re.split(r"\n(?=- [✅❌])", block)
            for case in cases:
                case = case.strip()
                if len(case) < 20:
                    continue

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

    if not all_chunks:
        print("ERROR: No chunks found. Check law files exist.")
        return

    # 3. ChromaDB 벡터 인덱스
    print("\n=== ChromaDB 벡터 인덱싱 ===")
    os.makedirs(CHROMA_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        client.delete_collection("election_law")
    except Exception:
        pass

    embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    collection = client.create_collection(
        name="election_law",
        metadata={"hnsw:space": "cosine"},
    )

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
        print(f"  ChromaDB: {min(i + batch_size, len(all_chunks))}/{len(all_chunks)}")

    # 4. BM25 인덱스
    # Note: pickle is used here intentionally for BM25Okapi serialization,
    # which cannot be represented in JSON. The pickled files are generated
    # and consumed only by this application.
    print("\n=== BM25 인덱싱 ===")
    os.makedirs(BM25_DIR, exist_ok=True)
    tokenized = [c["text"].split() for c in all_chunks]
    bm25 = BM25Okapi(tokenized)

    with open(os.path.join(BM25_DIR, "bm25.pkl"), "wb") as f:
        pickle.dump(bm25, f)
    with open(os.path.join(BM25_DIR, "chunks.pkl"), "wb") as f:
        pickle.dump(all_chunks, f)

    # 5. 상호참조 인덱스
    with open(os.path.join(BM25_DIR, "cross_refs.json"), "w", encoding="utf-8") as f:
        json.dump(all_cross_refs, f, ensure_ascii=False, indent=2)

    print(f"\n=== 인덱싱 완료 ===")
    print(f"  ChromaDB: {CHROMA_DIR}")
    print(f"  BM25: {BM25_DIR}")
    print(f"  상호참조: {len(all_cross_refs)} entries")


if __name__ == "__main__":
    build_index()
