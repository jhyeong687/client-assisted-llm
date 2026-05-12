# Phase 1 Real Model Plan

Phase 1의 목표는 실제 작은 로컬 모델과 큰 서버 모델을 붙이기 전에, 가장 중요한 숫자인 accept rate를 측정하는 것입니다.

## 핵심 질문

같은 프롬프트에서 작은 모델이 제안한 token id를 큰 모델이 얼마나 자주 그대로 선택하는가?

## 추천 모델 조합

첫 실험에서는 같은 계열 모델을 씁니다. tokenizer와 분포가 비슷해야 draft token이 accept될 가능성이 큽니다.

| Local draft model | Server verifier model | 이유 |
| --- | --- | --- |
| Qwen 2.5 3B | Qwen 2.5 14B | 같은 tokenizer, 좋은 한국어 성능 |
| Llama 3.2 3B | Llama 3.1 8B | 가벼운 로컬 draft 실험 가능 |
| Gemma 2 2B | Gemma 2 9B | 작은 로컬 모델 테스트에 적합 |

## 1차 구현 범위

완성형 streaming API를 만들지 않습니다. 먼저 accept rate 측정기만 만듭니다.

```text
prompt
  -> local model generates draft token ids
  -> server model computes next-token choices
  -> compare token ids
  -> write accept/reject metrics
```

## 필요한 파일

예상 추가 파일:

- `src/client_assisted_llm/tokenizer.py`
- `src/client_assisted_llm/draft_client.py`
- `src/client_assisted_llm/verifier.py`
- `experiments/phase1_accept_rate.py`

## 측정 지표

- prompt category
- draft window
- accepted tokens
- rejected tokens
- accept rate
- local draft latency
- server verify latency
- total latency
- server-only baseline latency

## 중요 구현 원칙

- text similarity가 아니라 token id equality를 봅니다.
- local model과 server model은 가능한 같은 tokenizer를 씁니다.
- 서버는 클라이언트 draft를 신뢰하지 않고 항상 검증합니다.
- mismatch가 나면 accepted prefix까지만 인정합니다.

## 최소 성공 기준

다음 중 2개 이상이면 Phase 2로 갑니다.

- 평균 accept rate 50% 이상
- 쉬운 프롬프트에서 accept rate 65% 이상
- 서버 decode/verify step 추정치 25% 이상 감소
- 품질 평가에서 server-only 대비 큰 차이가 없음

## 실패 시 대안

- 같은 계열의 더 큰 local draft model 사용
- draft window를 줄여 reject 낭비 감소
- 쉬운 task category부터 제한적으로 제품화
- speculative decoding 대신 local preprocessing, retrieval, cache 절감 방향으로 전환

