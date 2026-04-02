# OpenRouter API 키 설정

이 서비스는 [OpenRouter](https://openrouter.ai)를 통해 LLM 모델에 접근합니다.

## API 키 발급

1. [openrouter.ai](https://openrouter.ai) 에 접속하여 회원가입
2. [API Keys 페이지](https://openrouter.ai/keys) 에서 **Create Key** 클릭
3. 생성된 키 (`sk-or-v1-...` 형식)를 복사

## 프로젝트에 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 키를 입력합니다:

```
OPENROUTER_API_KEY=sk-or-v1-여기에_복사한_키_붙여넣기
```

## 비용

- 회원가입 시 **무료 크레딧**이 제공됩니다
- 기본 모델인 Gemini 3.1 Flash Lite는 매우 저렴합니다
- 일반적인 사용(하루 수십 건 질문)에는 큰 비용이 발생하지 않습니다

## 다른 모델 사용

`backend/agents/__init__.py`에서 모델을 변경할 수 있습니다:

```python
def get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="google/gemini-3.1-flash-lite-preview",  # 여기를 변경
        openai_api_key=os.environ["OPENROUTER_API_KEY"],
        openai_api_base="https://openrouter.ai/api/v1",
        temperature=0.3,
        streaming=True,
    )
```

[OpenRouter 모델 목록](https://openrouter.ai/models)에서 사용 가능한 모델을 확인하세요.

!!! tip "추천 모델"
    - **Gemini 3.1 Flash Lite** — 빠르고 저렴, 한국어 성능 우수 (기본값)
    - **Claude Sonnet** — 더 정교한 법률 해석이 필요한 경우
    - **GPT-4o Mini** — 균형잡힌 성능
