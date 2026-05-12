# Phase 0B Sensitivity Experiment

Phase 0은 accept rate와 draft window를 중심으로 봤다. Phase 0B는 제품화 리스크가 큰 두 변수인 로컬 draft 속도와 네트워크 왕복 지연을 본다.

## 질문

로컬 모델이 느리거나 네트워크 RTT가 커져도 client-assisted inference가 여전히 이득인가?

## 고정값

기본 실험은 아래 값을 고정한다.

- target tokens: 256
- draft window: 8
- accept rate: 0.65
- server ms per step: 20

## 변화시키는 값

- local ms/token: 1.5, 3, 4.5, 6, 8, 12
- network RTT ms: 3, 8, 15, 30, 60, 100

## 실행

```bash
python3 experiments/phase0_sensitivity.py
```

결과는 `results/phase0b_sensitivity/`에 생성된다.

## 해석

이 실험은 실제 GPU benchmark가 아니다. 다만 제품 관점에서 중요한 감각을 준다.

- 로컬 draft가 빠를수록 유리하다.
- RTT가 낮을수록 유리하다.
- draft window가 작으면 네트워크 비용을 자주 낸다.
- draft window가 크면 reject된 token 낭비가 커질 수 있다.

## 다음 의사결정

Phase 0B에서 RTT 30ms 이하, local 6ms/token 이하 조건에서 이득이 남으면 실제 모델 accept-rate 측정으로 넘어간다.
