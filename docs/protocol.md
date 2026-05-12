# Draft Protocol v0

이 문서는 client-assisted inference를 위한 최소 프로토콜 초안이다.

## Request

```json
{
  "request_id": "req_123",
  "prompt_token_ids": [1, 2, 3],
  "draft_token_ids": [42, 51, 91, 17],
  "max_new_tokens": 256,
  "draft_window": 4,
  "client_model": "qwen2.5-3b",
  "server_model": "qwen2.5-14b"
}
```

## Response

```json
{
  "request_id": "req_123",
  "accepted_token_ids": [42, 51],
  "rejected_from_index": 2,
  "server_token_ids": [88, 19, 73],
  "metrics": {
    "accepted_tokens": 2,
    "rejected_tokens": 2,
    "server_steps": 1,
    "server_gpu_ms": 18.4
  }
}
```

## 중요한 원칙

- 서버는 클라이언트 draft를 신뢰하지 않고 항상 검증한다.
- 클라이언트와 서버는 같은 tokenizer를 써야 한다.
- 서버는 accepted prefix만 채택한다.
- mismatch 이후에는 서버가 정답 token을 생성하거나 새 draft window를 요청한다.

## MVP에서는 생략할 것

- authentication
- billing
- streaming optimization
- KV cache sharing
- multi-user scheduling
- quantization policy

