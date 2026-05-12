# Phase 1 Accept Rate Summary

This is a real-model measurement, not the Phase 0 toy simulation.

- draft_model: HuggingFaceTB/SmolLM2-135M-Instruct
- verifier_model: HuggingFaceTB/SmolLM2-360M-Instruct
- device: mps
- prompt_count: 5
- draft_window: 8
- max_new_tokens: 32
- weighted_accept_rate: 35.3%
- mean_prompt_accept_rate: 37.6%
- total_elapsed_s: 7.581

## Per Prompt

- prompt_id=1, accept_rate=27.1%, accepted=23/85, elapsed_s=1.79
- prompt_id=2, accept_rate=23.9%, accepted=21/88, elapsed_s=2.03
- prompt_id=3, accept_rate=52.0%, accepted=26/50, elapsed_s=1.17
- prompt_id=4, accept_rate=45.6%, accepted=26/57, elapsed_s=1.28
- prompt_id=5, accept_rate=39.7%, accepted=25/63, elapsed_s=1.31
