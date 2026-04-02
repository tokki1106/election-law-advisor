import re
import random
import asyncio
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


_SENTINEL = object()


async def _stream_agent(chain, params, event_prefix: str, queue: asyncio.Queue, result_holder: list):
    """Stream a single agent's output into a shared queue."""
    full_text = ""
    await queue.put(StreamEvent(event=f"{event_prefix}_start"))
    try:
        async for chunk in chain.astream(params):
            token = chunk.content if isinstance(chunk, AIMessageChunk) else str(chunk)
            if token:
                full_text += token
                await queue.put(StreamEvent(event=f"{event_prefix}_token", data={"token": token}))
    except Exception as e:
        await queue.put(StreamEvent(event=f"{event_prefix}_token", data={"token": f"\n[오류: {e}]"}))

    articles = _extract_articles(full_text)
    await queue.put(StreamEvent(event=f"{event_prefix}_end", data={"cited_articles": articles}))
    result_holder.append(full_text)


async def run_agent_workflow(
    question: str,
    mode: str,
    conversation_id: str,
) -> AsyncGenerator[StreamEvent, None]:
    """Agent workflow execution. Yields SSE events with parallel agent streaming."""
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

    agent_params = {
        "question": question,
        "mode": mode,
        "context": law_context,
        "cases": case_context,
    }

    # 4. Run conservative + liberal agents in PARALLEL
    queue: asyncio.Queue = asyncio.Queue()
    conservative_result: list[str] = []
    liberal_result: list[str] = []

    conservative_chain = CONSERVATIVE_PROMPT | llm
    liberal_chain = LIBERAL_PROMPT | llm

    async def run_both():
        await asyncio.gather(
            _stream_agent(conservative_chain, agent_params, "conservative", queue, conservative_result),
            _stream_agent(liberal_chain, agent_params, "liberal", queue, liberal_result),
        )
        await queue.put(_SENTINEL)

    task = asyncio.create_task(run_both())

    # Yield interleaved events from both agents
    while True:
        item = await queue.get()
        if item is _SENTINEL:
            break
        yield item

    await task  # ensure no unhandled exceptions

    conservative_full = conservative_result[0] if conservative_result else ""
    liberal_full = liberal_result[0] if liberal_result else ""

    # 5. Consensus agent (needs both opinions, runs after)
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
        token = chunk.content if isinstance(chunk, AIMessageChunk) else str(chunk)
        if token:
            consensus_full += token

    # Parse risk level
    risk_level = "caution"
    risk_match = re.search(r"\[RISK:(safe|caution|danger)\]", consensus_full)
    if risk_match:
        risk_level = risk_match.group(1)
        consensus_full = consensus_full.replace(risk_match.group(0), "").strip()

    consensus_articles = _extract_articles(consensus_full)
    conservative_articles = _extract_articles(conservative_full)
    liberal_articles = _extract_articles(liberal_full)
    all_articles = list(set(conservative_articles + liberal_articles + consensus_articles))

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
