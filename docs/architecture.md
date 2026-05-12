# Architecture

## 최종 목표 구조

```text
┌──────────────────────────┐
│ User Laptop              │
│                          │
│  Local Draft Model       │
│  - small LLM             │
│  - fast token proposal   │
│                          │
│  Client SDK              │
│  - tokenize prompt       │
│  - draft token window    │
│  - send draft to server  │
└─────────────┬────────────┘
              │
              │ draft token ids
              │
┌─────────────▼────────────┐
│ Cloud Server             │
│                          │
│  Large Verifier Model    │
│  - validate draft tokens │
│  - accept prefix         │
│  - continue on mismatch  │
│                          │
│  Metrics Collector       │
│  - server steps          │
│  - accepted tokens       │
│  - GPU active time       │
└─────────────┬────────────┘
              │
              │ accepted tokens + continuation
              │
┌─────────────▼────────────┐
│ Client                   │
│  Final response stream   │
└──────────────────────────┘
```

## 왜 기존 상용 API 위에서는 어렵나

상용 LLM API는 내부 logits, KV cache, layer activation, token verification primitive를 공개하지 않는다. 사용자는 prompt를 보내고 text/token stream을 받을 뿐이다.

따라서 이 프로젝트의 절감 대상은 OpenAI 같은 외부 API 요금이 아니라, 우리가 직접 운영하는 서버의 GPU 원가이다.

## 제품화 가능한 형태

### SDK

개발자가 앱에 붙이는 클라이언트 라이브러리이다.

```python
client = AssistedLLM(local_model="qwen2.5:3b", server_url="https://api.example.com")
response = client.generate("한국어로 speculative decoding 설명해줘")
```

### Local companion app

사용자 노트북에서 로컬 draft 모델을 관리한다.

- 모델 다운로드
- GPU/NPU 사용량 확인
- privacy 옵션
- battery saver 옵션

### Cloud verifier API

우리가 운영하는 서버 API이다.

- draft token 검증
- fallback generation
- billing
- observability

## 가장 큰 리스크

- 로컬 모델과 서버 모델의 tokenizer가 다르면 구현이 복잡해진다.
- draft accept rate가 낮으면 이득이 없다.
- 네트워크 지연이 큰 환경에서는 latency 이득이 줄어든다.
- 클라이언트 GPU가 느리면 서버가 기다리는 시간이 생긴다.
- 보안상 클라이언트가 조작한 draft를 서버가 신뢰하면 안 된다.

