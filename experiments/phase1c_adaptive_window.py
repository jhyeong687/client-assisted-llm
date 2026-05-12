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


@dataclass(frozen=True)
class AdaptivePromptResult:
    prompt_id: int
    prompt: str
    generated_tokens: int
    proposed_tokens: int
    accepted_tokens: int
    rejected_tokens: int
    windows: int
    accept_rate: float
    accepted_tokens_per_window: float
    elapsed_s: float
    window_trace: str
    output_text: str


def encode_prompt(tokenizer, prompt: str, device: str, *, use_chat_template: bool):
    if use_chat_template and getattr(tokenizer, "chat_template", None):
        encoded = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            add_generation_prompt=True,
            return_tensors="pt",
        )
        return encoded.to(device)
    return tokenizer(prompt, return_tensors="pt").input_ids.to(device)


def measure_prompt_adaptive(
    *,
    prompt_id: int,
    prompt: str,
    tokenizer,
    draft_model,
    verifier_model,
    device: str,
    min_window: int,
    max_window: int,
    max_new_tokens: int,
    use_chat_template: bool,
) -> AdaptivePromptResult:
    import torch

    start = time.perf_counter()
    input_ids = encode_prompt(tokenizer, prompt, device, use_chat_template=use_chat_template)
    initial_len = input_ids.shape[1]
    current_window = min_window

    proposed_tokens = 0
    accepted_tokens = 0
    rejected_tokens = 0
    windows = 0
    trace: list[str] = []

    with torch.no_grad():
        while input_ids.shape[1] - initial_len < max_new_tokens:
            remaining = max_new_tokens - (input_ids.shape[1] - initial_len)
            draft_window = min(current_window, remaining)
            proposed = draft_tokens(tokenizer, draft_model, input_ids, draft_window=draft_window)
            if not proposed:
                break

            accepted, replacement = verify_prefix(verifier_model, input_ids, proposed)
            proposed_tokens += len(proposed)
            accepted_tokens += accepted
            rejected_tokens += len(proposed) - accepted
            windows += 1
            trace.append(f"{draft_window}:{accepted}/{len(proposed)}")

            next_tokens = proposed[:accepted]
            if accepted < len(proposed) and replacement is not None:
                next_tokens.append(replacement)

            if not next_tokens:
                break

            next_tensor = torch.tensor([next_tokens], dtype=input_ids.dtype, device=device)
            input_ids = torch.cat([input_ids, next_tensor], dim=1)

            if accepted == len(proposed):
                current_window = min(max_window, current_window * 2)
            else:
                current_window = max(min_window, current_window // 2)

            if tokenizer.eos_token_id in next_tokens:
                break

    elapsed_s = time.perf_counter() - start
    generated_tokens = input_ids.shape[1] - initial_len
    output_text = tokenizer.decode(input_ids[0, initial_len:], skip_special_tokens=True)
    accept_rate = accepted_tokens / proposed_tokens if proposed_tokens else 0.0
    accepted_tokens_per_window = accepted_tokens / windows if windows else 0.0
    return AdaptivePromptResult(
        prompt_id=prompt_id,
        prompt=prompt,
        generated_tokens=generated_tokens,
        proposed_tokens=proposed_tokens,
        accepted_tokens=accepted_tokens,
        rejected_tokens=rejected_tokens,
        windows=windows,
        accept_rate=accept_rate,
        accepted_tokens_per_window=accepted_tokens_per_window,
        elapsed_s=elapsed_s,
        window_trace=" ".join(trace),
        output_text=output_text,
    )


def summarize(results: list[AdaptivePromptResult]) -> dict[str, float | int]:
    total_proposed = sum(result.proposed_tokens for result in results)
    total_accepted = sum(result.accepted_tokens for result in results)
    total_rejected = sum(result.rejected_tokens for result in results)
    total_windows = sum(result.windows for result in results)
    return {
        "prompt_count": len(results),
        "total_proposed_tokens": total_proposed,
        "total_accepted_tokens": total_accepted,
        "total_rejected_tokens": total_rejected,
        "total_windows": total_windows,
        "weighted_accept_rate": round(total_accepted / total_proposed, 4)
        if total_proposed
        else 0.0,
        "mean_prompt_accept_rate": round(
            sum(result.accept_rate for result in results) / len(results), 4
        ),
        "accepted_tokens_per_window": round(total_accepted / total_windows, 4)
        if total_windows
        else 0.0,
        "total_elapsed_s": round(sum(result.elapsed_s for result in results), 3),
    }


def write_outputs(
    output_dir: Path,
    results: list[AdaptivePromptResult],
    summary: dict[str, float | int],
    config: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "adaptive_window.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "prompt_id",
                "generated_tokens",
                "proposed_tokens",
                "accepted_tokens",
                "rejected_tokens",
                "windows",
                "accept_rate",
                "accepted_tokens_per_window",
                "elapsed_s",
                "window_trace",
                "prompt",
                "output_text",
            ],
        )
        writer.writeheader()
        for result in results:
            writer.writerow(
                {
                    "prompt_id": result.prompt_id,
                    "generated_tokens": result.generated_tokens,
                    "proposed_tokens": result.proposed_tokens,
                    "accepted_tokens": result.accepted_tokens,
                    "rejected_tokens": result.rejected_tokens,
                    "windows": result.windows,
                    "accept_rate": round(result.accept_rate, 4),
                    "accepted_tokens_per_window": round(result.accepted_tokens_per_window, 4),
                    "elapsed_s": round(result.elapsed_s, 3),
                    "window_trace": result.window_trace,
                    "prompt": result.prompt,
                    "output_text": result.output_text,
                }
            )

    full_summary = {**config, **summary}
    (output_dir / "summary.json").write_text(
        json.dumps(full_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Phase 1C Adaptive Draft Window",
        "",
        "This run starts from a small draft window and grows/shrinks it based on accept behavior.",
        "",
        f"- draft_model: {config['draft_model']}",
        f"- verifier_model: {config['verifier_model']}",
        f"- device: {config['device']}",
        f"- min_window: {config['min_window']}",
        f"- max_window: {config['max_window']}",
        f"- max_new_tokens: {config['max_new_tokens']}",
        f"- prompt_count: {summary['prompt_count']}",
        f"- weighted_accept_rate: {float(summary['weighted_accept_rate']):.1%}",
        f"- accepted_tokens_per_window: {float(summary['accepted_tokens_per_window']):.2f}",
        f"- total_elapsed_s: {float(summary['total_elapsed_s']):.2f}",
        "",
        "## Per Prompt",
        "",
        "| prompt_id | accept_rate | accepted/proposed | windows | accepted/window | elapsed_s |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in results:
        lines.append(
            "| "
            f"{result.prompt_id} | "
            f"{result.accept_rate:.1%} | "
            f"{result.accepted_tokens}/{result.proposed_tokens} | "
            f"{result.windows} | "
            f"{result.accepted_tokens_per_window:.2f} | "
            f"{result.elapsed_s:.2f} |"
        )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run adaptive draft-window accept-rate test.")
    parser.add_argument("--draft-model", default="HuggingFaceTB/SmolLM2-135M-Instruct")
    parser.add_argument("--verifier-model", default="HuggingFaceTB/SmolLM2-360M-Instruct")
    parser.add_argument("--prompts", type=Path, default=Path("examples/prompts_ko.txt"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--min-window", type=int, default=1)
    parser.add_argument("--max-window", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--raw-prompt", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("results/phase1c_adaptive_window"))
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

    results = []
    for prompt_id, prompt in enumerate(prompts, start=1):
        result = measure_prompt_adaptive(
            prompt_id=prompt_id,
            prompt=prompt,
            tokenizer=tokenizer,
            draft_model=draft_model,
            verifier_model=verifier_model,
            device=device,
            min_window=args.min_window,
            max_window=args.max_window,
            max_new_tokens=args.max_new_tokens,
            use_chat_template=not args.raw_prompt,
        )
        print(
            f"prompt={prompt_id}: accept_rate={result.accept_rate:.1%} "
            f"accepted={result.accepted_tokens}/{result.proposed_tokens} "
            f"accepted/window={result.accepted_tokens_per_window:.2f} "
            f"elapsed={result.elapsed_s:.2f}s"
        )
        results.append(result)

    summary = summarize(results)
    write_outputs(
        args.output_dir,
        results,
        summary,
        {
            "draft_model": args.draft_model,
            "verifier_model": args.verifier_model,
            "device": device,
            "min_window": args.min_window,
            "max_window": args.max_window,
            "max_new_tokens": args.max_new_tokens,
            "use_chat_template": not args.raw_prompt,
        },
    )
    print(f"Wrote Phase 1C artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()

