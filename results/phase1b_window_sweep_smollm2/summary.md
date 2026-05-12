# Phase 1B Draft Window Sweep

This run measures how draft window size changes real-model accept rate.

- draft_model: HuggingFaceTB/SmolLM2-135M-Instruct
- verifier_model: HuggingFaceTB/SmolLM2-360M-Instruct
- device: mps
- max_new_tokens: 32
- prompt_count: 5
- best_draft_window: 1
- best_weighted_accept_rate: 76.2%

## Results

| draft_window | weighted_accept_rate | accepted/token proposals | accepted/window | elapsed_s |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 76.2% | 122/160 | 0.76 | 10.21 |
| 2 | 67.0% | 122/182 | 1.33 | 5.64 |
| 4 | 51.7% | 122/236 | 2.00 | 5.11 |
| 8 | 34.0% | 122/359 | 2.60 | 6.32 |
