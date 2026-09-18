#!/usr/bin/env python3
"""Compare two UniHelp benchmark CSVs (before vs after).

Reports numerical % change; does not label a change as an improvement.

Usage:
    python benchmarks/compare.py \\
        benchmarks/baseline.csv benchmarks/optimized.csv \\
        -o benchmarks/comparison.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from run_benchmark import (
    FEATURE_COUNT_COLUMNS,
    FEATURE_LABELS,
    fmt_num,
    headline_metrics,
    load_result_csv,
    per_feature_means,
    per_query_type_metrics,
    successful_rows,
)

HERE = Path(__file__).resolve().parent


def pct_change(before: Optional[float], after: Optional[float]) -> Optional[float]:
    if before is None or after is None:
        return None
    if before == 0:
        if after == 0:
            return 0.0
        return None
    return (before - after) / before * 100.0


def fmt_pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}%"


def query_ids(rows: list[dict]) -> set[str]:
    return {str(r.get("query_id")) for r in rows}


def filter_query_ids(rows: list[dict], ids: set[str]) -> list[dict]:
    return [r for r in rows if str(r.get("query_id")) in ids]


HEADLINE_KEYS = [
    ("llm_calls_per_request", "Mean LLM calls/request", 2),
    ("executor_calls_per_request", "Mean Executor LLM calls/request", 2),
    ("tokens_per_request", "Mean total tokens/request", 1),
    ("mean_latency_ms", "Mean latency (ms)", 1),
    ("p50_latency_ms", "P50 latency (ms)", 1),
    ("p95_latency_ms", "P95 latency (ms)", 1),
    ("estimated_cost_per_request", "Mean estimated cost/request", 6),
]


def write_comparison(
    path: Path,
    before_path: Path,
    after_path: Path,
    before_rows: list[dict],
    after_rows: list[dict],
) -> None:
    before_ids = query_ids(before_rows)
    after_ids = query_ids(after_rows)
    shared = before_ids & after_ids
    only_before = sorted(before_ids - after_ids, key=_id_sort)
    only_after = sorted(after_ids - before_ids, key=_id_sort)

    before_ok = successful_rows(before_rows)
    after_ok = successful_rows(after_rows)
    before_ind = headline_metrics(before_rows)
    after_ind = headline_metrics(after_rows)

    before_paired = filter_query_ids(before_rows, shared)
    after_paired = filter_query_ids(after_rows, shared)
    before_pair_m = headline_metrics(before_paired)
    after_pair_m = headline_metrics(after_paired)

    lines = [
        "# UniHelp benchmark comparison",
        "",
        f"- Before: `{before_path}`",
        f"- After: `{after_path}`",
        f"- Before rows: {len(before_rows)} ({len(before_ok)} successful)",
        f"- After rows: {len(after_rows)} ({len(after_ok)} successful)",
        f"- Shared query_ids: {len(shared)}",
        "",
        "% change is `(before - after) / before * 100`. A positive value "
        "means the after number is lower. This file does **not** label a "
        "change as an improvement.",
        "",
    ]

    if only_before or only_after:
        lines.append("## Unmatched query IDs")
        lines.append("")
        if only_before:
            lines.append(
                "- Present only in before: " + ", ".join(only_before)
            )
        if only_after:
            lines.append(
                "- Present only in after: " + ", ".join(only_after)
            )
        lines.append("")
        lines.append(
            "Unmatched IDs are excluded from paired comparisons below. "
            "Independent aggregates still use every row in each file."
        )
        lines.append("")
        print(
            "WARNING: query_id mismatch. "
            f"only_before={only_before or '[]'} only_after={only_after or '[]'}",
            file=sys.stderr,
        )
    else:
        lines.append("All query_ids appear in both files.")
        lines.append("")

    lines.extend(
        [
            "## Independent aggregates (all rows in each file)",
            "",
            "| Metric | Before | After | % change |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for key, label, digits in HEADLINE_KEYS:
        b, a = before_ind[key], after_ind[key]
        lines.append(
            f"| {label} | {fmt_num(b, digits)} | {fmt_num(a, digits)} | "
            f"{fmt_pct(pct_change(b, a))} |"
        )
    lines.append("")

    lines.extend(
        [
            "## Paired comparison (shared query_ids only)",
            "",
            "| Metric | Before | After | % change |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for key, label, digits in HEADLINE_KEYS:
        b, a = before_pair_m[key], after_pair_m[key]
        lines.append(
            f"| {label} | {fmt_num(b, digits)} | {fmt_num(a, digits)} | "
            f"{fmt_pct(pct_change(b, a))} |"
        )
    lines.append("")

    lines.extend(
        [
            "## Query-type breakdown (paired query_ids)",
            "",
            "| query_type | Metric | Before | After | % change |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
    )
    before_types = dict(per_query_type_metrics(before_paired))
    after_types = dict(per_query_type_metrics(after_paired))
    type_keys = []
    for key in list(before_types) + list(after_types):
        if key not in type_keys:
            type_keys.append(key)
    for tkey in type_keys:
        bm = before_types.get(tkey) or {k: None for k, _, _ in HEADLINE_KEYS}
        am = after_types.get(tkey) or {k: None for k, _, _ in HEADLINE_KEYS}
        for key, label, digits in HEADLINE_KEYS:
            b, a = bm.get(key), am.get(key)
            lines.append(
                f"| {tkey} | {label} | {fmt_num(b, digits)} | "
                f"{fmt_num(a, digits)} | {fmt_pct(pct_change(b, a))} |"
            )
    lines.append("")

    lines.extend(
        [
            "## Per-feature LLM calls (paired query_ids, avg/request)",
            "",
            "| Feature | Before | After | % change |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    before_feat = per_feature_means(before_paired)
    after_feat = per_feature_means(after_paired)
    for name in FEATURE_COUNT_COLUMNS:
        b, a = before_feat[name], after_feat[name]
        lines.append(
            f"| {FEATURE_LABELS[name]} | {fmt_num(b)} | {fmt_num(a)} | "
            f"{fmt_pct(pct_change(b, a))} |"
        )
    lines.append("")

    lines.extend(
        [
            "## Notes",
            "",
            "- Independent aggregates include unmatched query_ids; paired "
            "tables do not.",
            "- Successful rows are those with `status == ok`.",
            "- `cached_tokens` (when present in the CSVs) is LLM/provider "
            "caching, not application cache hits.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _id_sort(value: str):
    try:
        return (0, int(value))
    except ValueError:
        return (1, value)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two UniHelp benchmark CSV files."
    )
    parser.add_argument("before", type=Path, help="Earlier run CSV (e.g. baseline.csv)")
    parser.add_argument("after", type=Path, help="Later run CSV (e.g. optimized.csv)")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=HERE / "comparison.md",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    if not args.before.is_file():
        raise SystemExit(f"before CSV not found: {args.before}")
    if not args.after.is_file():
        raise SystemExit(f"after CSV not found: {args.after}")

    before_rows = load_result_csv(args.before)
    after_rows = load_result_csv(args.after)
    write_comparison(
        args.output,
        args.before,
        args.after,
        before_rows,
        after_rows,
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
