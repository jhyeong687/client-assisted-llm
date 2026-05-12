# Phase 1B Draft Window Sweep

This run measures how draft window size changes real-model accept rate.

- draft_model: Qwen/Qwen2.5-0.5B-Instruct
- verifier_model: Qwen/Qwen2.5-1.5B-Instruct
- device: mps
- max_new_tokens: 24
- prompt_count: 3
- best_draft_window: 1
- best_weighted_accept_rate: 59.1%

## Results

| draft_window | weighted_accept_rate | accepted/token proposals | accepted/window | elapsed_s |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 59.1% | 39/66 | 0.59 | 4.42 |
| 2 | 45.4% | 39/86 | 0.89 | 2.97 |
| 4 | 29.8% | 39/131 | 1.11 | 3.23 |
| 8 | 18.9% | 39/206 | 1.34 | 4.07 |
