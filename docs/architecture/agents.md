# 듀얼 에이전트

## 개요

두 에이전트가 **asyncio로 병렬 실행**되며, `asyncio.Queue`를 통해 토큰이 **인터리빙**되어 SSE로 전송됩니다. 사용자는 두 에이전트의 답변이 동시에 스트리밍되는 것을 볼 수 있습니다.

## 에이전트 성격

| | 보수적 에이전트 | 관용적 에이전트 |
|---|---|---|
| 아이콘 | :scales: | :dove: |
| 관점 | 법 조문의 문리적/엄격 해석 | 법 취지와 판례 기반 합리적 해석 |
| 성향 | "의심되면 하지 마라" | "명시적 금지가 아니면 허용 가능성 탐색" |
| 시민 모드 | 쉬운 말 + 강한 경고 | 쉬운 말 + 가능한 범위 안내 |
| 후보자 모드 | 조문 번호 + 판례 + 리스크 | 조문 번호 + 허용 범위 + 조건 |

## 워크플로우 상세

```
쿼리 분석 → 검색 결과 확보
         ↓
    ┌────┴────┐
    ↓         ↓
 보수 에이전트  관용 에이전트   ← asyncio.gather (병렬)
    ↓         ↓
 asyncio.Queue  ← 토큰 인터리빙
    ↓
 SSE 스트리밍
    ↓
 합의 에이전트  ← 두 의견이 모두 완료된 후 실행
    ↓
 위험도 판정 + 최종 응답
```

## 합의 도출

합의 에이전트는 두 에이전트의 **전체 응답**을 받아서:

1. **공통 합의점**을 정리합니다
2. **견해 차이**를 명시합니다
3. **위험도 등급**을 판정합니다 (safe / caution / danger)
4. **구체적 행동 권고**를 제시합니다

위험도는 응답 첫 줄에 `[RISK:safe]`, `[RISK:caution]`, `[RISK:danger]` 형식으로 출력되며, 파싱 후 제거됩니다.

## SSE 이벤트 형식

```
event: conservative_start     ← 보수 에이전트 시작
event: conservative_token     ← 보수 토큰 (data: {"token": "..."})
event: liberal_start          ← 관용 에이전트 시작 (동시)
event: liberal_token          ← 관용 토큰
event: conservative_end       ← 보수 완료 (data: {"cited_articles": [...]})
event: liberal_end            ← 관용 완료
event: consensus              ← 합의 결론 (data: {"content": "...", "risk_level": "...", ...})
```

병렬 실행이므로 `conservative_token`과 `liberal_token`이 **교차로** 전송됩니다.
