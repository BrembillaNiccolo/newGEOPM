#!/usr/bin/env python3
"""Compress per-cell results into per-control response curves.

Instead of one row per (bench, knob, level) like phase0_knob_detail.csv, this
emits one row per (bench, control) with a sorted list of (level, dE, dt) tuples
and a verdict about how the control behaves on that bench:

  USEFUL_LINEAR     — dE drops monotonically as the cap tightens, runtime ok
  USEFUL_THRESHOLD  — dE only drops past a threshold level, runtime ok
  HARMFUL           — at least one level breaks the runtime budget
  NEGLIGIBLE        — every level within +-1 % dE and +-1 % dt

Reads analysis/phase0_cells.csv (raw per-cell data). Writes:
  analysis/phase0_by_control.csv     — machine-readable per-(bench, control) row
  analysis/phase0_by_control_curves.md — human-readable response-curve tables
"""

import argparse
import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


# Order levels by intensity for the curve display. Higher index = more aggressive.
def level_sort_key(level: str) -> tuple:
    """Sort levels left-to-right from most-lenient to most-aggressive.

    Heuristics:
      - 'default' goes first.
      - For literal watts (lit_3000W): higher watts = more lenient -> earlier.
      - For tdp_NN / rb_NN / frac_NN: higher NN = closer to 100 % = more lenient.
      - For lit_0_75 etc.: higher number = (depends on knob; treat as numeric).
      - For rb_half / rb_double: half < default < double (treat as 0.5 / 2.0).
      - Anything unrecognized goes last.
    """
    if level == "default":
        return (0, 0.0)
    m = re.match(r"lit_(\d+)W", level)
    if m:
        return (1, -int(m.group(1)))  # higher watts -> smaller sort key -> more lenient first
    m = re.match(r"(?:tdp|rb|frac)_(\d+)", level)
    if m:
        return (1, -int(m.group(1)))  # 100 -> -100 -> earliest; 40 -> -40 -> latest
    # Old-style readback_NNpct
    m = re.match(r"readback_(\d+)pct", level)
    if m:
        return (1, -int(m.group(1)))
    m = re.match(r"lit_(\d+)_(\d+)", level)
    if m:
        return (2, float(f"{m.group(1)}.{m.group(2)}"))
    if level == "rb_half":
        return (3, 0.5)
    if level == "rb_double":
        return (3, 2.0)
    return (9, level)


def shortlevel(level: str) -> str:
    """Compact label for table headers (max 8 chars)."""
    if level == "default":
        return "DEF"
    m = re.match(r"lit_(\d+)W", level)
    if m:
        return f"{int(m.group(1))//100/10:.1f}kW"
    m = re.match(r"tdp_(\d+)", level)
    if m:
        return f"tdp{m.group(1)}"
    m = re.match(r"rb_(\d+)", level)
    if m:
        return f"rb{m.group(1)}"
    m = re.match(r"frac_(\d+)", level)
    if m:
        return f"frac{m.group(1)}"
    # Old-style label names from earlier sweep:
    m = re.match(r"readback_(\d+)pct", level)
    if m:
        return f"rb{m.group(1)}"
    m = re.match(r"lit_(\d+)_(\d+)", level)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    if level in ("rb_half", "readback_half"):
        return "tw0.5x"
    if level in ("rb_double", "readback_double"):
        return "tw2x"
    return level[:8]


def short_control(name: str) -> str:
    """Compact control name for tables."""
    return (name
            .replace("LEVELZERO::", "L0::")
            .replace("_CONTROL", "")
            .replace("_FREQUENCY", "_FREQ")
            .replace("_POWER_TIME_WINDOW", "_PTWIN"))


def load_cells(cells_csv: Path) -> list[dict[str, Any]]:
    rows = []
    for r in csv.DictReader(cells_csv.open()):
        try:
            runtime = float(r["runtime_s"]) if r["runtime_s"] else None
        except ValueError:
            runtime = None
        if runtime is None:
            continue
        rows.append({
            "bench": r["benchmark"],
            "knob": r["knob"],
            "level": r["level"],
            "runtime_s": runtime,
            "board_J": float(r["board_energy_j"]) if r["board_energy_j"] else None,
            "cpu_J": float(r["cpu_energy_j"]) if r["cpu_energy_j"] else None,
            "gpu_J": float(r["gpu_energy_j"]) if r["gpu_energy_j"] else None,
            "dram_J": float(r["dram_energy_j"]) if r["dram_energy_j"] else None,
            "component_J": float(r["component_energy_j"]) if r["component_energy_j"] else None,
            "run_tag": r["run_tag"],
        })
    return rows


def per_level_medians(rows: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict]:
    """Returns {(bench, knob, level) -> {runtime, board_J, n}} medians across repeats."""
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["bench"], r["knob"], r["level"])].append(r)
    out = {}
    for k, group in grouped.items():
        runtimes = [g["runtime_s"] for g in group]
        boards = [g["board_J"] for g in group if g["board_J"] is not None and g["board_J"] > 0]
        out[k] = {
            "runtime_s": statistics.median(runtimes),
            "board_J": statistics.median(boards) if boards else None,
            "n": len(group),
        }
    return out


def classify_curve(level_data: list[dict]) -> str:
    """Classify a per-control response curve.

    level_data is the curve excluding the default baseline, sorted by intensity
    (lenient -> aggressive). Each entry has keys 'dE_pct', 'dt_pct'.
    """
    if not level_data:
        return "NO_DATA"
    dEs = [l["dE_pct"] for l in level_data if l.get("dE_pct") is not None]
    dts = [l["dt_pct"] for l in level_data]

    max_dt = max(dts) if dts else 0.0
    min_dE = min(dEs) if dEs else 0.0
    span_dE = (max(dEs) - min(dEs)) if dEs else 0.0
    span_dt = (max(dts) - min(dts)) if dts else 0.0

    if max_dt > 5.0:
        return "HARMFUL"
    if span_dE < 1.0 and span_dt < 1.0:
        return "NEGLIGIBLE"
    # Monotonic check on dE across the levels (more-aggressive should give smaller dE)
    monotone = all(dEs[i] >= dEs[i+1] - 0.5 for i in range(len(dEs)-1))  # tolerate small wobble
    if monotone and min_dE < -1.0:
        return "USEFUL_LINEAR"
    if min_dE < -3.0:
        return "USEFUL_THRESHOLD"
    if min_dE < -0.5:
        return "USEFUL_MILD"
    return "FLAT"


def build_per_control(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    medians = per_level_medians(rows)
    # group medians by (bench, knob), find baseline (level="default"), compute deltas
    by_bench_knob = defaultdict(dict)
    for (b, k, l), m in medians.items():
        by_bench_knob[(b, k)][l] = m

    out = []
    for (bench, knob), levels in by_bench_knob.items():
        baseline = levels.get("default")
        if baseline is None:
            # no default baseline -> skip; can't compute deltas
            continue
        # Sort non-default levels
        non_default = sorted(
            [(lvl, m) for lvl, m in levels.items() if lvl != "default"],
            key=lambda x: level_sort_key(x[0]),
        )
        level_data = []
        for lvl, m in non_default:
            dt_pct = 100.0 * (m["runtime_s"] / baseline["runtime_s"] - 1.0)
            dE_pct = (100.0 * (m["board_J"] / baseline["board_J"] - 1.0)
                      if m["board_J"] is not None and baseline["board_J"] else None)
            level_data.append({
                "level": lvl,
                "n": m["n"],
                "dt_pct": dt_pct,
                "dE_pct": dE_pct,
            })
        verdict = classify_curve(level_data) if level_data else "NO_DATA"
        out.append({
            "benchmark": bench,
            "control": knob,
            "n_levels": len(level_data),
            "baseline_runtime_s": baseline["runtime_s"],
            "baseline_board_J": baseline["board_J"],
            "verdict": verdict,
            "best_dE_pct": (min((l["dE_pct"] for l in level_data if l["dE_pct"] is not None), default=None)),
            "worst_dt_pct": (max((l["dt_pct"] for l in level_data), default=0.0)),
            "curve": level_data,
        })
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flat = []
    for r in rows:
        base = {k: v for k, v in r.items() if k != "curve"}
        # Serialise the curve as a compact string: "lvl:dE/dt | lvl:dE/dt | ..."
        base["curve_pairs"] = " | ".join(
            f"{c['level']}:dE={c['dE_pct']:.1f}%/dt={c['dt_pct']:+.1f}%"
            if c['dE_pct'] is not None
            else f"{c['level']}:dE=?/dt={c['dt_pct']:+.1f}%"
            for c in r["curve"]
        )
        flat.append(base)
    if not flat:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(flat[0].keys()))
        w.writeheader()
        w.writerows(flat)


def write_markdown_tables(path: Path, results: list[dict[str, Any]]) -> None:
    """One table per benchmark, columns are intensity levels (sorted)."""
    by_bench = defaultdict(list)
    for r in results:
        by_bench[r["benchmark"]].append(r)

    lines = []
    lines.append("# Per-control response curves\n")
    lines.append("For each benchmark, one row per control. Columns are the levels sorted from most-lenient (left) to most-aggressive (right). Each cell is `ΔE% / Δt%` vs the default-level baseline of the same control. **Bold** = USEFUL_LINEAR, *italic* = HARMFUL, plain = NEGLIGIBLE/FLAT/MILD.\n")
    lines.append("Verdict legend:\n")
    lines.append("- **USEFUL_LINEAR**: ΔE monotonically drops as the cap tightens, runtime stays within +5 % budget. Bandit-friendly response curve.\n")
    lines.append("- **USEFUL_THRESHOLD**: notable ΔE drop only at one level, mostly flat elsewhere. Use that specific level.\n")
    lines.append("- **USEFUL_MILD**: small (< 3 %) but real ΔE drop, runtime ok. Low-priority arm.\n")
    lines.append("- **HARMFUL**: at least one level pushes runtime > +5 % over baseline. Use only with workload classifier.\n")
    lines.append("- **NEGLIGIBLE**: ΔE span < 1 %; this control doesn't do much on this bench.\n")
    lines.append("- **FLAT**: small effect, not monotone.\n")
    lines.append("- **NO_DATA**: no non-default cells captured.\n\n")

    for bench in sorted(by_bench):
        rows = sorted(by_bench[bench], key=lambda r: r["control"])
        lines.append(f"## {bench}\n")
        # Find union of levels across all controls for this bench (to align columns)
        all_levels_set = set()
        for r in rows:
            for c in r["curve"]:
                all_levels_set.add(c["level"])
        all_levels = sorted(all_levels_set, key=level_sort_key)
        header = ["control", "verdict", "n_lv", "base_J"] + [shortlevel(l) for l in all_levels]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * len(header)) + "|")
        for r in rows:
            curve_by_level = {c["level"]: c for c in r["curve"]}
            cells = []
            for lvl in all_levels:
                c = curve_by_level.get(lvl)
                if c is None:
                    cells.append("·")
                else:
                    dE = c["dE_pct"]
                    dt = c["dt_pct"]
                    if dE is None:
                        cells.append(f"? / {dt:+.1f}")
                    else:
                        s = f"{dE:+.1f} / {dt:+.1f}"
                        cells.append(s)
            v = r["verdict"]
            v_fmt = f"**{v}**" if v == "USEFUL_LINEAR" else (f"*{v}*" if v == "HARMFUL" else v)
            base_J = f"{int(r['baseline_board_J']):,}" if r["baseline_board_J"] else "—"
            row = [short_control(r["control"]), v_fmt, str(r["n_levels"]), base_J] + cells
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells-csv", default="analysis/phase0_cells.csv")
    parser.add_argument("--out-csv", default="analysis/phase0_by_control.csv")
    parser.add_argument("--out-md", default="analysis/phase0_by_control_curves.md")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    cells = load_cells(repo_root / args.cells_csv)
    results = build_per_control(cells)
    results.sort(key=lambda r: (r["benchmark"], r["control"]))

    write_csv(repo_root / args.out_csv, results)
    write_markdown_tables(repo_root / args.out_md, results)

    print(f"[by_control_csv] {args.out_csv}  ({len(results)} (bench, control) rows)")
    print(f"[by_control_md ] {args.out_md}")

    # Quick console summary: verdict counts
    from collections import Counter
    verdicts = Counter(r["verdict"] for r in results)
    print()
    print("Verdict distribution:")
    for v, n in verdicts.most_common():
        print(f"  {v:20s} {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
