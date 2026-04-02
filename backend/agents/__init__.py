import os
from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="google/gemini-3.1-flash-lite-preview",
        openai_api_key=os.environ["OPENROUTER_API_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
        streaming=True,
    )
