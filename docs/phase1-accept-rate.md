# Phase 1 Accept Rate Measurement

Phase 1은 실제 pretrained causal LM 두 개로 draft token accept rate를 측정한다.

## 기본 조합

- draft model: `HuggingFaceTB/SmolLM2-135M-Instruct`
- verifier model: `HuggingFaceTB/SmolLM2-360M-Instruct`

이 조합은 제품용 조합이 아니라 빠른 smoke test용이다. 실제 제품 가능성은 같은 계열의 더 큰 모델 조합, 예를 들어 Qwen 2.5 3B -> 14B 같은 설정에서 다시 봐야 한다.

## 실행

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-phase1.txt
python experiments/phase1_accept_rate.py
```

Instruct 모델은 기본적으로 tokenizer의 chat template을 적용한다. raw prompt를 그대로 넣고 비교하려면:

```bash
python experiments/phase1_accept_rate.py --raw-prompt
```

## 측정 방식

1. draft model이 현재 context에서 `draft_window`개 token을 greedy로 제안한다.
2. verifier model이 `context + draft_tokens`를 한 번에 forward한다.
3. 각 위치에서 verifier의 greedy top-1 token과 draft token id를 비교한다.
4. 처음 mismatch가 나오기 전까지의 prefix만 accepted token으로 센다.
5. mismatch 위치에는 verifier token을 붙이고 다음 window로 넘어간다.

## 주의

- text similarity가 아니라 token id equality를 측정한다.
- 두 모델은 같은 tokenizer vocabulary를 가져야 한다.
- 이 스크립트는 accept rate 측정기이다. 아직 실제 server GPU billing system은 아니다.
- MPS, CUDA, CPU 순서로 장치를 선택한다.
