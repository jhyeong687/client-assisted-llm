from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.client_assisted_llm.simulate import SimulationConfig, simulate


DEFAULT_ACCEPT_RATES = [0.25, 0.40, 0.55, 0.70, 0.85]
DEFAULT_DRAFT_WINDOWS = [2, 4, 8, 16, 32]


def parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def parse_int_list(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def run_sweep(
    *,
    target_tokens: int,
    accept_rates: list[float],
    draft_windows: list[int],
    local_ms_per_token: float,
    server_ms_per_step: float,
    network_rtt_ms: float,
) -> list[dict[str, float | int]]:
    rows: list[dict[str, float | int]] = []
    for accept_rate in accept_rates:
        for draft_window in draft_windows:
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
                    "server_only_steps": result.server_only_steps,
                    "assisted_server_steps": result.assisted_server_steps,
                    "accepted_tokens": result.accepted_tokens,
                    "rejected_tokens": result.rejected_tokens,
                    "server_step_reduction_pct": round(result.server_step_delta_pct, 3),
                    "latency_reduction_pct": round(result.latency_delta_pct, 3),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def metric_color(value: float, *, low: float, high: float) -> str:
    clamped = max(low, min(high, value))
    normalized = (clamped - low) / (high - low)

    if normalized < 0.5:
        ratio = normalized / 0.5
        red = 214
        green = round(69 + (160 - 69) * ratio)
        blue = 80
    else:
        ratio = (normalized - 0.5) / 0.5
        red = round(214 + (76 - 214) * ratio)
        green = round(160 + (175 - 160) * ratio)
        blue = round(80 + (80 - 80) * ratio)
    return f"#{red:02x}{green:02x}{blue:02x}"


def write_heatmap_svg(
    path: Path,
    rows: list[dict[str, float | int]],
    *,
    metric: str,
    title: str,
    value_suffix: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    accept_rates = sorted({float(row["accept_rate"]) for row in rows})
    draft_windows = sorted({int(row["draft_window"]) for row in rows})
    values = {
        (float(row["accept_rate"]), int(row["draft_window"])): float(row[metric]) for row in rows
    }

    cell_w = 112
    cell_h = 52
    left = 112
    top = 84
    width = left + cell_w * len(draft_windows) + 36
    height = top + cell_h * len(accept_rates) + 64

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fafafa"/>',
        f'<text x="24" y="32" font-family="Arial, sans-serif" font-size="20" '
        f'font-weight="700" fill="#202124">{title}</text>',
        '<text x="24" y="56" font-family="Arial, sans-serif" font-size="12" '
        'fill="#5f6368">Rows: accept rate, columns: draft window</text>',
    ]

    for col, draft_window in enumerate(draft_windows):
        x = left + col * cell_w + cell_w / 2
        parts.append(
            f'<text x="{x}" y="{top - 18}" text-anchor="middle" '
            'font-family="Arial, sans-serif" font-size="12" fill="#3c4043">'
            f"k={draft_window}</text>"
        )

    for row_index, accept_rate in enumerate(accept_rates):
        y = top + row_index * cell_h
        parts.append(
            f'<text x="{left - 16}" y="{y + cell_h / 2 + 4}" text-anchor="end" '
            'font-family="Arial, sans-serif" font-size="12" fill="#3c4043">'
            f"{accept_rate:.2f}</text>"
        )
        for col, draft_window in enumerate(draft_windows):
            value = values[(accept_rate, draft_window)]
            x = left + col * cell_w
            fill = metric_color(value, low=-50, high=90)
            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell_w - 4}" height="{cell_h - 4}" '
                f'rx="6" fill="{fill}"/>'
            )
            parts.append(
                f'<text x="{x + (cell_w - 4) / 2}" y="{y + cell_h / 2 + 4}" '
                'text-anchor="middle" font-family="Arial, sans-serif" '
                'font-size="13" font-weight="700" fill="#ffffff">'
                f"{value:.1f}{value_suffix}</text>"
            )

    parts.append("</svg>")
    path.write_text("\n".join(parts), encoding="utf-8")


def write_summary(path: Path, rows: list[dict[str, float | int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    best_latency = max(rows, key=lambda row: float(row["latency_reduction_pct"]))
    best_steps = max(rows, key=lambda row: float(row["server_step_reduction_pct"]))
    viable = [
        row
        for row in rows
        if float(row["latency_reduction_pct"]) >= 15
        and float(row["server_step_reduction_pct"]) >= 25
    ]

    lines = [
        "# Phase 0 Sweep Summary",
        "",
        "This summary is generated from the toy simulation model. Treat it as a quick map, not a real GPU benchmark.",
        "",
        "## Best Latency Case",
        "",
        f"- accept_rate: {float(best_latency['accept_rate']):.2f}",
        f"- draft_window: {int(best_latency['draft_window'])}",
        f"- latency_reduction_pct: {float(best_latency['latency_reduction_pct']):.1f}",
        f"- server_step_reduction_pct: {float(best_latency['server_step_reduction_pct']):.1f}",
        "",
        "## Best Server Step Case",
        "",
        f"- accept_rate: {float(best_steps['accept_rate']):.2f}",
        f"- draft_window: {int(best_steps['draft_window'])}",
        f"- latency_reduction_pct: {float(best_steps['latency_reduction_pct']):.1f}",
        f"- server_step_reduction_pct: {float(best_steps['server_step_reduction_pct']):.1f}",
        "",
        "## Viable Cells",
        "",
    ]

    if not viable:
        lines.append("No cells met both the latency and server-step thresholds.")
    else:
        for row in viable:
            lines.append(
                "- "
                f"accept_rate={float(row['accept_rate']):.2f}, "
                f"draft_window={int(row['draft_window'])}, "
                f"latency_reduction={float(row['latency_reduction_pct']):.1f}%, "
                f"server_step_reduction={float(row['server_step_reduction_pct']):.1f}%"
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Phase 0 sweep and write result artifacts.")
    parser.add_argument("--target-tokens", type=int, default=256)
    parser.add_argument("--accept-rates", type=parse_float_list, default=DEFAULT_ACCEPT_RATES)
    parser.add_argument("--draft-windows", type=parse_int_list, default=DEFAULT_DRAFT_WINDOWS)
    parser.add_argument("--local-ms-per-token", type=float, default=4.0)
    parser.add_argument("--server-ms-per-step", type=float, default=20.0)
    parser.add_argument("--network-rtt-ms", type=float, default=15.0)
    parser.add_argument("--output-dir", type=Path, default=Path("results/phase0"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = run_sweep(
        target_tokens=args.target_tokens,
        accept_rates=args.accept_rates,
        draft_windows=args.draft_windows,
        local_ms_per_token=args.local_ms_per_token,
        server_ms_per_step=args.server_ms_per_step,
        network_rtt_ms=args.network_rtt_ms,
    )

    output_dir = args.output_dir
    write_csv(output_dir / "sweep.csv", rows)
    write_heatmap_svg(
        output_dir / "latency_reduction.svg",
        rows,
        metric="latency_reduction_pct",
        title="Latency Reduction",
        value_suffix="%",
    )
    write_heatmap_svg(
        output_dir / "server_step_reduction.svg",
        rows,
        metric="server_step_reduction_pct",
        title="Server Step Reduction",
        value_suffix="%",
    )
    write_summary(output_dir / "summary.md", rows)
    print(f"Wrote Phase 0 artifacts to {output_dir}")


if __name__ == "__main__":
    main()
