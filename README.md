# Client-Assisted LLM Inference

Client-assisted LLM inference prototype for testing whether a user's laptop can participate in cloud LLM generation and reduce server-side inference cost.

The project focuses on a practical version of the idea: the client runs a smaller local draft model, proposes token IDs, and the server-side verifier model accepts or rejects those draft tokens. If the verifier accepts enough of the local draft, the cloud server can reduce expensive autoregressive generation work.

```text
prompt
  -> local draft model proposes token IDs
  -> server verifier model checks the draft
  -> accepted prefix is reused
  -> server continues when the draft diverges
```

This is related to speculative decoding, but with the draft model running on the user's machine instead of inside the same server process.

## Why This Exists

Modern laptops have increasingly capable GPUs/NPUs, but most LLM APIs still treat the client as a thin terminal:

```text
client sends prompt -> cloud GPU does all generation -> client waits
```

This repo explores a different question:

> Can client hardware do useful inference work during cloud generation, enough to reduce cloud GPU cost or latency?

This is not a wrapper for OpenAI, Claude, or Gemini pricing. Existing closed APIs generally do not expose the token-verification primitives needed for this. The target is an open model stack where the client and server protocol can be controlled.

## Current Status

Real pretrained models have been tested. The first results are mixed but useful:

| Run | Draft model | Verifier model | Weighted accept rate |
| --- | --- | --- | ---: |
| SmolLM2 smoke test | `HuggingFaceTB/SmolLM2-135M-Instruct` | `HuggingFaceTB/SmolLM2-360M-Instruct` | 35.3% |
| Qwen raw prompt | `Qwen/Qwen2.5-0.5B-Instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | 15.6% |
| Qwen chat template | `Qwen/Qwen2.5-0.5B-Instruct` | `Qwen/Qwen2.5-1.5B-Instruct` | 18.9% |
| Same-model sanity check | `SmolLM2-135M-Instruct` | `SmolLM2-135M-Instruct` | 100.0% |

The same-model sanity check reaching 100% suggests the token comparison logic is working. The early cross-model accept rates are below the rough product target of 50%+, so the next research step is testing stronger draft/verifier pairs such as Qwen 1.5B -> 3B/7B, smaller draft windows, and task-specific prompt sets.

Detailed results: [docs/phase1-results.md](docs/phase1-results.md)

## Repository Map

- [experiments/phase1_accept_rate.py](experiments/phase1_accept_rate.py): real-model accept-rate measurement
- [docs/phase1-accept-rate.md](docs/phase1-accept-rate.md): how the Phase 1 measurement works
- [docs/phase1-results.md](docs/phase1-results.md): current measured results
- [docs/protocol.md](docs/protocol.md): draft token protocol sketch
- [docs/architecture.md](docs/architecture.md): target client/server architecture
- [docs/experiment-design.md](docs/experiment-design.md): overall experiment plan
- [experiments/phase0_sweep.py](experiments/phase0_sweep.py): analytical sweep for accept rate and draft window
- [experiments/phase0_sensitivity.py](experiments/phase0_sensitivity.py): sensitivity check for local speed and network RTT

## Run Real-Model Accept Rate

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-phase1.txt
python experiments/phase1_accept_rate.py
```

The default run uses:

- draft: `HuggingFaceTB/SmolLM2-135M-Instruct`
- verifier: `HuggingFaceTB/SmolLM2-360M-Instruct`
- prompts: [examples/prompts_ko.txt](examples/prompts_ko.txt)
- output: `results/phase1_accept_rate/`

Example Qwen run:

```bash
python experiments/phase1_accept_rate.py \
  --draft-model Qwen/Qwen2.5-0.5B-Instruct \
  --verifier-model Qwen/Qwen2.5-1.5B-Instruct \
  --limit 3 \
  --draft-window 8 \
  --max-new-tokens 24 \
  --output-dir results/phase1_accept_rate_qwen_chat
```

## Method

For each prompt:

1. The draft model greedily proposes `draft_window` token IDs.
2. The verifier model runs on `context + draft_tokens`.
3. Each draft token is compared against the verifier model's greedy top-1 token at that position.
4. The accepted prefix is counted.
5. On first mismatch, the verifier token is appended and the next draft window begins.

The main metric is:

```text
accept_rate = accepted_draft_tokens / proposed_draft_tokens
```

## Early Takeaways

- The measurement pipeline works: same-model verification gives 100% accept rate.
- Very small draft models are probably too weak for reliable savings on the current Korean prompt set.
- The idea becomes interesting when accept rate approaches 50%+ and the client/server RTT is low.
- The next serious test should use a stronger same-family pair and compare draft windows 2, 4, and 8.

## Analytical Experiments

The Phase 0 scripts are not the main evidence; they are planning tools for understanding which variables matter.

```bash
python3 experiments/phase0_sweep.py
python3 experiments/phase0_sensitivity.py
```

Generated artifacts:

- `results/phase0/`
- `results/phase0b_sensitivity/`

## Next Steps

1. Run Qwen 1.5B -> Qwen 3B or 7B accept-rate measurements.
2. Sweep `draft_window` across 2, 4, and 8 for each model pair.
3. Split prompts by category: Korean explanation, code, translation, summarization.
4. Add server-only latency baseline for the verifier model.
5. Convert the accept-rate measurement into a minimal client/server protocol demo.
