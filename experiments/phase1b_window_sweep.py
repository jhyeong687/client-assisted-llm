from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from experiments.phase1_accept_rate import (
    choose_device,
    load_model_pair,
    load_prompts,
    measure_prompt,
)


def parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def summarize_results(results) -> dict[str, float | int]:
    total_proposed = sum(result.proposed_tokens for result in results)
    total_accepted = sum(result.accepted_tokens for result in results)
    total_rejected = sum(result.rejected_tokens for result in results)
    total_windows = sum(result.windows for result in results)
    weighted_accept_rate = total_accepted / total_proposed if total_proposed else 0.0
    mean_accept_rate = sum(result.accept_rate for result in results) / len(results)
    total_elapsed_s = sum(result.elapsed_s for result in results)
    accepted_per_window = total_accepted / total_windows if total_windows else 0.0
    return {
        "prompt_count": len(results),
        "total_proposed_tokens": total_proposed,
        "total_accepted_tokens": total_accepted,
        "total_rejected_tokens": total_rejected,
        "total_windows": total_windows,
        "weighted_accept_rate": round(weighted_accept_rate, 4),
        "mean_prompt_accept_rate": round(mean_accept_rate, 4),
        "accepted_tokens_per_window": round(accepted_per_window, 4),
        "total_elapsed_s": round(total_elapsed_s, 3),
    }


def write_sweep_outputs(
    output_dir: Path,
    rows: list[dict[str, object]],
    per_prompt_rows: list[dict[str, object]],
    config: dict[str, object],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "window_sweep.csv").open("w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "draft_window",
            "prompt_count",
            "total_proposed_tokens",
            "total_accepted_tokens",
            "total_rejected_tokens",
            "total_windows",
            "weighted_accept_rate",
            "mean_prompt_accept_rate",
            "accepted_tokens_per_window",
            "total_elapsed_s",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with (output_dir / "per_prompt.csv").open("w", newline="", encoding="utf-8") as file:
        fieldnames = [
            "draft_window",
            "prompt_id",
            "proposed_tokens",
            "accepted_tokens",
            "rejected_tokens",
            "windows",
            "accept_rate",
            "elapsed_s",
            "prompt",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(per_prompt_rows)

    best = max(rows, key=lambda row: float(row["weighted_accept_rate"]))
    summary = {
        **config,
        "best_draft_window": best["draft_window"],
        "best_weighted_accept_rate": best["weighted_accept_rate"],
        "rows": rows,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Phase 1B Draft Window Sweep",
        "",
        "This run measures how draft window size changes real-model accept rate.",
        "",
        f"- draft_model: {config['draft_model']}",
        f"- verifier_model: {config['verifier_model']}",
        f"- device: {config['device']}",
        f"- max_new_tokens: {config['max_new_tokens']}",
        f"- prompt_count: {config['prompt_count']}",
        f"- best_draft_window: {best['draft_window']}",
        f"- best_weighted_accept_rate: {float(best['weighted_accept_rate']):.1%}",
        "",
        "## Results",
        "",
        "| draft_window | weighted_accept_rate | accepted/token proposals | accepted/window | elapsed_s |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['draft_window']} | "
            f"{float(row['weighted_accept_rate']):.1%} | "
            f"{row['total_accepted_tokens']}/{row['total_proposed_tokens']} | "
            f"{float(row['accepted_tokens_per_window']):.2f} | "
            f"{float(row['total_elapsed_s']):.2f} |"
        )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sweep draft_window for real-model accept rate.")
    parser.add_argument("--draft-model", default="HuggingFaceTB/SmolLM2-135M-Instruct")
    parser.add_argument("--verifier-model", default="HuggingFaceTB/SmolLM2-360M-Instruct")
    parser.add_argument("--prompts", type=Path, default=Path("examples/prompts_ko.txt"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--windows", type=parse_int_list, default=[1, 2, 4, 8])
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--raw-prompt", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("results/phase1b_window_sweep"))
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

    rows = []
    per_prompt_rows = []
    for draft_window in args.windows:
        results = []
        for prompt_id, prompt in enumerate(prompts, start=1):
            result = measure_prompt(
                prompt_id=prompt_id,
                prompt=prompt,
                tokenizer=tokenizer,
                draft_model=draft_model,
                verifier_model=verifier_model,
                device=device,
                draft_window=draft_window,
                max_new_tokens=args.max_new_tokens,
                use_chat_template=not args.raw_prompt,
            )
            print(
                f"window={draft_window} prompt={prompt_id}: "
                f"accept_rate={result.accept_rate:.1%} "
                f"accepted={result.accepted_tokens}/{result.proposed_tokens} "
                f"elapsed={result.elapsed_s:.2f}s"
            )
            results.append(result)
            per_prompt_rows.append(
                {
                    "draft_window": draft_window,
                    "prompt_id": prompt_id,
                    "proposed_tokens": result.proposed_tokens,
                    "accepted_tokens": result.accepted_tokens,
                    "rejected_tokens": result.rejected_tokens,
                    "windows": result.windows,
                    "accept_rate": round(result.accept_rate, 4),
                    "elapsed_s": round(result.elapsed_s, 3),
                    "prompt": prompt,
                }
            )

        rows.append({"draft_window": draft_window, **summarize_results(results)})

    write_sweep_outputs(
        args.output_dir,
        rows,
        per_prompt_rows,
        {
            "draft_model": args.draft_model,
            "verifier_model": args.verifier_model,
            "device": device,
            "max_new_tokens": args.max_new_tokens,
            "prompt_count": len(prompts),
            "use_chat_template": not args.raw_prompt,
            "windows": args.windows,
        },
    )
    print(f"Wrote Phase 1B artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()

