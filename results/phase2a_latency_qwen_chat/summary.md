# Phase 2A Server-Only vs Assisted Latency

이 실험은 server-only generation과 client-assisted generation의 실제 elapsed time을 비교한다.

- draft_model: Qwen/Qwen2.5-0.5B-Instruct
- verifier_model: Qwen/Qwen2.5-1.5B-Instruct
- prompt_count: 3
- max_new_tokens: 24
- best_strategy: server_only
- best_rtt_ms: 0.0
- best_speedup: 1.00x

## Summary

| strategy | RTT ms | effective_s | speedup | accept_rate | windows |
| --- | ---: | ---: | ---: | ---: | ---: |
| server_only | 0 | 1.83 | 1.00x | 0.0% | 0 |
| server_only | 15 | 1.83 | 1.00x | 0.0% | 0 |
| server_only | 60 | 1.83 | 1.00x | 0.0% | 0 |
| fixed_1 | 0 | 4.29 | 0.43x | 59.1% | 66 |
| fixed_1 | 15 | 5.28 | 0.35x | 59.1% | 66 |
| fixed_1 | 60 | 8.25 | 0.22x | 59.1% | 66 |
| fixed_2 | 0 | 3.15 | 0.58x | 45.4% | 44 |
| fixed_2 | 15 | 3.81 | 0.48x | 45.4% | 44 |
| fixed_2 | 60 | 5.79 | 0.32x | 45.4% | 44 |
| fixed_4 | 0 | 3.27 | 0.56x | 29.8% | 35 |
| fixed_4 | 15 | 3.80 | 0.48x | 29.8% | 35 |
| fixed_4 | 60 | 5.37 | 0.34x | 29.8% | 35 |
| fixed_8 | 0 | 3.80 | 0.48x | 18.9% | 29 |
| fixed_8 | 15 | 4.23 | 0.43x | 18.9% | 29 |
| fixed_8 | 60 | 5.54 | 0.33x | 18.9% | 29 |
| adaptive | 0 | 2.67 | 0.69x | 52.7% | 45 |
| adaptive | 15 | 3.34 | 0.55x | 52.7% | 45 |
| adaptive | 60 | 5.37 | 0.34x | 52.7% | 45 |
