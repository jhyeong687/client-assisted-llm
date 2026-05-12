# Experiment Design

## 질문

사용자 노트북이 만든 draft token을 서버 LLM이 검증하는 구조가 서버 GPU 원가를 줄일 수 있는가?

## 가설

### H1: 서버 decode step 감소

로컬 draft token의 accept rate가 충분히 높으면, 서버가 토큰을 하나씩 생성하는 baseline보다 더 적은 서버 decode step으로 같은 길이의 응답을 만들 수 있다.

### H2: 비용 절감 가능성

직접 운영하는 LLM 서버에서는 비용이 토큰 가격이 아니라 GPU 점유 시간과 throughput에서 나오므로, 서버 decode step 감소는 원가 절감으로 이어질 수 있다.

### H3: 네트워크 지연이 변수다

클라이언트와 서버가 draft와 검증 결과를 자주 주고받으면 latency 이득이 사라질 수 있다. draft window를 너무 작게 잡으면 왕복 지연이 커지고, 너무 크게 잡으면 reject 이후 낭비가 커진다.

## 비교군

### A. Server-only baseline

큰 서버 모델이 혼자 모든 토큰을 autoregressive decoding으로 생성한다.

측정:

- total latency
- server decode steps
- server GPU active time
- output quality

### B. Client-assisted speculative path

로컬 작은 모델이 draft token `k`개를 만들고, 서버 큰 모델이 한 번에 검증한다.

측정:

- total latency
- local draft time
- server verify steps
- accepted tokens
- rejected tokens
- accept rate
- server GPU active time
- output quality

## 주요 변수

- `draft_window`: 한 번에 로컬이 제안하는 token 수
- `accept_rate`: 서버가 draft token을 받아들이는 비율
- local draft speed
- server verify speed
- network round-trip latency
- prompt category
- local model size
- server model size

## 프롬프트 세트

처음에는 20개 정도면 충분하다.

- 짧은 한국어 설명 질문
- 긴 문서 요약
- 간단한 코드 생성
- 복잡한 코드 생성
- 번역
- 이메일 작성
- 추론형 질문
- 사실 확인이 필요한 질문

## 1차 성공 기준

다음 중 2개 이상을 만족하면 구현을 계속한다.

- server-only 대비 서버 decode step 25% 이상 감소
- end-to-end latency 15% 이상 감소
- accept rate 50% 이상
- 사람이 봤을 때 답변 품질 차이가 작음

## 1차 실패 기준

다음 중 하나라도 강하면 방향을 바꾼다.

- accept rate가 대부분 30% 이하
- 네트워크 왕복 때문에 latency가 더 느림
- 서버 GPU time이 줄지 않음
- 초안 검증을 위해 필요한 서버 연산이 baseline과 거의 같음

## 단계별 실험

### Phase 0: 시뮬레이션

실제 모델 없이 accept rate, draft window, 네트워크 지연이 이론적으로 어떤 영향을 주는지 확인한다.

이 단계의 시뮬레이션은 실제 transformer verifier 비용을 정확히 모델링하지 않는다. 낙관적인 toy model로 보고, 다음 단계에서 실제 GPU 측정으로 반드시 교정한다.

### Phase 1: 로컬 draft

Ollama 또는 llama.cpp로 작은 모델을 붙인다.

추천 후보:

- Qwen 2.5 1.5B/3B
- Gemma 2 2B
- Llama 3.2 1B/3B

### Phase 2: 서버 verifier

vLLM 또는 llama.cpp server로 큰 모델을 붙인다.

추천 후보:

- Qwen 2.5 7B/14B
- Llama 3.1 8B
- Mistral 계열

### Phase 3: 실제 speculative decoding

draft token ids를 서버로 보내고 서버가 accept/reject한다.

### Phase 4: 제품 판단

서버 원가 절감이 분명하면 SDK, 로컬 앱, 서버 API 형태로 확장한다.
