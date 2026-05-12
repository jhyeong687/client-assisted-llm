# Client-Assisted LLM Inference

로컬 노트북 GPU/CPU가 클라우드 LLM 추론에 실제로 참여해서 서버 GPU 원가를 줄일 수 있는지 검증하는 실험 repo입니다.

## 핵심 아이디어

기존 API는 사용자의 노트북을 단순 터미널처럼 씁니다.

```text
prompt -> cloud GPU -> response
```

이 프로젝트는 사용자의 로컬 모델이 먼저 draft token을 만들고, 서버의 큰 모델이 여러 draft token을 한 번에 검증하는 구조를 실험합니다.

```text
prompt
  -> local small model drafts tokens
  -> cloud large model verifies draft tokens
  -> accepted tokens reduce server autoregressive work
```

이 방식은 client-side speculative decoding에 가깝습니다. OpenAI, Claude, Gemini 같은 기존 상용 API 비용을 직접 줄이는 방식이 아니라, 우리가 직접 운영하는 오픈소스 LLM 서버의 GPU 원가를 낮출 수 있는지 보는 실험입니다.

## 첫 번째 목표

다음 문장이 참인지 측정합니다.

> 로컬 작은 모델의 draft token이 서버 큰 모델에 충분히 많이 accept되면, 서버 GPU forward step과 latency를 줄일 수 있다.

## 현재 포함된 것

- 실험 설계 문서: [docs/experiment-design.md](docs/experiment-design.md)
- 시스템 구조 초안: [docs/architecture.md](docs/architecture.md)
- 프로토콜 초안: [docs/protocol.md](docs/protocol.md)
- Phase 0B 민감도 실험: [docs/phase0b-sensitivity.md](docs/phase0b-sensitivity.md)
- Phase 1 실제 모델 계획: [docs/phase1-real-model-plan.md](docs/phase1-real-model-plan.md)
- 첫 단계 시뮬레이터: [src/client_assisted_llm/simulate.py](src/client_assisted_llm/simulate.py)
- Phase 0 sweep runner: [experiments/phase0_sweep.py](experiments/phase0_sweep.py)
- Phase 0B sensitivity runner: [experiments/phase0_sensitivity.py](experiments/phase0_sensitivity.py)

주의: 현재 시뮬레이터는 실제 transformer 연산을 재현하지 않는 낙관적 toy model입니다. 첫 목적은 "어떤 accept rate와 draft window에서 가능성이 생기는가"를 빠르게 감 잡는 것입니다.

## 빠른 실행

Python 3.10 이상에서 실행합니다.

```bash
python3 -m src.client_assisted_llm.simulate --target-tokens 256 --draft-window 8 --accept-rate 0.65
```

여러 조건을 비교하려면:

```bash
python3 -m src.client_assisted_llm.simulate --sweep
```

CSV와 SVG 그래프를 파일로 남기려면:

```bash
python3 experiments/phase0_sweep.py
```

결과는 기본적으로 `results/phase0/`에 생성됩니다.

```text
results/phase0/sweep.csv
results/phase0/latency_reduction.svg
results/phase0/server_step_reduction.svg
results/phase0/summary.md
```

로컬 draft 속도와 네트워크 RTT 민감도를 보려면:

```bash
python3 experiments/phase0_sensitivity.py
```

결과는 기본적으로 `results/phase0b_sensitivity/`에 생성됩니다.

## 마일스톤

1. 시뮬레이션으로 draft window와 accept rate의 의미 이해
2. 로컬 draft 모델 연결: Ollama 또는 llama.cpp
3. 서버 verifier 연결: vLLM 기반 오픈소스 큰 모델
4. 실제 prompt set으로 baseline vs assisted 비교
5. 서버 GPU time, latency, accept rate, 품질을 기준으로 제품 가능성 판단

## 성공 기준

첫 실험에서는 아래 중 2개 이상을 만족하면 다음 단계로 갑니다.

- 서버 decode step 25% 이상 감소
- end-to-end latency 15% 이상 감소
- 품질 저하가 눈에 띄지 않음
- accept rate 50% 이상 유지
