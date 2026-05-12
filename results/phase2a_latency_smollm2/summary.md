# Phase 2A Server-Only vs Assisted Latency

이 실험은 server-only generation과 client-assisted generation의 실제 elapsed time을 비교한다.

- draft_model: HuggingFaceTB/SmolLM2-135M-Instruct
- verifier_model: HuggingFaceTB/SmolLM2-360M-Instruct
- prompt_count: 5
- max_new_tokens: 32
- best_strategy: server_only
- best_rtt_ms: 0.0
- best_speedup: 1.00x

## Summary

| strategy | RTT ms | effective_s | speedup | accept_rate | windows |
| --- | ---: | ---: | ---: | ---: | ---: |
| server_only | 0 | 3.07 | 1.00x | 0.0% | 0 |
| server_only | 15 | 3.07 | 1.00x | 0.0% | 0 |
| server_only | 60 | 3.07 | 1.00x | 0.0% | 0 |
| fixed_1 | 0 | 8.42 | 0.36x | 76.2% | 160 |
| fixed_1 | 15 | 10.82 | 0.28x | 76.2% | 160 |
| fixed_1 | 60 | 18.02 | 0.17x | 76.2% | 160 |
| fixed_2 | 0 | 5.34 | 0.58x | 67.0% | 92 |
| fixed_2 | 15 | 6.72 | 0.46x | 67.0% | 92 |
| fixed_2 | 60 | 10.86 | 0.28x | 67.0% | 92 |
| fixed_4 | 0 | 5.32 | 0.58x | 51.7% | 61 |
| fixed_4 | 15 | 6.23 | 0.49x | 51.7% | 61 |
| fixed_4 | 60 | 8.98 | 0.34x | 51.7% | 61 |
| fixed_8 | 0 | 6.33 | 0.48x | 34.0% | 47 |
| fixed_8 | 15 | 7.04 | 0.44x | 34.0% | 47 |
| fixed_8 | 60 | 9.15 | 0.34x | 34.0% | 47 |
| adaptive | 0 | 5.18 | 0.59x | 55.2% | 82 |
| adaptive | 15 | 6.41 | 0.48x | 55.2% | 82 |
| adaptive | 60 | 10.10 | 0.30x | 55.2% | 82 |
