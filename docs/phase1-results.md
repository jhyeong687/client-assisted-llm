# Phase 1 Results

Phase 1 measured real pretrained model accept rate. This is the first non-toy result in the repo.

## Runs

| Run | Draft model | Verifier model | Prompts | Max new tokens | Weighted accept rate |
| --- | --- | --- | ---: | ---: | ---: |
| SmolLM2 smoke test | `HuggingFaceTB/SmolLM2-135M-Instruct` | `HuggingFaceTB/SmolLM2-360M-Instruct` | 5 | 32 | 35.3% |
| Qwen raw prompt | `Qwen/Qwen2.5-0.5B-Instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | 3 | 24 | 15.6% |
| Qwen chat template | `Qwen/Qwen2.5-0.5B-Instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | 3 | 24 | 18.9% |
| Sanity check | `HuggingFaceTB/SmolLM2-135M-Instruct` | `HuggingFaceTB/SmolLM2-135M-Instruct` | 2 | 24 | 100.0% |

## Phase 1B Draft Window Sweep

Phase 1B tested whether `draft_window=8` was causing excess rejection waste. The answer is yes: smaller windows materially improved measured accept rate.

| Model pair | Window 1 | Window 2 | Window 4 | Window 8 |
| --- | ---: | ---: | ---: | ---: |
| SmolLM2 135M -> 360M | 76.2% | 67.0% | 51.7% | 34.0% |
| Qwen 0.5B -> 1.5B chat | 59.1% | 45.4% | 29.8% | 18.9% |

This is the strongest positive signal so far. The cross-model accept rate can exceed 50% when the draft window is small. However, smaller windows increase verification round trips, so latency and network RTT still matter.

## Phase 1C Adaptive Draft Window

Phase 1C starts at window 1, doubles the window when the whole draft is accepted, and halves it on mismatch.

| Model pair | Adaptive accept rate | Accepted tokens/window | Elapsed |
| --- | ---: | ---: | ---: |
| SmolLM2 135M -> 360M | 55.2% | 1.49 | 7.52s |
| Qwen 0.5B -> 1.5B chat | 52.7% | 0.87 | 4.12s |

The simple adaptive policy is not better than fixed window 1 on raw accept rate, but it reduces some rejection waste compared with window 8 and begins to explore the latency/accept-rate tradeoff. A better next policy should be latency-aware, not only accept-rate-aware.

## Phase 2A Latency Benchmark

Phase 2A compares server-only generation against fixed-window and adaptive assisted generation. The current naive assisted path does not beat server-only latency.

| Model pair | Best assisted strategy | RTT 0ms speedup | RTT 15ms speedup | RTT 60ms speedup |
| --- | --- | ---: | ---: | ---: |
| SmolLM2 135M -> 360M | adaptive | 0.59x | 0.48x | 0.30x |
| Qwen 0.5B -> 1.5B chat | adaptive | 0.69x | 0.55x | 0.34x |

Read: accept rate alone is not enough. The prototype repeatedly runs draft generation and verifier forward passes, so short generations pay too much orchestration overhead. The next benchmark should test longer outputs and a latency-aware policy.

## Read

The measurement code appears directionally correct because the same-model sanity check reaches 100% accept rate.

The early product signal is mixed:

- SmolLM2 135M -> 360M gets a usable but not yet compelling 35.3% weighted accept rate.
- Qwen 0.5B -> 1.5B is lower than expected on the Korean prompt set, even with chat template enabled.
- Phase 0 suggested that 50%+ accept rate is where the idea starts getting interesting. These tiny models are below that threshold.

## Interpretation

This does not kill the idea. It means the first small-model pair is probably not strong enough as a draft/verifier family for Korean prompts.

Likely next tests:

- Qwen 1.5B -> Qwen 3B or 7B
- Qwen base models instead of instruct models
- English prompt subset
- adaptive draft window, starting with 1 or 2 and increasing only when accept streaks are high
- prompt categories where local draft and server verifier are more likely to agree

## Result Artifacts

- `results/phase1_accept_rate_smollm2/`
- `results/phase1_accept_rate_qwen_small/`
- `results/phase1_accept_rate_qwen_chat/`
- `results/phase1_accept_rate_sanity_same_model/`
- `results/phase1b_window_sweep_smollm2/`
- `results/phase1b_window_sweep_qwen_chat/`
- `results/phase1c_adaptive_window_smollm2/`
- `results/phase1c_adaptive_window_qwen_chat/`
- `results/phase2a_latency_smollm2/`
- `results/phase2a_latency_qwen_chat/`
