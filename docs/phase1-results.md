# Phase 1 Results

Phase 1 measured real pretrained model accept rate. This is the first non-toy result in the repo.

## Runs

| Run | Draft model | Verifier model | Prompts | Max new tokens | Weighted accept rate |
| --- | --- | --- | ---: | ---: | ---: |
| SmolLM2 smoke test | `HuggingFaceTB/SmolLM2-135M-Instruct` | `HuggingFaceTB/SmolLM2-360M-Instruct` | 5 | 32 | 35.3% |
| Qwen raw prompt | `Qwen/Qwen2.5-0.5B-Instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | 3 | 24 | 15.6% |
| Qwen chat template | `Qwen/Qwen2.5-0.5B-Instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | 3 | 24 | 18.9% |
| Sanity check | `HuggingFaceTB/SmolLM2-135M-Instruct` | `HuggingFaceTB/SmolLM2-135M-Instruct` | 2 | 24 | 100.0% |

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
- smaller draft window, such as 2 or 4
- prompt categories where local draft and server verifier are more likely to agree

## Result Artifacts

- `results/phase1_accept_rate_smollm2/`
- `results/phase1_accept_rate_qwen_small/`
- `results/phase1_accept_rate_qwen_chat/`
- `results/phase1_accept_rate_sanity_same_model/`

