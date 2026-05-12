from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from experiments.phase1_accept_rate import (
    choose_device,
    draft_tokens,
    load_model_pair,
    load_prompts,
    verify_prefix,
)
from experiments.phase1c_adaptive_window import encode_prompt


@dataclass(frozen=True)
class LatencyRun:
    strategy: str
    prompt_id: int
    generated_tokens: int
    proposed_tokens: int
    accepted_tokens: int
    rejected_tokens: int
    windows: int
    accept_rate: float
    elapsed_s: float
    draft_s: float
    verify_s: float


def parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def measure_server_only(
    *,
    prompt_id: int,
    prompt: str,
    tokenizer,
    verifier_model,
    device: str,
    max_new_tokens: int,
    use_chat_template: bool,
) -> LatencyRun:
    input_ids = encode_prompt(tokenizer, prompt, device, use_chat_template=use_chat_template)
    attention_mask = input_ids.new_ones(input_ids.shape)
    start = time.perf_counter()
    generated = verifier_model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    elapsed_s = time.perf_counter() - start
    generated_tokens = generated.shape[1] - input_ids.shape[1]
    return LatencyRun(
        strategy="server_only",
        prompt_id=prompt_id,
        generated_tokens=generated_tokens,
        proposed_tokens=0,
        accepted_tokens=0,
        rejected_tokens=0,
        windows=0,
        accept_rate=0.0,
        elapsed_s=elapsed_s,
        draft_s=0.0,
        verify_s=elapsed_s,
    )


def measure_assisted(
    *,
    strategy: str,
    prompt_id: int,
    prompt: str,
    tokenizer,
    draft_model,
    verifier_model,
    device: str,
    max_new_tokens: int,
    use_chat_template: bool,
    fixed_window: int | None,
    min_window: int,
    max_window: int,
) -> LatencyRun:
    import torch

    input_ids = encode_prompt(tokenizer, prompt, device, use_chat_template=use_chat_template)
    initial_len = input_ids.shape[1]
    current_window = fixed_window or min_window

    proposed_tokens = 0
    accepted_tokens = 0
    rejected_tokens = 0
    windows = 0
    draft_s = 0.0
    verify_s = 0.0
    start = time.perf_counter()

    with torch.no_grad():
        while input_ids.shape[1] - initial_len < max_new_tokens:
            remaining = max_new_tokens - (input_ids.shape[1] - initial_len)
            draft_window = min(current_window, remaining)

            draft_start = time.perf_counter()
            proposed = draft_tokens(tokenizer, draft_model, input_ids, draft_window=draft_window)
            draft_s += time.perf_counter() - draft_start
            if not proposed:
                break

            verify_start = time.perf_counter()
            accepted, replacement = verify_prefix(verifier_model, input_ids, proposed)
            verify_s += time.perf_counter() - verify_start

            proposed_tokens += len(proposed)
            accepted_tokens += accepted
            rejected_tokens += len(proposed) - accepted
            windows += 1

            next_tokens = proposed[:accepted]
            if accepted < len(proposed) and replacement is not None:
                next_tokens.append(replacement)
            if not next_tokens:
                break

            next_tensor = torch.tensor([next_tokens], dtype=input_ids.dtype, device=device)
            input_ids = torch.cat([input_ids, next_tensor], dim=1)

            if fixed_window is None:
                if accepted == len(proposed):
                    current_window = min(max_window, current_window * 2)
                else:
                    current_window = max(min_window, current_window // 2)

            if tokenizer.eos_token_id in next_tokens:
                break

    elapsed_s = time.perf_counter() - start
    generated_tokens = input_ids.shape[1] - initial_len
    accept_rate = accepted_tokens / proposed_tokens if proposed_tokens else 0.0
    return LatencyRun(
        strategy=strategy,
        prompt_id=prompt_id,
        generated_tokens=generated_tokens,
        proposed_tokens=proposed_tokens,
        accepted_tokens=accepted_tokens,
        rejected_tokens=rejected_tokens,
        windows=windows,
        accept_rate=accept_rate,
        elapsed_s=elapsed_s,
        draft_s=draft_s,
        verify_s=verify_s,
    )


def aggregate(rows: list[LatencyRun], *, rtt_ms_values: list[float]) -> list[dict[str, object]]:
    by_strategy: dict[str, list[LatencyRun]] = {}
    for row in rows:
        by_strategy.setdefault(row.strategy, []).append(row)

    summary_rows: list[dict[str, object]] = []
    server_elapsed = sum(row.elapsed_s for row in by_strategy["server_only"])
    for strategy, strategy_rows in by_strategy.items():
        total_elapsed = sum(row.elapsed_s for row in strategy_rows)
        total_windows = sum(row.windows for row in strategy_rows)
        total_proposed = sum(row.proposed_tokens for row in strategy_rows)
        total_accepted = sum(row.accepted_tokens for row in strategy_rows)
        for rtt_ms in rtt_ms_values:
            network_s = total_windows * rtt_ms / 1000
            effective_s = total_elapsed + network_s
            speedup = server_elapsed / effective_s if effective_s else 0.0
            summary_rows.append(
                {
                    "strategy": strategy,
                    "rtt_ms": rtt_ms,
                    "prompt_count": len(strategy_rows),
                    "elapsed_s": round(total_elapsed, 4),
                    "network_s": round(network_s, 4),
                    "effective_s": round(effective_s, 4),
                    "server_only_s": round(server_elapsed, 4),
                    "speedup_vs_server_only": round(speedup, 4),
                    "windows": total_windows,
                    "proposed_tokens": total_proposed,
                    "accepted_tokens": total_accepted,
                    "accept_rate": round(total_accepted / total_proposed, 4)
                    if total_proposed
                    else 0.0,
                    "draft_s": round(sum(row.draft_s for row in strategy_rows), 4),
                    "verify_s": round(sum(row.verify_s for row in strategy_rows), 4),
                }
            )
    return summary_rows


def write_outputs(
    *,
    output_dir: Path,
    detail_rows: list[LatencyRun],
    summary_rows: list[dict[str, object]],
    config: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "latency_detail.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "strategy",
                "prompt_id",
                "generated_tokens",
                "proposed_tokens",
                "accepted_tokens",
                "rejected_tokens",
                "windows",
                "accept_rate",
                "elapsed_s",
                "draft_s",
                "verify_s",
            ],
        )
        writer.writeheader()
        for row in detail_rows:
            writer.writerow(
                {
                    "strategy": row.strategy,
                    "prompt_id": row.prompt_id,
                    "generated_tokens": row.generated_tokens,
                    "proposed_tokens": row.proposed_tokens,
                    "accepted_tokens": row.accepted_tokens,
                    "rejected_tokens": row.rejected_tokens,
                    "windows": row.windows,
                    "accept_rate": round(row.accept_rate, 4),
                    "elapsed_s": round(row.elapsed_s, 4),
                    "draft_s": round(row.draft_s, 4),
                    "verify_s": round(row.verify_s, 4),
                }
            )

    with (output_dir / "latency_summary.csv").open("w", newline="", encoding="utf-8") as file:
        fieldnames = list(summary_rows[0].keys())
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    best = max(summary_rows, key=lambda row: float(row["speedup_vs_server_only"]))
    full_summary = {**config, "best": best, "rows": summary_rows}
    (output_dir / "summary.json").write_text(
        json.dumps(full_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Phase 2A Server-Only vs Assisted Latency",
        "",
        "이 실험은 server-only generation과 client-assisted generation의 실제 elapsed time을 비교한다.",
        "",
        f"- draft_model: {config['draft_model']}",
        f"- verifier_model: {config['verifier_model']}",
        f"- prompt_count: {config['prompt_count']}",
        f"- max_new_tokens: {config['max_new_tokens']}",
        f"- best_strategy: {best['strategy']}",
        f"- best_rtt_ms: {best['rtt_ms']}",
        f"- best_speedup: {float(best['speedup_vs_server_only']):.2f}x",
        "",
        "## Summary",
        "",
        "| strategy | RTT ms | effective_s | speedup | accept_rate | windows |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(
            "| "
            f"{row['strategy']} | "
            f"{float(row['rtt_ms']):.0f} | "
            f"{float(row['effective_s']):.2f} | "
            f"{float(row['speedup_vs_server_only']):.2f}x | "
            f"{float(row['accept_rate']):.1%} | "
            f"{row['windows']} |"
        )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare server-only and assisted latency.")
    parser.add_argument("--draft-model", default="HuggingFaceTB/SmolLM2-135M-Instruct")
    parser.add_argument("--verifier-model", default="HuggingFaceTB/SmolLM2-360M-Instruct")
    parser.add_argument("--prompts", type=Path, default=Path("examples/prompts_ko.txt"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--fixed-windows", type=parse_int_list, default=[1, 2, 4, 8])
    parser.add_argument("--adaptive-min-window", type=int, default=1)
    parser.add_argument("--adaptive-max-window", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--rtt-ms", type=parse_float_list, default=[0, 15, 60])
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--raw-prompt", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("results/phase2a_latency"))
    return parser


def main() -> None:
    args = build_parser().parse_args()

    import torch

    device = choose_device(torch) if args.device == "auto" else args.device
    prompts = load_prompts(args.prompts, args.limit)
    tokenizer, draft_model, verifier_model = load_model_pair(
        args.draft_model,
        args.verifier_model,
        device,
    )
    use_chat_template = not args.raw_prompt

    detail_rows: list[LatencyRun] = []
    for prompt_id, prompt in enumerate(prompts, start=1):
        server = measure_server_only(
            prompt_id=prompt_id,
            prompt=prompt,
            tokenizer=tokenizer,
            verifier_model=verifier_model,
            device=device,
            max_new_tokens=args.max_new_tokens,
            use_chat_template=use_chat_template,
        )
        print(f"server_only prompt={prompt_id}: elapsed={server.elapsed_s:.2f}s")
        detail_rows.append(server)

    for fixed_window in args.fixed_windows:
        for prompt_id, prompt in enumerate(prompts, start=1):
            row = measure_assisted(
                strategy=f"fixed_{fixed_window}",
                prompt_id=prompt_id,
                prompt=prompt,
                tokenizer=tokenizer,
                draft_model=draft_model,
                verifier_model=verifier_model,
                device=device,
                max_new_tokens=args.max_new_tokens,
                use_chat_template=use_chat_template,
                fixed_window=fixed_window,
                min_window=args.adaptive_min_window,
                max_window=args.adaptive_max_window,
            )
            print(
                f"fixed_{fixed_window} prompt={prompt_id}: "
                f"elapsed={row.elapsed_s:.2f}s accept={row.accept_rate:.1%} windows={row.windows}"
            )
            detail_rows.append(row)

    for prompt_id, prompt in enumerate(prompts, start=1):
        row = measure_assisted(
            strategy="adaptive",
            prompt_id=prompt_id,
            prompt=prompt,
            tokenizer=tokenizer,
            draft_model=draft_model,
            verifier_model=verifier_model,
            device=device,
            max_new_tokens=args.max_new_tokens,
            use_chat_template=use_chat_template,
            fixed_window=None,
            min_window=args.adaptive_min_window,
            max_window=args.adaptive_max_window,
        )
        print(
            f"adaptive prompt={prompt_id}: "
            f"elapsed={row.elapsed_s:.2f}s accept={row.accept_rate:.1%} windows={row.windows}"
        )
        detail_rows.append(row)

    summary_rows = aggregate(detail_rows, rtt_ms_values=args.rtt_ms)
    write_outputs(
        output_dir=args.output_dir,
        detail_rows=detail_rows,
        summary_rows=summary_rows,
        config={
            "draft_model": args.draft_model,
            "verifier_model": args.verifier_model,
            "device": device,
            "prompt_count": len(prompts),
            "max_new_tokens": args.max_new_tokens,
            "fixed_windows": args.fixed_windows,
            "rtt_ms": args.rtt_ms,
            "use_chat_template": use_chat_template,
        },
    )
    print(f"Wrote Phase 2A artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()

