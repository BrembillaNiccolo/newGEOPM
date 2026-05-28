#!/usr/bin/env python3
"""Test whether knob effects are additive on Phase 1.5 Block B (CPU × GPU 3×3).

Predicted ΔE for a (CPU_level, GPU_level) combo:
    predicted_dE = phase0_dE(CPU=CPU_level) + phase0_dE(GPU=GPU_level)

Compared to measured Phase 1.5 ΔE for that combo. Additivity holds if the
residual |measured - predicted| is small (<5 percentage points) on most
(bench, combo) cells.

Also handles partial Block C (CPU × UNCORE) when data is present.

Output:
- analysis/phase1_5/additivity.csv — per (bench, combo, predicted, measured, residual)
- analysis/phase1_5/additivity_summary.md — human-readable verdict + table
"""

import csv
import os
import statistics
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PHASE0_KNOB = REPO / "analysis/phase0_knob_detail.csv"
PHASE1_5_COMBO = REPO / "analysis/phase1_5/by_combo.csv"
OUT_CSV = REPO / "analysis/phase1_5/additivity.csv"
OUT_MD = REPO / "analysis/phase1_5/additivity_summary.md"

# Map combo label "B_cpuX.Y_gpuP.Q" -> (CPU_level_str, GPU_level_str)
# Phase 0 levels for CPU_FREQUENCY_MAX_CONTROL: lit_1_0GHz / lit_1_2GHz / ...
# Phase 0 levels for GPU_CORE_FREQUENCY_MAX_CONTROL: lit_0_4GHz / lit_1_0GHz / ...
def parse_B_label(label):
    # B_cpu1.0_gpu0.4 -> ("lit_1_0GHz", "lit_0_4GHz")
    parts = label.replace("B_", "").split("_")
    cpu_v = parts[0].replace("cpu", "")           # "1.0"
    gpu_v = parts[1].replace("gpu", "")           # "0.4"
    cpu_lbl = "lit_" + cpu_v.replace(".", "_") + "GHz"
    gpu_lbl = "lit_" + gpu_v.replace(".", "_") + "GHz"
    return cpu_lbl, gpu_lbl

def parse_C_label(label):
    # C_cpu1.0_unc0.8 -> ("lit_1_0GHz" for CPU, "lit_0_8GHz" for UNCORE)
    parts = label.replace("C_", "").split("_")
    cpu_v = parts[0].replace("cpu", "")
    unc_v = parts[1].replace("unc", "")
    cpu_lbl = "lit_" + cpu_v.replace(".", "_") + "GHz"
    unc_lbl = "lit_" + unc_v.replace(".", "_") + "GHz"
    return cpu_lbl, unc_lbl

def load_phase0_priors():
    """Returns priors[bench][knob][level_label] = (dE_pct, dt_pct).
    Uses the row's own energy_change_pct / runtime_change_pct columns —
    Phase 0 detail does NOT have a 'default' baseline row so we cannot
    derive an absolute baseline from it. The baseline lives in each row's
    baseline_energy_j / baseline_runtime_s columns."""
    priors = defaultdict(lambda: defaultdict(dict))
    with PHASE0_KNOB.open() as f:
        for r in csv.DictReader(f):
            bench = r["benchmark"]
            knob = r["knob"]
            level = r["level"]
            try:
                dE_pct = float(r["energy_change_pct"])
                dt_pct = float(r["runtime_change_pct"])
            except (ValueError, KeyError):
                continue
            priors[bench][knob][level] = (dt_pct, dE_pct)
    return priors


def load_phase1_5_baselines():
    """Returns base[bench] = (median_runtime_s, median_energy_j) from the
    A0_all_max row in by_combo.csv."""
    base = {}
    with PHASE1_5_COMBO.open() as f:
        for r in csv.DictReader(f):
            if r["combo_label"] != "A0_all_max":
                continue
            base[r["benchmark"]] = (float(r["median_runtime_s"]),
                                    float(r["median_energy_j"]))
    return base

def main():
    if not PHASE0_KNOB.exists():
        raise SystemExit(f"Missing {PHASE0_KNOB}. Run analysis/scripts/summarize_phase0_knobs.sh first.")
    if not PHASE1_5_COMBO.exists():
        raise SystemExit(f"Missing {PHASE1_5_COMBO}. Aggregate Phase 1.5 first.")

    priors = load_phase0_priors()
    baselines = load_phase1_5_baselines()
    combos = list(csv.DictReader(PHASE1_5_COMBO.open()))

    out_rows = []
    for r in combos:
        block = r["block"]
        if block == "B_cpu_x_gpu_grid":
            cpu_lbl, gpu_lbl = parse_B_label(r["combo_label"])
            cpu_knob = "CPU_FREQUENCY_MAX_CONTROL"
            other_knob = "GPU_CORE_FREQUENCY_MAX_CONTROL"
            other_lbl = gpu_lbl
        elif block == "C_cpu_x_uncore_grid":
            cpu_lbl, unc_lbl = parse_C_label(r["combo_label"])
            cpu_knob = "CPU_FREQUENCY_MAX_CONTROL"
            other_knob = "CPU_UNCORE_FREQUENCY_MAX_CONTROL"
            other_lbl = unc_lbl
        else:
            continue

        bench = r["benchmark"]
        bench_priors = priors.get(bench, {})
        base = baselines.get(bench)
        cpu_p = bench_priors.get(cpu_knob, {}).get(cpu_lbl)
        other_p = bench_priors.get(other_knob, {}).get(other_lbl)
        if not base or not cpu_p or not other_p:
            out_rows.append({
                "benchmark": bench, "combo_label": r["combo_label"],
                "block": block, "status": "missing_priors",
                "baseline_E_J": (f"{base[1]:.0f}" if base else None),
                "cpu_level": cpu_lbl, "other_level": other_lbl,
                "cpu_only_dE_pct": None if not cpu_p else f"{cpu_p[1]:+.1f}",
                "other_only_dE_pct": None if not other_p else f"{other_p[1]:+.1f}",
            })
            continue

        base_r, base_e = base
        cpu_dt_pct, cpu_dE_pct = cpu_p
        other_dt_pct, other_dE_pct = other_p
        predicted_dE_pct = cpu_dE_pct + other_dE_pct
        predicted_dt_pct = cpu_dt_pct + other_dt_pct

        measured_e = float(r["median_energy_j"])
        measured_r = float(r["median_runtime_s"])
        measured_dE_pct = (measured_e - base_e) / base_e * 100
        measured_dt_pct = (measured_r - base_r) / base_r * 100

        residual = measured_dE_pct - predicted_dE_pct
        residual_dt = measured_dt_pct - predicted_dt_pct

        out_rows.append({
            "benchmark": bench, "combo_label": r["combo_label"], "block": block,
            "cpu_level": cpu_lbl, "other_level": other_lbl,
            "n": r["n"],
            "baseline_E_J": f"{base_e:.0f}",
            "cpu_only_dE_pct": f"{cpu_dE_pct:+.1f}",
            "other_only_dE_pct": f"{other_dE_pct:+.1f}",
            "predicted_dE_pct": f"{predicted_dE_pct:+.1f}",
            "measured_dE_pct": f"{measured_dE_pct:+.1f}",
            "residual_dE_pct": f"{residual:+.1f}",
            "predicted_dt_pct": f"{predicted_dt_pct:+.1f}",
            "measured_dt_pct": f"{measured_dt_pct:+.1f}",
            "residual_dt_pct": f"{residual_dt:+.1f}",
            "status": "ok",
        })

    # Write CSV
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    keys = ["benchmark","combo_label","block","cpu_level","other_level","n",
            "baseline_E_J","cpu_only_dE_pct","other_only_dE_pct",
            "predicted_dE_pct","measured_dE_pct","residual_dE_pct",
            "predicted_dt_pct","measured_dt_pct","residual_dt_pct","status"]
    with OUT_CSV.open("w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out_rows)
    print(f"[csv] wrote {OUT_CSV} ({len(out_rows)} rows)")

    # Markdown verdict per bench × block
    by_bench_block = defaultdict(list)
    for r in out_rows:
        if r["status"] != "ok": continue
        by_bench_block[(r["benchmark"], r["block"])].append(r)

    lines = []
    lines.append("# Additivity check — Phase 0 single-knob ΔE sum vs Phase 1.5 combo ΔE")
    lines.append("")
    lines.append("**Rule:** if combined effect = sum of single-knob effects (within ±5 pp residual), "
                 "knobs are additive on that bench. Significant negative residual → synergy "
                 "(combined saves MORE than sum). Significant positive residual → antagonism "
                 "(combined saves LESS than sum).")
    lines.append("")

    for (bench, block), items in sorted(by_bench_block.items()):
        residuals = [float(r["residual_dE_pct"]) for r in items]
        n = len(residuals)
        med = statistics.median(residuals)
        std = statistics.stdev(residuals) if n > 1 else 0.0
        worst = max(residuals, key=abs)
        verdict = ("ADDITIVE" if abs(med) < 5 and std < 5
                   else "ANTAGONISTIC" if med > 5
                   else "SYNERGISTIC" if med < -5
                   else "MIXED")
        lines.append(f"### {bench} — {block}  ({verdict})")
        lines.append("")
        lines.append(f"residual median = {med:+.1f} pp, σ = {std:.1f} pp, worst = {worst:+.1f} pp, n = {n}")
        lines.append("")
        lines.append("| combo | CPU only ΔE | other only ΔE | predicted | measured | residual | meas dt |")
        lines.append("|---|---|---|---|---|---|---|")
        for r in sorted(items, key=lambda x: x["combo_label"]):
            lines.append(f"| `{r['combo_label']}` | "
                         f"{r['cpu_only_dE_pct']}% | "
                         f"{r['other_only_dE_pct']}% | "
                         f"{r['predicted_dE_pct']}% | "
                         f"{r['measured_dE_pct']}% | "
                         f"**{r['residual_dE_pct']} pp** | "
                         f"{r['measured_dt_pct']}% |")
        lines.append("")

    OUT_MD.write_text("\n".join(lines))
    print(f"[md ] wrote {OUT_MD}")

if __name__ == "__main__":
    main()
