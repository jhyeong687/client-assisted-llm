# Client-Assisted LLM Inference

사용자의 노트북이 클라우드 LLM 추론에 실제로 참여해서 서버 GPU 비용과 지연 시간을 줄일 수 있는지 검증하는 프로토타입이다.

핵심 아이디어는 단순하다. 노트북의 작은 로컬 모델이 먼저 token ID 초안을 만들고, 서버의 더 큰 verifier 모델이 그 token들을 accept/reject한다. 서버가 충분히 많은 token을 accept하면, 클라우드가 매 token을 처음부터 생성하는 부담을 줄일 수 있다.

```text
prompt
  -> local draft model이 token ID 제안
  -> server verifier model이 draft 검증
  -> 맞은 prefix는 그대로 사용
  -> 틀린 지점부터 서버가 이어서 생성
```

이 방식은 speculative decoding과 관련이 있지만, draft model이 서버 내부가 아니라 사용자의 노트북에서 돈다는 점이 다르다.

## 왜 하는가

요즘 노트북 GPU/NPU 성능은 계속 좋아지지만, 대부분의 LLM API는 여전히 클라이언트를 얇은 터미널처럼 다룬다.

```text
client가 prompt 전송 -> cloud GPU가 전부 생성 -> client는 기다림
```

이 repo의 질문은 이것이다.

> 클라이언트 하드웨어가 cloud generation 중 실제로 유용한 추론 작업을 맡아서 서버 GPU 비용이나 latency를 줄일 수 있을까?

이 프로젝트는 OpenAI, Claude, Gemini 같은 폐쇄형 API 요금을 직접 줄이는 wrapper가 아니다. 그런 API들은 보통 token verification, logits, KV cache 같은 내부 primitive를 제공하지 않는다. 목표는 클라이언트/서버 프로토콜을 직접 제어할 수 있는 오픈 모델 스택이다.

## 현재 결과

### Latency benchmark

Phase 2A에서 server-only baseline과 assisted generation latency를 비교했다. 현재 naive assisted 구현은 server-only보다 느리다.

| 모델 조합 | best assisted | RTT 0ms speedup | RTT 15ms speedup | RTT 60ms speedup |
| --- | --- | ---: | ---: | ---: |
| SmolLM2 135M -> 360M | adaptive | 0.59x | 0.48x | 0.30x |
| Qwen2.5 0.5B -> 1.5B chat | adaptive | 0.69x | 0.55x | 0.34x |

이 결과는 중요한 현실 체크이다. accept rate는 50% 이상까지 올라왔지만, 현재 구현은 draft generation과 verifier check를 순차로 반복한다. 이 overhead 때문에 짧은 generation에서는 server-only를 이기지 못한다.

제품화하려면 다음 중 하나가 필요하다.

- verifier 서버에서 여러 draft token 검증을 더 효율적으로 처리
- draft generation과 server verification의 overlap
- 더 긴 generation에서 amortization 확인
- 더 강한 draft model로 더 큰 window에서도 높은 accept rate 유지
- 실제 서버 GPU cost 기준 측정

### Accept rate

실제 pretrained 모델로 accept rate를 측정했다. 가장 중요한 결과는 `draft_window`가 작을수록 accept rate가 크게 올라가고, adaptive window가 그 중간 균형점을 만들 수 있다는 점이다.

| 모델 조합 | window 1 | window 2 | window 4 | window 8 |
| --- | ---: | ---: | ---: | ---: |
| SmolLM2 135M -> 360M | 76.2% | 67.0% | 51.7% | 34.0% |
| Qwen2.5 0.5B -> 1.5B chat | 59.1% | 45.4% | 29.8% | 18.9% |

Adaptive window 결과:

| 모델 조합 | adaptive accept rate | accepted tokens/window |
| --- | ---: | ---: |
| SmolLM2 135M -> 360M | 55.2% | 1.49 |
| Qwen2.5 0.5B -> 1.5B chat | 52.7% | 0.87 |

이전 `draft_window=8` 기준 결과만 보면 신호가 약해 보였지만, window sweep과 adaptive window 이후에는 아이디어가 더 살아났다. 특히 window 1에서는 두 cross-model 조합 모두 50%를 넘었고, adaptive 정책도 50% 이상을 유지했다.

다만 window가 작아지면 서버 검증 round trip이 늘어난다. 따라서 실제 제품에서는 accept rate만 볼 것이 아니라 latency, 네트워크 RTT, verifier batch 효율까지 같이 봐야 한다.

측정 로직 sanity check도 통과했다.

| Run | Draft model | Verifier model | Weighted accept rate |
| --- | --- | --- | ---: |
| Same-model sanity check | `SmolLM2-135M-Instruct` | `SmolLM2-135M-Instruct` | 100.0% |

자세한 결과: [docs/phase1-results.md](docs/phase1-results.md)

## Repo 구조

- [experiments/phase1_accept_rate.py](experiments/phase1_accept_rate.py): 실제 모델 accept rate 측정기
- [experiments/phase1b_window_sweep.py](experiments/phase1b_window_sweep.py): draft window sweep 실험
- [experiments/phase1c_adaptive_window.py](experiments/phase1c_adaptive_window.py): adaptive draft window 실험
- [experiments/phase2a_latency_benchmark.py](experiments/phase2a_latency_benchmark.py): server-only vs assisted latency benchmark
- [docs/phase1-results.md](docs/phase1-results.md): 현재 실제 모델 결과
- [docs/phase1-accept-rate.md](docs/phase1-accept-rate.md): Phase 1 측정 방식
- [docs/phase1b-window-sweep.md](docs/phase1b-window-sweep.md): Phase 1B 실험 설명
- [docs/phase1c-adaptive-window.md](docs/phase1c-adaptive-window.md): Phase 1C 실험 설명
- [docs/phase2a-latency-benchmark.md](docs/phase2a-latency-benchmark.md): Phase 2A latency 실험 설명
- [docs/protocol.md](docs/protocol.md): draft token 프로토콜 초안
- [docs/architecture.md](docs/architecture.md): 목표 client/server 구조
- [docs/experiment-design.md](docs/experiment-design.md): 전체 실험 설계
- [experiments/phase0_sweep.py](experiments/phase0_sweep.py): accept rate/draft window 분석용 sweep
- [experiments/phase0_sensitivity.py](experiments/phase0_sensitivity.py): local speed/network RTT 민감도 분석

## 실행 방법

가상환경과 의존성을 준비한다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-phase1.txt
```

기본 accept rate 측정:

```bash
python experiments/phase1_accept_rate.py
```

Draft window sweep:

```bash
python experiments/phase1b_window_sweep.py
```

Adaptive draft window:

```bash
python experiments/phase1c_adaptive_window.py
```

Server-only vs assisted latency:

```bash
python experiments/phase2a_latency_benchmark.py
```

Qwen 조합 window sweep:

```bash
python experiments/phase1b_window_sweep.py \
  --draft-model Qwen/Qwen2.5-0.5B-Instruct \
  --verifier-model Qwen/Qwen2.5-1.5B-Instruct \
  --limit 3 \
  --windows 1,2,4,8 \
  --max-new-tokens 24 \
  --output-dir results/phase1b_window_sweep_qwen_chat
```

## 측정 방식

각 prompt에 대해 다음을 반복한다.

1. draft model이 `draft_window`개 token ID를 greedy로 제안한다.
2. verifier model이 `context + draft_tokens`를 forward한다.
3. 각 위치에서 verifier의 greedy top-1 token과 draft token ID를 비교한다.
4. 처음 mismatch가 나오기 전까지의 prefix만 accepted token으로 센다.
5. mismatch가 나오면 verifier token을 붙이고 다음 window로 넘어간다.

핵심 지표:

```text
accept_rate = accepted_draft_tokens / proposed_draft_tokens
```

## 지금까지의 해석

- 측정 파이프라인은 정상이다. 같은 모델로 검증하면 accept rate가 100%이다.
- `draft_window=8`은 작은 draft model에 너무 공격적일 수 있다.
- window 1~2에서는 cross-model accept rate가 의미 있게 올라간다.
- 하지만 작은 window는 검증 왕복 횟수를 늘리므로, 실제 제품은 adaptive window가 필요할 가능성이 크다.
- 첫 adaptive 정책은 두 모델 조합 모두 50% 이상의 accept rate를 유지했다.
- 현재 naive latency benchmark에서는 assisted 방식이 server-only보다 느리다.
- 다음 핵심 실험은 더 긴 generation, Qwen 1.5B -> 3B/7B, latency-aware adaptive policy이다.

## 분석용 실험

Phase 0 스크립트들은 실제 증거라기보다 어떤 변수가 중요한지 보는 분석 도구이다.

```bash
python3 experiments/phase0_sweep.py
python3 experiments/phase0_sensitivity.py
```

결과 폴더:

- `results/phase0/`
- `results/phase0b_sensitivity/`

## 다음 단계

1. 더 긴 generation 길이에서 server-only vs assisted latency 재측정
2. Qwen 1.5B -> Qwen 3B 또는 7B accept rate 측정
3. window 1/2/4/8 비교를 더 큰 모델 조합에 반복
4. prompt를 번역, 코드, 요약, 한국어 설명으로 분리
5. adaptive draft window 정책을 latency-aware 방식으로 개선
