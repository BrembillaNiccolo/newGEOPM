#!/usr/bin/env python3
"""Summarize Phase 0/1 knob runs into workload-class recommendations.

Walks experiments/phase1/<bench>/runs/ recursively, so both layouts work:
  - flat:   runs/<cell_id>/meta.json
  - tagged: runs/<job_tag>/<cell_id>/meta.json   (when --run-tag was used)

Multiple submissions of the same sweep accumulate in different <job_tag>/
directories and are averaged together automatically.

Invoke via the wrapper:
  ./analysis/scripts/summarize_phase0_knobs.sh experiments/phase1/<bench>/runs ...
which uses aurora_geopm_python (python3.10+) so modern type hints are fine.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


ENERGY_KEYS = ("energy_j", "component_energy_j", "total_energy_j")
RUNTIME_KEYS = ("runtime_s", "wall_clock_s", "avg_iter_s")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def first_number(metrics: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def read_runs(run_roots: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for root in run_roots:
        # rglob handles both flat (runs/<cell>/) and tagged (runs/<job>/<cell>/) layouts.
        for meta_path in root.rglob("meta.json"):
            metrics_path = meta_path.with_name("metrics.json")
            if not metrics_path.exists():
                continue
            meta = load_json(meta_path)
            metrics = load_json(metrics_path)
            runtime = first_number(metrics, RUNTIME_KEYS)
            energy = first_number(metrics, ENERGY_KEYS)
            if runtime is None:
                continue
            # Surface the run-tag: parent of the cell dir, unless that's the runs root.
            cell_parent = meta_path.parent.parent.name
            run_tag = cell_parent if cell_parent != "runs" else ""
            rows.append({
                "benchmark": meta["benchmark"],
                "workload_type": meta["workload_type"],
                "variant": meta["variant"],
                "knob": meta["knob"],
                "level": meta["level"]["label"],
                "repeat": meta["repeat"],
                "run_tag": run_tag,
                "apply_controls": bool(meta.get("apply_controls")),
                "runtime_slack": float(meta.get("runtime_slack") or 0.05),
                "runtime_s": runtime,
                "energy_j": energy,
                "cpu_energy_j": metrics.get("cpu_energy_j", ""),
                "dram_energy_j": metrics.get("dram_energy_j", ""),
                "gpu_energy_j": metrics.get("gpu_energy_j", ""),
                "board_energy_j": metrics.get("board_energy_j", ""),
                "component_energy_j": metrics.get("component_energy_j", ""),
                "trace_runtime_s": metrics.get("trace_runtime_s", ""),
                "returncode": meta.get("returncode", metrics.get("process_returncode", 1)),
                "run_dir": str(meta_path.parent),
            })
    return [row for row in rows if row["returncode"] == 0]


def cells_csv_rows(rows):
    """One row per cell: useful for smokes, baseline-only runs, or any run where
    you don't care about knob-vs-baseline comparison."""
    keys = ("benchmark", "workload_type", "variant", "knob", "level", "repeat",
            "run_tag", "apply_controls", "runtime_s", "cpu_energy_j",
            "dram_energy_j", "gpu_energy_j", "board_energy_j",
            "component_energy_j", "trace_runtime_s", "run_dir")
    return [{k: r.get(k, "") for k in keys} for r in rows]


def median(values: list[float]) -> float:
    return statistics.median(values) if values else float("nan")


def mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else float("nan")


def stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def summarize_details(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["benchmark"], row["workload_type"], row["variant"], row["knob"], row["level"])].append(row)

    med_rows = []
    for (benchmark, workload_type, variant, knob, level), members in grouped.items():
        runtimes = [m["runtime_s"] for m in members]
        energies = [m["energy_j"] for m in members if m["energy_j"] is not None]
        tags = sorted({m["run_tag"] for m in members if m.get("run_tag")})
        med_rows.append({
            "benchmark": benchmark,
            "workload_type": workload_type,
            "variant": variant,
            "knob": knob,
            "level": level,
            "apply_controls": any(m["apply_controls"] for m in members),
            "runtime_slack": max(m["runtime_slack"] for m in members),
            "n": len(members),
            "run_tags": ";".join(tags),
            "median_runtime_s": median(runtimes),
            "median_energy_j": median(energies) if energies else "",
            "mean_runtime_s": mean(runtimes),
            "mean_energy_j": mean(energies) if energies else "",
            "std_runtime_s": stdev(runtimes),
            "std_energy_j": stdev(energies) if energies else "",
        })

    baselines: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for row in med_rows:
        if row["level"] == "default":
            baselines[(row["benchmark"], row["workload_type"], row["variant"], row["knob"])] = row

    details = []
    for row in med_rows:
        if row["level"] == "default":
            continue
        base = baselines.get((row["benchmark"], row["workload_type"], row["variant"], row["knob"]))
        if not base:
            continue
        runtime_change_pct = 100.0 * (float(row["median_runtime_s"]) / float(base["median_runtime_s"]) - 1.0)
        energy_change_pct: float | str = ""
        energy_savings_pct: float | str = ""
        if not row["apply_controls"]:
            effectiveness = "control_not_applied"
        elif row["median_energy_j"] != "" and base["median_energy_j"] != "":
            energy_change_pct = 100.0 * (float(row["median_energy_j"]) / float(base["median_energy_j"]) - 1.0)
            energy_savings_pct = -energy_change_pct
            if runtime_change_pct <= 100.0 * float(row["runtime_slack"]) and energy_change_pct < 0:
                effectiveness = "useful"
            elif runtime_change_pct <= 100.0 * float(row["runtime_slack"]):
                effectiveness = "runtime_ok_no_energy_win"
            else:
                effectiveness = "too_slow"
        elif runtime_change_pct <= 100.0 * float(row["runtime_slack"]):
            effectiveness = "runtime_ok_energy_unknown"
        else:
            effectiveness = "too_slow_energy_unknown"

        details.append({
            **row,
            "baseline_runtime_s": base["median_runtime_s"],
            "baseline_energy_j": base["median_energy_j"],
            "runtime_change_pct": runtime_change_pct,
            "energy_change_pct": energy_change_pct,
            "energy_savings_pct": energy_savings_pct,
            "effectiveness": effectiveness,
        })
    return details


def summarize_by_workload(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in details:
        grouped[(row["workload_type"], row["benchmark"])].append(row)

    out = []
    for (workload_type, benchmark), members in sorted(grouped.items()):
        ranked = sorted(
            members,
            key=lambda row: (
                0 if str(row["effectiveness"]).startswith("useful") else 1,
                float(row["runtime_change_pct"]),
                str(row["knob"]),
            ),
        )
        useful = [
            f"{row['knob']}:{row['level']}({row['effectiveness']}, dt={float(row['runtime_change_pct']):+.2f}%, dE={row['energy_change_pct'] if row['energy_change_pct'] != '' else 'unknown'}%)"
            for row in ranked
            if row["effectiveness"] in {"useful", "runtime_ok_energy_unknown"}
        ]
        rejected = [
            f"{row['knob']}:{row['level']}({row['effectiveness']})"
            for row in ranked
            if row["effectiveness"] not in {"useful", "runtime_ok_energy_unknown"}
        ]
        out.append({
            "workload_type": workload_type,
            "benchmark": benchmark,
            "most_useful_knobs": "; ".join(useful) if useful else "none_yet",
            "rejected_or_risky_knobs": "; ".join(rejected),
            "status": "energy_ranked" if any(row["energy_change_pct"] != "" for row in members) else "runtime_only_waiting_for_geopm_energy",
        })
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_roots", nargs="*", default=["experiments/phase1/cpu-dgemm/runs"])
    parser.add_argument("--summary-csv", default="analysis/phase0_knob_summary.csv")
    parser.add_argument("--detail-csv", default="analysis/phase0_knob_detail.csv")
    parser.add_argument("--cells-csv", default="analysis/phase0_cells.csv",
                        help="One row per successful cell. Useful for smoke runs / baseline-only sweeps.")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    rows = read_runs([repo_root / root for root in args.run_roots])
    details = summarize_details(rows)
    summary = summarize_by_workload(details)
    write_csv(repo_root / args.detail_csv, details)
    write_csv(repo_root / args.summary_csv, summary)
    write_csv(repo_root / args.cells_csv, cells_csv_rows(rows))
    print(f"[summary] {args.summary_csv}")
    print(f"[detail]  {args.detail_csv}")
    print(f"[cells]   {args.cells_csv}  ({len(rows)} cells)")
    print(f"[runs] {len(rows)} successful raw runs, {len(details)} level comparisons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
