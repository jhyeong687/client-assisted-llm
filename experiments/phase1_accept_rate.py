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


@dataclass(frozen=True)
class PromptResult:
    prompt_id: int
    prompt: str
    generated_tokens: int
    proposed_tokens: int
    accepted_tokens: int
    rejected_tokens: int
    windows: int
    accept_rate: float
    elapsed_s: float
    output_text: str


def load_prompts(path: Path, limit: int | None) -> list[str]:
    prompts = [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if limit is not None:
        prompts = prompts[:limit]
    if not prompts:
        raise ValueError(f"No prompts found in {path}")
    return prompts


def choose_device(torch_module):
    if torch_module.backends.mps.is_available():
        return "mps"
    if torch_module.cuda.is_available():
        return "cuda"
    return "cpu"


def load_model_pair(draft_model_name: str, verifier_model_name: str, device: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(verifier_model_name)
    draft_tokenizer = AutoTokenizer.from_pretrained(draft_model_name)
    if tokenizer.get_vocab() != draft_tokenizer.get_vocab():
        raise ValueError(
            "Draft and verifier tokenizers have different vocabularies. "
            "Use same-family models for token-id accept rate measurement."
        )

    dtype = torch.float16 if device in {"cuda", "mps"} else torch.float32
    draft_model = AutoModelForCausalLM.from_pretrained(draft_model_name, torch_dtype=dtype)
    verifier_model = AutoModelForCausalLM.from_pretrained(verifier_model_name, torch_dtype=dtype)
    draft_model.to(device).eval()
    verifier_model.to(device).eval()
    return tokenizer, draft_model, verifier_model


def draft_tokens(tokenizer, draft_model, input_ids, *, draft_window: int):
    attention_mask = input_ids.new_ones(input_ids.shape)
    generated = draft_model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=draft_window,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id,
    )
    return generated[0, input_ids.shape[1] :].tolist()


def verify_prefix(verifier_model, input_ids, draft_token_ids: list[int]):
    import torch

    if not draft_token_ids:
        return 0, None

    device = input_ids.device
    draft_tensor = torch.tensor([draft_token_ids], dtype=input_ids.dtype, device=device)
    candidate = torch.cat([input_ids, draft_tensor], dim=1)
    attention_mask = candidate.new_ones(candidate.shape)
    context_len = input_ids.shape[1]

    with torch.no_grad():
        logits = verifier_model(candidate, attention_mask=attention_mask).logits

    accepted = 0
    first_replacement_token = None
    for index, draft_token_id in enumerate(draft_token_ids):
        prediction_position = context_len + index - 1
        verifier_token_id = int(torch.argmax(logits[0, prediction_position]).item())
        if verifier_token_id == draft_token_id:
            accepted += 1
            continue
        first_replacement_token = verifier_token_id
        break

    return accepted, first_replacement_token


def measure_prompt(
    *,
    prompt_id: int,
    prompt: str,
    tokenizer,
    draft_model,
    verifier_model,
    device: str,
    draft_window: int,
    max_new_tokens: int,
    use_chat_template: bool,
) -> PromptResult:
    import torch

    start = time.perf_counter()
    if use_chat_template and getattr(tokenizer, "chat_template", None):
        encoded = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            add_generation_prompt=True,
            return_tensors="pt",
        )
        input_ids = encoded.to(device)
    else:
        input_ids = tokenizer(prompt, return_tensors="pt").input_ids.to(device)
    initial_len = input_ids.shape[1]

    proposed_tokens = 0
    accepted_tokens = 0
    rejected_tokens = 0
    windows = 0

    with torch.no_grad():
        while input_ids.shape[1] - initial_len < max_new_tokens:
            remaining = max_new_tokens - (input_ids.shape[1] - initial_len)
            current_window = min(draft_window, remaining)
            proposed = draft_tokens(
                tokenizer,
                draft_model,
                input_ids,
                draft_window=current_window,
            )
            if not proposed:
                break

            accepted, replacement = verify_prefix(verifier_model, input_ids, proposed)
            proposed_tokens += len(proposed)
            accepted_tokens += accepted
            rejected_tokens += len(proposed) - accepted
            windows += 1

            accepted_piece = proposed[:accepted]
            next_tokens = accepted_piece
            if accepted < len(proposed) and replacement is not None:
                next_tokens.append(replacement)

            if not next_tokens:
                break

            next_tensor = torch.tensor([next_tokens], dtype=input_ids.dtype, device=device)
            input_ids = torch.cat([input_ids, next_tensor], dim=1)

            if tokenizer.eos_token_id in next_tokens:
                break

    elapsed_s = time.perf_counter() - start
    generated_tokens = input_ids.shape[1] - initial_len
    output_text = tokenizer.decode(input_ids[0, initial_len:], skip_special_tokens=True)
    accept_rate = accepted_tokens / proposed_tokens if proposed_tokens else 0.0

    return PromptResult(
        prompt_id=prompt_id,
        prompt=prompt,
        generated_tokens=generated_tokens,
        proposed_tokens=proposed_tokens,
        accepted_tokens=accepted_tokens,
        rejected_tokens=rejected_tokens,
        windows=windows,
        accept_rate=accept_rate,
        elapsed_s=elapsed_s,
        output_text=output_text,
    )


def write_outputs(output_dir: Path, results: list[PromptResult], config: dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / "accept_rate.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as file:
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
                "elapsed_s",
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
                    "elapsed_s": round(result.elapsed_s, 3),
                    "prompt": result.prompt,
                    "output_text": result.output_text,
                }
            )

    total_proposed = sum(result.proposed_tokens for result in results)
    total_accepted = sum(result.accepted_tokens for result in results)
    weighted_accept_rate = total_accepted / total_proposed if total_proposed else 0.0
    mean_accept_rate = sum(result.accept_rate for result in results) / len(results)
    summary = {
        **config,
        "prompt_count": len(results),
        "total_proposed_tokens": total_proposed,
        "total_accepted_tokens": total_accepted,
        "weighted_accept_rate": round(weighted_accept_rate, 4),
        "mean_prompt_accept_rate": round(mean_accept_rate, 4),
        "total_elapsed_s": round(sum(result.elapsed_s for result in results), 3),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Phase 1 Accept Rate Summary",
        "",
        "This is a real-model measurement, not the Phase 0 toy simulation.",
        "",
        f"- draft_model: {config['draft_model']}",
        f"- verifier_model: {config['verifier_model']}",
        f"- device: {config['device']}",
        f"- prompt_count: {len(results)}",
        f"- draft_window: {config['draft_window']}",
        f"- max_new_tokens: {config['max_new_tokens']}",
        f"- weighted_accept_rate: {weighted_accept_rate:.1%}",
        f"- mean_prompt_accept_rate: {mean_accept_rate:.1%}",
        f"- total_elapsed_s: {summary['total_elapsed_s']}",
        "",
        "## Per Prompt",
        "",
    ]
    for result in results:
        lines.append(
            "- "
            f"prompt_id={result.prompt_id}, "
            f"accept_rate={result.accept_rate:.1%}, "
            f"accepted={result.accepted_tokens}/{result.proposed_tokens}, "
            f"elapsed_s={result.elapsed_s:.2f}"
        )
    (output_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure real-model draft token accept rate.")
    parser.add_argument("--draft-model", default="HuggingFaceTB/SmolLM2-135M-Instruct")
    parser.add_argument("--verifier-model", default="HuggingFaceTB/SmolLM2-360M-Instruct")
    parser.add_argument("--prompts", type=Path, default=Path("examples/prompts_ko.txt"))
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--draft-window", type=int, default=8)
    parser.add_argument("--max-new-tokens", type=int, default=32)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "mps", "cuda"])
    parser.add_argument("--raw-prompt", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=Path("results/phase1_accept_rate"))
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
        result = measure_prompt(
            prompt_id=prompt_id,
            prompt=prompt,
            tokenizer=tokenizer,
            draft_model=draft_model,
            verifier_model=verifier_model,
            device=device,
            draft_window=args.draft_window,
            max_new_tokens=args.max_new_tokens,
            use_chat_template=not args.raw_prompt,
        )
        print(
            f"prompt {prompt_id}: accept_rate={result.accept_rate:.1%} "
            f"accepted={result.accepted_tokens}/{result.proposed_tokens} "
            f"elapsed={result.elapsed_s:.2f}s"
        )
        results.append(result)

    write_outputs(
        args.output_dir,
        results,
        {
            "draft_model": args.draft_model,
            "verifier_model": args.verifier_model,
            "device": device,
            "draft_window": args.draft_window,
            "max_new_tokens": args.max_new_tokens,
            "use_chat_template": not args.raw_prompt,
            "prompts": str(args.prompts),
            "limit": args.limit,
        },
    )
    print(f"Wrote Phase 1 artifacts to {args.output_dir}")


if __name__ == "__main__":
    main()
