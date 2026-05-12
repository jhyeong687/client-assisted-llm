# Client-Assisted LLM Inference

사용자의 노트북이 클라우드 LLM 추론에 실제로 참여해서 서버 GPU 비용과 지연 시간을 줄일 수 있는지 검증하는 프로토타입입니다.

핵심 아이디어는 단순합니다. 노트북의 작은 로컬 모델이 먼저 token ID 초안을 만들고, 서버의 더 큰 verifier 모델이 그 token들을 accept/reject합니다. 서버가 충분히 많은 token을 accept하면, 클라우드가 매 token을 처음부터 생성하는 부담을 줄일 수 있습니다.

```text
prompt
  -> local draft model이 token ID 제안
  -> server verifier model이 draft 검증
  -> 맞은 prefix는 그대로 사용
  -> 틀린 지점부터 서버가 이어서 생성
```

이 방식은 speculative decoding과 관련이 있지만, draft model이 서버 내부가 아니라 사용자의 노트북에서 돈다는 점이 다릅니다.

## 왜 하는가

요즘 노트북 GPU/NPU 성능은 계속 좋아지지만, 대부분의 LLM API는 여전히 클라이언트를 얇은 터미널처럼 다룹니다.

```text
client가 prompt 전송 -> cloud GPU가 전부 생성 -> client는 기다림
```

이 repo의 질문은 이것입니다.

> 클라이언트 하드웨어가 cloud generation 중 실제로 유용한 추론 작업을 맡아서 서버 GPU 비용이나 latency를 줄일 수 있을까?

이 프로젝트는 OpenAI, Claude, Gemini 같은 폐쇄형 API 요금을 직접 줄이는 wrapper가 아닙니다. 그런 API들은 보통 token verification, logits, KV cache 같은 내부 primitive를 제공하지 않습니다. 목표는 클라이언트/서버 프로토콜을 직접 제어할 수 있는 오픈 모델 스택입니다.

## 현재 결과

실제 pretrained 모델로 accept rate를 측정했습니다. 가장 중요한 최신 결과는 `draft_window`가 작을수록 accept rate가 크게 올라간다는 점입니다.

| 모델 조합 | window 1 | window 2 | window 4 | window 8 |
| --- | ---: | ---: | ---: | ---: |
| SmolLM2 135M -> 360M | 76.2% | 67.0% | 51.7% | 34.0% |
| Qwen2.5 0.5B -> 1.5B chat | 59.1% | 45.4% | 29.8% | 18.9% |

이전 `draft_window=8` 기준 결과만 보면 신호가 약해 보였지만, window sweep 이후에는 아이디어가 더 살아났습니다. 특히 window 1에서는 두 cross-model 조합 모두 50%를 넘었습니다.

다만 window가 작아지면 서버 검증 round trip이 늘어납니다. 따라서 실제 제품에서는 accept rate만 볼 것이 아니라 latency, 네트워크 RTT, verifier batch 효율까지 같이 봐야 합니다.

측정 로직 sanity check도 통과했습니다.

| Run | Draft model | Verifier model | Weighted accept rate |
| --- | --- | --- | ---: |
| Same-model sanity check | `SmolLM2-135M-Instruct` | `SmolLM2-135M-Instruct` | 100.0% |

자세한 결과: [docs/phase1-results.md](docs/phase1-results.md)

## Repo 구조

- [experiments/phase1_accept_rate.py](experiments/phase1_accept_rate.py): 실제 모델 accept rate 측정기
- [experiments/phase1b_window_sweep.py](experiments/phase1b_window_sweep.py): draft window sweep 실험
- [docs/phase1-results.md](docs/phase1-results.md): 현재 실제 모델 결과
- [docs/phase1-accept-rate.md](docs/phase1-accept-rate.md): Phase 1 측정 방식
- [docs/phase1b-window-sweep.md](docs/phase1b-window-sweep.md): Phase 1B 실험 설명
- [docs/protocol.md](docs/protocol.md): draft token 프로토콜 초안
- [docs/architecture.md](docs/architecture.md): 목표 client/server 구조
- [docs/experiment-design.md](docs/experiment-design.md): 전체 실험 설계
- [experiments/phase0_sweep.py](experiments/phase0_sweep.py): accept rate/draft window 분석용 sweep
- [experiments/phase0_sensitivity.py](experiments/phase0_sensitivity.py): local speed/network RTT 민감도 분석

## 실행 방법

가상환경과 의존성을 준비합니다.

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

각 prompt에 대해 다음을 반복합니다.

1. draft model이 `draft_window`개 token ID를 greedy로 제안합니다.
2. verifier model이 `context + draft_tokens`를 forward합니다.
3. 각 위치에서 verifier의 greedy top-1 token과 draft token ID를 비교합니다.
4. 처음 mismatch가 나오기 전까지의 prefix만 accepted token으로 셉니다.
5. mismatch가 나오면 verifier token을 붙이고 다음 window로 넘어갑니다.

핵심 지표:

```text
accept_rate = accepted_draft_tokens / proposed_draft_tokens
```

## 지금까지의 해석

- 측정 파이프라인은 정상입니다. 같은 모델로 검증하면 accept rate가 100%입니다.
- `draft_window=8`은 작은 draft model에 너무 공격적일 수 있습니다.
- window 1~2에서는 cross-model accept rate가 의미 있게 올라갑니다.
- 하지만 작은 window는 검증 왕복 횟수를 늘리므로, 실제 제품은 adaptive window가 필요할 가능성이 큽니다.
- 다음 핵심 실험은 Qwen 1.5B -> 3B/7B, 그리고 window 1/2/4/8 비교입니다.

## 분석용 실험

Phase 0 스크립트들은 실제 증거라기보다 어떤 변수가 중요한지 보는 분석 도구입니다.

```bash
python3 experiments/phase0_sweep.py
python3 experiments/phase0_sensitivity.py
```

결과 폴더:

- `results/phase0/`
- `results/phase0b_sensitivity/`

## 다음 단계

1. Qwen 1.5B -> Qwen 3B 또는 7B accept rate 측정
2. window 1/2/4/8 비교를 더 큰 모델 조합에 반복
3. prompt를 번역, 코드, 요약, 한국어 설명으로 분리
4. verifier server-only latency baseline 추가
5. accept streak에 따라 window를 키우고 줄이는 adaptive draft window 구현
