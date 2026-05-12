# Phase 1C Adaptive Draft Window

This run starts from a small draft window and grows/shrinks it based on accept behavior.

- draft_model: HuggingFaceTB/SmolLM2-135M-Instruct
- verifier_model: HuggingFaceTB/SmolLM2-360M-Instruct
- device: mps
- min_window: 1
- max_window: 8
- max_new_tokens: 32
- prompt_count: 5
- weighted_accept_rate: 55.2%
- accepted_tokens_per_window: 1.49
- total_elapsed_s: 7.52

## Per Prompt

| prompt_id | accept_rate | accepted/proposed | windows | accepted/window | elapsed_s |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 46.7% | 21/45 | 21 | 1.00 | 1.73 |
| 2 | 57.1% | 28/49 | 11 | 2.55 | 1.55 |
| 3 | 54.5% | 24/44 | 17 | 1.41 | 1.48 |
| 4 | 53.5% | 23/43 | 19 | 1.21 | 1.43 |
| 5 | 65.0% | 26/40 | 14 | 1.86 | 1.33 |
