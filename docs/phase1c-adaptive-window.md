# Phase 1C Adaptive Draft Window

이 실험은 고정 `draft_window` 대신 accept/reject 결과에 따라 window를 동적으로 조절합니다.

## 정책

- `min_window=1`에서 시작합니다.
- 현재 window의 draft token이 모두 accept되면 window를 2배로 키웁니다.
- mismatch가 발생하면 window를 절반으로 줄입니다.
- window는 `min_window`와 `max_window` 사이에 머뭅니다.

## 왜 필요한가

Phase 1B에서 window 1은 accept rate가 높았지만 검증 횟수가 많아질 수 있고, window 8은 검증 횟수는 줄지만 reject 낭비가 컸습니다. Adaptive window는 둘 사이의 균형을 찾기 위한 첫 시도입니다.

## 실행

```bash
python experiments/phase1c_adaptive_window.py
```

Qwen 조합:

```bash
python experiments/phase1c_adaptive_window.py \
  --draft-model Qwen/Qwen2.5-0.5B-Instruct \
  --verifier-model Qwen/Qwen2.5-1.5B-Instruct \
  --limit 3 \
  --max-new-tokens 24 \
  --output-dir results/phase1c_adaptive_window_qwen_chat
```

## 해석 기준

- window 1보다 accept rate가 낮더라도 accepted tokens/window가 높으면 제품적으로 의미가 있을 수 있습니다.
- window 8보다 rejected token 낭비가 줄면 프로토콜 개선 신호입니다.
- 네트워크 RTT가 큰 환경에서는 accepted tokens/window가 중요합니다.

