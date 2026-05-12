from __future__ import annotations

import argparse
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SimulationConfig:
    target_tokens: int
    draft_window: int
    accept_rate: float
    local_ms_per_token: float
    server_ms_per_step: float
    network_rtt_ms: float


@dataclass(frozen=True)
class SimulationResult:
    target_tokens: int
    draft_window: int
    accept_rate: float
    server_only_ms: float
    assisted_ms: float
    server_only_steps: int
    assisted_server_steps: int
    accepted_tokens: int
    rejected_tokens: int

    @property
    def latency_delta_pct(self) -> float:
        return pct_reduction(self.server_only_ms, self.assisted_ms)

    @property
    def server_step_delta_pct(self) -> float:
        return pct_reduction(self.server_only_steps, self.assisted_server_steps)


def pct_reduction(before: float, after: float) -> float:
    if before == 0:
        return 0.0
    return (before - after) / before * 100


def simulate(config: SimulationConfig) -> SimulationResult:
    if config.target_tokens <= 0:
        raise ValueError("target_tokens must be positive")
    if config.draft_window <= 0:
        raise ValueError("draft_window must be positive")
    if not 0 <= config.accept_rate <= 1:
        raise ValueError("accept_rate must be between 0 and 1")

    server_only_steps = config.target_tokens
    server_only_ms = server_only_steps * config.server_ms_per_step

    accepted_per_window = max(1, math.floor(config.draft_window * config.accept_rate))
    windows = math.ceil(config.target_tokens / accepted_per_window)

    accepted_tokens = min(config.target_tokens, windows * accepted_per_window)
    proposed_tokens = windows * config.draft_window
    rejected_tokens = max(0, proposed_tokens - accepted_tokens)

    local_draft_ms = proposed_tokens * config.local_ms_per_token
    server_verify_ms = windows * config.server_ms_per_step
    network_ms = windows * config.network_rtt_ms
    assisted_ms = local_draft_ms + server_verify_ms + network_ms

    return SimulationResult(
        target_tokens=config.target_tokens,
        draft_window=config.draft_window,
        accept_rate=config.accept_rate,
        server_only_ms=server_only_ms,
        assisted_ms=assisted_ms,
        server_only_steps=server_only_steps,
        assisted_server_steps=windows,
        accepted_tokens=accepted_tokens,
        rejected_tokens=rejected_tokens,
    )


def print_result(result: SimulationResult) -> None:
    print("Client-assisted inference simulation")
    print("------------------------------------")
    print(f"target_tokens:          {result.target_tokens}")
    print(f"draft_window:           {result.draft_window}")
    print(f"accept_rate:            {result.accept_rate:.2f}")
    print(f"server_only_steps:      {result.server_only_steps}")
    print(f"assisted_server_steps:  {result.assisted_server_steps}")
    print(f"accepted_tokens:        {result.accepted_tokens}")
    print(f"rejected_tokens:        {result.rejected_tokens}")
    print(f"server_only_ms:         {result.server_only_ms:.1f}")
    print(f"assisted_ms:            {result.assisted_ms:.1f}")
    print(f"server_step_reduction:  {result.server_step_delta_pct:.1f}%")
    print(f"latency_reduction:      {result.latency_delta_pct:.1f}%")


def run_sweep(args: argparse.Namespace) -> None:
    print("accept_rate,draft_window,server_step_reduction_pct,latency_reduction_pct,assisted_ms")
    for accept_rate in [0.25, 0.40, 0.55, 0.70, 0.85]:
        for draft_window in [2, 4, 8, 16, 32]:
            result = simulate(
                SimulationConfig(
                    target_tokens=args.target_tokens,
                    draft_window=draft_window,
                    accept_rate=accept_rate,
                    local_ms_per_token=args.local_ms_per_token,
                    server_ms_per_step=args.server_ms_per_step,
                    network_rtt_ms=args.network_rtt_ms,
                )
            )
            print(
                f"{accept_rate:.2f},"
                f"{draft_window},"
                f"{result.server_step_delta_pct:.1f},"
                f"{result.latency_delta_pct:.1f},"
                f"{result.assisted_ms:.1f}"
            )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simulate client-assisted speculative decoding economics."
    )
    parser.add_argument("--target-tokens", type=int, default=256)
    parser.add_argument("--draft-window", type=int, default=8)
    parser.add_argument("--accept-rate", type=float, default=0.65)
    parser.add_argument("--local-ms-per-token", type=float, default=4.0)
    parser.add_argument("--server-ms-per-step", type=float, default=20.0)
    parser.add_argument("--network-rtt-ms", type=float, default=15.0)
    parser.add_argument("--sweep", action="store_true")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.sweep:
        run_sweep(args)
        return

    result = simulate(
        SimulationConfig(
            target_tokens=args.target_tokens,
            draft_window=args.draft_window,
            accept_rate=args.accept_rate,
            local_ms_per_token=args.local_ms_per_token,
            server_ms_per_step=args.server_ms_per_step,
            network_rtt_ms=args.network_rtt_ms,
        )
    )
    print_result(result)


if __name__ == "__main__":
    main()

