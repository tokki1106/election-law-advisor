"""RAG 검색 API — 법률 조문/사례를 직접 검색."""

from fastapi import APIRouter
from backend.schemas import RAGSearchRequest, RAGSearchResponse, RAGChunk
from backend.rag.retriever import get_retriever

router = APIRouter(prefix="/api/search", tags=["검색 (RAG)"])


@router.post(
    "",
    response_model=RAGSearchResponse,
    summary="법률/사례 검색",
    description=(
        "Hybrid Retrieval(BM25 키워드 + 벡터 시맨틱)로 선거 관련 법률 조문과 사례를 검색합니다.\n\n"
        "- BM25: 법률 용어 정확 매칭\n"
        "- 벡터: 의미적 유사 조문 검색\n"
        "- RRF: 두 결과를 Reciprocal Rank Fusion으로 병합\n"
        "- 상호참조 확장: expand_refs=true 시 참조 조문 자동 추적"
    ),
)
async def search(body: RAGSearchRequest):
    retriever = get_retriever()
    results = retriever.search(body.query, top_k=body.top_k)
    if body.expand_refs:
        results = retriever.expand_cross_refs(results, max_expand=5)
    return RAGSearchResponse(
        query=body.query,
        total=len(results),
        results=[
            RAGChunk(id=r["id"], text=r["text"], metadata=r["metadata"])
            for r in results
        ],
    )


@router.get(
    "/stats",
    summary="인덱스 통계",
    description="현재 인덱싱된 법률 데이터의 통계를 반환합니다.",
)
async def stats():
    retriever = get_retriever()
    total = len(retriever.chunks)
    law_count = sum(
        1 for c in retriever.chunks if c["metadata"].get("type") == "law"
    )
    case_count = sum(
        1 for c in retriever.chunks
        if c["metadata"].get("type") == "case_example"
    )
    cross_ref_count = len(retriever.cross_refs)
    return {
        "total_chunks": total,
        "law_chunks": law_count,
        "case_example_chunks": case_count,
        "cross_references": cross_ref_count,
    }
