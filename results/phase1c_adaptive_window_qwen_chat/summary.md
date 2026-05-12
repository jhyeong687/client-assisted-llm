# Phase 1C Adaptive Draft Window

This run starts from a small draft window and grows/shrinks it based on accept behavior.

- draft_model: Qwen/Qwen2.5-0.5B-Instruct
- verifier_model: Qwen/Qwen2.5-1.5B-Instruct
- device: mps
- min_window: 1
- max_window: 8
- max_new_tokens: 24
- prompt_count: 3
- weighted_accept_rate: 52.7%
- accepted_tokens_per_window: 0.87
- total_elapsed_s: 4.12

## Per Prompt

| prompt_id | accept_rate | accepted/proposed | windows | accepted/window | elapsed_s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 55.6% | 15/27 | 17 | 0.88 | 1.91 |
| 2 | 35.0% | 7/20 | 15 | 0.47 | 1.05 |
| 3 | 63.0% | 17/27 | 13 | 1.31 | 1.16 |
