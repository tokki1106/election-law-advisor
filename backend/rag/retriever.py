import os
import json
import pickle  # noqa: S403 - used intentionally for BM25Okapi serialization
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

        # Note: pickle is used here intentionally for BM25Okapi deserialization,
        # matching the format written by indexer.py. The pickled files are
        # generated and consumed only by this application.
        with open(os.path.join(BM25_DIR, "bm25.pkl"), "rb") as f:
            self.bm25 = pickle.load(f)  # noqa: S301
        with open(os.path.join(BM25_DIR, "chunks.pkl"), "rb") as f:
            self.chunks: list[dict] = pickle.load(f)  # noqa: S301
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
