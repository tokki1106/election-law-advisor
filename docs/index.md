# 선거법 자문 에이전트

한국 선거법(공직선거법, 정치자금법, 정당법)에 기반하여 특정 행위가 선거법에 저촉되는지 판단하고 조언하는 **대화형 AI 웹서비스**입니다.

![듀얼 에이전트 토론](images/04-dual-agents-light.png)

## 어떻게 동작하나요?

두 명의 AI 에이전트가 **동시에** 같은 질문을 분석합니다:

- **보수적 에이전트** :scales: — 법 조문을 엄격하게 해석하고, 위험 가능성을 경고합니다
- **관용적 에이전트** :dove: — 법의 취지에 기반한 합리적 해석으로 허용 범위를 탐색합니다

두 에이전트의 의견을 종합하여 **합의 결론**과 **위험도 등급**을 도출합니다.

## 주요 기능

| 기능 | 설명 |
|---|---|
| 듀얼 에이전트 토론 | 보수/관용 두 관점이 동시에 실시간 스트리밍 |
| 위험도 판정 | :green_circle: 안전 / :yellow_circle: 주의 / :red_circle: 위반가능 |
| 법률 RAG | 1,877개 법률 청크에서 Hybrid Retrieval |
| 사례 기반 | 중앙선관위 사례예시집 838건 반영 |
| 위반 신고 | 위반가능 시 중앙선관위 신고 바로가기 |
| 다크 모드 | 라이트/다크 테마 전환 |
| 대화 관리 | 이력 저장, 폴더 정리, 상단 고정 |

## 빠른 시작

```bash
git clone https://github.com/tokki1106/election-law-advisor.git
cd election-law-advisor
cp .env.example .env        # API 키 설정
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build && cd ..
python3 scripts/index_laws.py  # 최초 1회
./start.sh                     # http://localhost:8000
```

자세한 설치 방법은 [설치 가이드](getting-started/installation.md)를 참고하세요.

!!! warning "면책 조항"
    이 서비스는 **법률 자문을 대체하지 않습니다**. AI 기반 참고 자료로만 활용하시고, 정확한 법적 판단이 필요한 경우 관할 선거관리위원회(1390) 또는 법률 전문가에게 문의하세요.
