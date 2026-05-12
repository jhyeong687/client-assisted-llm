# Phase 2A Latency Benchmark

이 실험은 accept rate가 아니라 실제 elapsed time을 비교한다.

## 비교 대상

- `server_only`: verifier model이 혼자 `max_new_tokens`를 생성한다.
- `fixed_N`: draft model이 고정 window `N`으로 token을 제안하고 verifier가 검증한다.
- `adaptive`: window 1에서 시작해 full accept 시 window를 키우고 mismatch 시 줄인다.

## 추가하는 네트워크 비용

같은 머신에서 실행하면 client/server RTT가 없으므로, 결과 요약에서는 RTT를 가정해 effective latency를 계산한다.

```text
effective_s = measured_elapsed_s + windows * RTT
```

기본 RTT 값은 `0ms, 15ms, 60ms`이다.

## 실행

```bash
python experiments/phase2a_latency_benchmark.py
```

Qwen 조합:

```bash
python experiments/phase2a_latency_benchmark.py \
  --draft-model Qwen/Qwen2.5-0.5B-Instruct \
  --verifier-model Qwen/Qwen2.5-1.5B-Instruct \
  --limit 3 \
  --max-new-tokens 24 \
  --output-dir results/phase2a_latency_qwen_chat
```

