# Phase 1B Draft Window Sweep

이 실험은 실제 모델에서 `draft_window` 크기가 accept rate에 어떤 영향을 주는지 측정한다.

## 왜 필요한가

Phase 1에서는 `draft_window=8`을 주로 사용했다. 하지만 draft window가 너무 크면 앞쪽에서 mismatch가 발생했을 때 뒤쪽 draft token이 모두 낭비된다.

따라서 `1, 2, 4, 8`을 비교해 다음을 확인한다.

- window를 줄이면 accept rate가 올라가는가?
- window를 줄이면 accepted token per window가 너무 낮아지는가?
- 모델 조합 문제인지, 프로토콜 파라미터 문제인지 구분할 수 있는가?

## 실행

```bash
python experiments/phase1b_window_sweep.py
```

Qwen 조합:

```bash
python experiments/phase1b_window_sweep.py \
  --draft-model Qwen/Qwen2.5-0.5B-Instruct \
  --verifier-model Qwen/Qwen2.5-1.5B-Instruct \
  --limit 3 \
  --max-new-tokens 24 \
  --output-dir results/phase1b_window_sweep_qwen_chat
```

## 해석 기준

- window를 줄여도 accept rate가 낮으면 모델 조합이 약한 것이다.
- window를 줄였을 때 accept rate가 크게 오르면 프로토콜 튜닝 여지가 있다.
- window가 너무 작으면 accept rate는 올라가도 왕복 횟수가 늘어 latency가 나빠질 수 있다.

