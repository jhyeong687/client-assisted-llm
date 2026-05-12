from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.client_assisted_llm.simulate import SimulationConfig, simulate


DEFAULT_LOCAL_MS = [1.5, 3.0, 4.5, 6.0, 8.0, 12.0]
DEFAULT_NETWORK_RTT_MS = [3.0, 8.0, 15.0, 30.0, 60.0, 100.0]


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def run_sensitivity(
    *,
    target_tokens: int,
    draft_window: int,
    accept_rate: float,
    local_ms_values: list[float],
    network_rtt_values: list[float],
    server_ms_per_step: float,
) -> list[dict[str, float | int | str]]:
    rows: list[dict[str, float | int | str]] = []
    for local_ms_per_token in local_ms_values:
        for network_rtt_ms in network_rtt_values:
            config = SimulationConfig(
                target_tokens=target_tokens,
                draft_window=draft_window,
                accept_rate=accept_rate,
                local_ms_per_token=local_ms_per_token,
                server_ms_per_step=server_ms_per_step,
                network_rtt_ms=network_rtt_ms,
            )
            result = simulate(config)
            rows.append(
                {
                    **asdict(config),
                    "server_only_ms": round(result.server_only_ms, 3),
                    "assisted_ms": round(result.assisted_ms, 3),
                    "server_step_reduction_pct": round(result.server_step_delta_pct, 3),
                    "latency_reduction_pct": round(result.latency_delta_pct, 3),
                    "viable": (
                        "yes"
                        if result.latency_delta_pct >= 15
                        and result.server_step_delta_pct >= 25
                        else "no"
                    ),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def color_for_latency(value: float) -> str:
    if value < 0:
        return "#c84b4b"
    if value < 15:
        return "#d7954a"
    if value < 35:
        return "#8fa64a"
    return "#4f9a68"


def write_latency_heatmap(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    local_values = sorted({float(row["local_ms_per_token"]) for row in rows})
    network_values = sorted({float(row["network_rtt_ms"]) for row in rows})
    values = {
        (float(row["local_ms_per_token"]), float(row["network_rtt_ms"])): float(
            row["latency_reduction_pct"]
        )
        for row in rows
    }

    cell_w = 104
    cell_h = 48
    left = 124
    top = 92
    width = left + cell_w * len(network_values) + 36
    height = top + cell_h * len(local_values) + 64

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fbfbfb"/>',
        '<text x="24" y="32" font-family="Arial, sans-serif" font-size="20" '
        'font-weight="700" fill="#202124">Latency Sensitivity</text>',
        '<text x="24" y="56" font-family="Arial, sans-serif" font-size="12" '
        'fill="#5f6368">Rows: local ms/token, columns: network RTT ms</text>',
    ]

    for col, rtt in enumerate(network_values):
        x = left + col * cell_w + cell_w / 2
        parts.append(
            f'<text x="{x}" y="{top - 18}" text-anchor="middle" '
            'font-family="Arial, sans-serif" font-size="12" fill="#3c4043">'
            f"{rtt:g}ms</text>"
        )

    for row_idx, local_ms in enumerate(local_values):
        y = top + row_idx * cell_h
        parts.append(
            f'<text x="{left - 16}" y="{y + cell_h / 2 + 4}" text-anchor="end" '
            'font-family="Arial, sans-serif" font-size="12" fill="#3c4043">'
            f"{local_ms:g}</text>"
        )
        for col, rtt in enumerate(network_values):
            x = left + col * cell_w
            value = values[(local_ms, rtt)]
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - 4}" height="{cell_h - 4}" '
                f'rx="6" fill="{color_for_latency(value)}"/>'
            )
            parts.append(
                f'<text x="{x + (cell_w - 4) / 2}" y="{y + cell_h / 2 + 4}" '
                'text-anchor="middle" font-family="Arial, sans-serif" '
                'font-size="13" font-weight="700" fill="#ffffff">'
                f"{value:.1f}%</text>"
            )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_summary(path: Path, rows: list[dict[str, float | int | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    viable_rows = [row for row in rows if row["viable"] == "yes"]
    best = max(rows, key=lambda row: float(row["latency_reduction_pct"]))
    worst = min(rows, key=lambda row: float(row["latency_reduction_pct"]))

    lines = [
        "# Phase 0B Sensitivity Summary",
        "",
        "This experiment checks how fragile the toy-model benefit is when local draft speed and network RTT change.",
        "",
        "## Best Case",
        "",
        f"- local_ms_per_token: {float(best['local_ms_per_token']):.1f}",
        f"- network_rtt_ms: {float(best['network_rtt_ms']):.1f}",
        f"- latency_reduction_pct: {float(best['latency_reduction_pct']):.1f}",
        "",
        "## Worst Case",
        "",
        f"- local_ms_per_token: {float(worst['local_ms_per_token']):.1f}",
        f"- network_rtt_ms: {float(worst['network_rtt_ms']):.1f}",
        f"- latency_reduction_pct: {float(worst['latency_reduction_pct']):.1f}",
        "",
        "## Product Read",
        "",
    ]

    if viable_rows:
        lines.extend(
            [
                f"- viable_cells: {len(viable_rows)} / {len(rows)}",
                "- client-assisted inference looks most promising when the local draft model is fast and the client/server round trip is low.",
                "- high RTT hurts because every draft verification window pays the network cost.",
            ]
        )
    else:
        lines.extend(
            [
                "- viable_cells: 0",
                "- under these assumptions, the client-assisted path is not compelling enough.",
            ]
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase 0B latency sensitivity experiment.")
    parser.add_argument("--target-tokens", type=int, default=256)
    parser.add_argument("--draft-window", type=int, default=8)
    parser.add_argument("--accept-rate", type=float, default=0.65)
    parser.add_argument("--local-ms-values", type=parse_float_list, default=DEFAULT_LOCAL_MS)
    parser.add_argument("--network-rtt-values", type=parse_float_list, default=DEFAULT_NETWORK_RTT_MS)
    parser.add_argument("--server-ms-per-step", type=float, default=20.0)
    parser.add_argument("--output-dir", type=Path, default=Path("results/phase0b_sensitivity"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = run_sensitivity(
        target_tokens=args.target_tokens,
        draft_window=args.draft_window,
        accept_rate=args.accept_rate,
        local_ms_values=args.local_ms_values,
        network_rtt_values=args.network_rtt_values,
        server_ms_per_step=args.server_ms_per_step,
    )
    output_dir = args.output_dir
    write_csv(output_dir / "sensitivity.csv", rows)
    write_latency_heatmap(output_dir / "latency_sensitivity.svg", rows)
    write_summary(output_dir / "summary.md", rows)
    print(f"Wrote Phase 0B artifacts to {output_dir}")


if __name__ == "__main__":
    main()
