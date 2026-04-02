# 설치 가이드

## 사전 요구사항

- Python 3.12 이상
- Node.js 20 이상
- Git
- [OpenRouter API 키](api-key.md)

## 설치 단계

### 1. 저장소 클론

```bash
git clone https://github.com/tokki1106/election-law-advisor.git
cd election-law-advisor
```

### 2. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 OpenRouter API 키를 입력합니다:

```
OPENROUTER_API_KEY=sk-or-v1-여기에_본인_API_키를_입력하세요
```

API 키 발급 방법은 [API 키 설정](api-key.md) 페이지를 참고하세요.

### 3. Python 환경 설정

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 4. 프론트엔드 설치

```bash
cd frontend
npm install
npm run build
cd ..
```

### 5. 법률 데이터 인덱싱 (최초 1회)

법률 데이터를 다운로드하고 검색 인덱스를 구축합니다. 약 5분 소요됩니다.

```bash
python3 scripts/index_laws.py
```

이 과정에서 다음이 수행됩니다:

1. [legalize-kr](https://github.com/legalize-kr/legalize-kr)에서 선거 관련 법률 sparse checkout
2. 법률 텍스트를 조문 단위로 청킹
3. 사례예시집을 사례 단위로 청킹
4. ChromaDB 벡터 인덱스 구축
5. BM25 키워드 인덱스 구축
6. 조문 상호참조 인덱스 구축

### 6. 서버 시작

```bash
./start.sh
```

브라우저에서 **http://localhost:8000** 에 접속하면 서비스를 사용할 수 있습니다.

## 간편 실행 (설치 완료 후)

```bash
./start.sh
```

## 문제 해결

### 포트 충돌

8000번 포트가 이미 사용 중인 경우:

```bash
lsof -ti:8000 | xargs kill -9
./start.sh
```

### 인덱싱 오류

인덱스를 재구축하려면 기존 데이터를 삭제 후 다시 실행합니다:

```bash
rm -rf backend/data/chroma_db backend/data/bm25_index backend/data/laws
python3 scripts/index_laws.py
```
