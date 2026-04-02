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
