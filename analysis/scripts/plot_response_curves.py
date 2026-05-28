#!/usr/bin/env python3
"""Plot per-knob response curves from phase0_cells.csv.

For each (benchmark, control) produces a 3-panel PNG showing how the knob
affects runtime, board energy, and mean board power as you sweep the level
from lenient -> aggressive. Error bars are IQR across the 10 PBS-job repeats.

Also produces, per control, a cross-bench overlay so you can compare workload
classes on one figure.

Output layout (under analysis/plots/):
  per_bench/<bench>/<control>.png         3-panel response curve
  per_control/<control>.png               cross-bench overlay (all 7 benches)
  index.md                                clickable thumbnail index

Conventions per analysis/CLAUDE.md:
  - matplotlib only
  - color per workload class
  - IQR error bars (25-75 % whiskers around median)
  - PNG only (no PDF to keep size down; can add later for paper)
"""

import csv
import re
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
CELLS_CSV = REPO_ROOT / "analysis/phase0_cells.csv"
PLOTS_DIR = REPO_ROOT / "analysis/plots"

# Color per workload class (per analysis/CLAUDE.md):
WORKLOAD_COLOR = {
    "gpu_compute":       "tab:red",
    "cpu_compute":       "tab:orange",
    "cpu_memory":        "tab:blue",
    "gpu_memory":        "tab:cyan",
    "mpi_communication": "tab:green",
    "mpi_slack":         "tab:olive",
    "gpu_bursty_idle":   "tab:purple",
}


def level_sort_key(level: str) -> tuple:
    """Sort lenient->aggressive. default goes first."""
    if level == "default":
        return (0, 0.0)
    m = re.match(r"lit_(\d+)W", level)
    if m:
        return (1, -int(m.group(1)))  # higher W -> earlier
    m = re.match(r"(?:tdp|rb|frac)_(\d+)", level)
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


def short_level(level: str) -> str:
    if level == "default":
        return "DEF"
    m = re.match(r"lit_(\d+)W", level)
    if m:
        return f"{int(m.group(1))//100/10:.1f}kW"
    m = re.match(r"tdp_(\d+)", level)
    if m:
        return f"{m.group(1)}%"
    m = re.match(r"rb_(\d+)", level)
    if m:
        return f"{m.group(1)}%"
    m = re.match(r"frac_(\d+)", level)
    if m:
        return f"{m.group(1)}%"
    m = re.match(r"lit_(\d+)_(\d+)", level)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    if level == "rb_half":
        return "0.5×"
    if level == "rb_double":
        return "2×"
    return level


def short_control(name: str) -> str:
    return (name
            .replace("LEVELZERO::", "L0::")
            .replace("_CONTROL", "")
            .replace("_FREQUENCY", "_FREQ")
            .replace("_POWER_TIME_WINDOW", "_PTWIN"))


def load_cells():
    rows = []
    for r in csv.DictReader(CELLS_CSV.open()):
        try:
            rt = float(r["runtime_s"]) if r["runtime_s"] else None
        except ValueError:
            rt = None
        if rt is None or rt <= 0:
            continue
        try:
            bE = float(r["board_energy_j"]) if r["board_energy_j"] else None
        except ValueError:
            bE = None
        rows.append({
            "bench": r["benchmark"],
            "workload": r["workload_type"],
            "knob": r["knob"],
            "level": r["level"],
            "runtime_s": rt,
            "board_J": bE,
            "cpu_J": float(r["cpu_energy_j"]) if r["cpu_energy_j"] else None,
            "gpu_J": float(r["gpu_energy_j"]) if r["gpu_energy_j"] else None,
            "dram_J": float(r["dram_energy_j"]) if r["dram_energy_j"] else None,
        })
    return rows


def stats_per_level(rows):
    """Return {(bench, knob, level) -> (n, median_dict, q25_dict, q75_dict)} for runtime/board_J/mean_W."""
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["bench"], r["knob"], r["level"])].append(r)
    out = {}
    for key, group in grouped.items():
        rts = [g["runtime_s"] for g in group]
        bEs = [g["board_J"] for g in group if g["board_J"] is not None and g["board_J"] > 0]
        # mean_W = board_J / runtime_s, computed cell-wise then aggregated
        meanWs = []
        for g in group:
            if g["board_J"] and g["runtime_s"]:
                meanWs.append(g["board_J"] / g["runtime_s"])

        def quart(xs):
            if not xs:
                return None, None, None
            xs = sorted(xs)
            n = len(xs)
            med = statistics.median(xs)
            q1 = xs[max(0, n // 4)] if n >= 4 else xs[0]
            q3 = xs[min(n - 1, 3 * n // 4)] if n >= 4 else xs[-1]
            return med, q1, q3

        rt_m, rt_q1, rt_q3 = quart(rts)
        bE_m, bE_q1, bE_q3 = quart(bEs)
        mW_m, mW_q1, mW_q3 = quart(meanWs)
        out[key] = {
            "n": len(group),
            "rt": (rt_m, rt_q1, rt_q3),
            "bE": (bE_m, bE_q1, bE_q3),
            "mW": (mW_m, mW_q1, mW_q3),
            "workload": group[0]["workload"],
        }
    return out


def plot_per_bench_control(bench, knob, levels, stats, baseline, color, out_path):
    """3-panel response curve for one (bench, knob)."""
    if not levels:
        return False
    xs = list(range(len(levels)))
    x_labels = [short_level(l) for l in levels]
    rt_med = [stats[(bench, knob, l)]["rt"][0] for l in levels]
    rt_q1  = [stats[(bench, knob, l)]["rt"][1] for l in levels]
    rt_q3  = [stats[(bench, knob, l)]["rt"][2] for l in levels]
    bE_med = [stats[(bench, knob, l)]["bE"][0] for l in levels]
    bE_q1  = [stats[(bench, knob, l)]["bE"][1] for l in levels]
    bE_q3  = [stats[(bench, knob, l)]["bE"][2] for l in levels]
    mW_med = [stats[(bench, knob, l)]["mW"][0] for l in levels]
    mW_q1  = [stats[(bench, knob, l)]["mW"][1] for l in levels]
    mW_q3  = [stats[(bench, knob, l)]["mW"][2] for l in levels]

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6), constrained_layout=True)

    def panel(ax, med, q1, q3, ylabel, baseline_val, fmt):
        valid_x = [x for x, m in zip(xs, med) if m is not None]
        valid_med = [m for m in med if m is not None]
        valid_lo  = [m - q for m, q in zip(med, q1) if m is not None]
        valid_hi  = [q - m for m, q in zip(med, q3) if m is not None]
        if valid_med:
            ax.errorbar(valid_x, valid_med, yerr=[valid_lo, valid_hi],
                        marker="o", capsize=3, color=color, linewidth=1.5, markersize=5)
            if baseline_val is not None:
                ax.axhline(baseline_val, color="grey", linestyle="--", alpha=0.6, linewidth=1, label=f"baseline {fmt.format(baseline_val)}")
                ax.legend(fontsize=7, loc="best")
        ax.set_xticks(xs)
        ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel(ylabel, fontsize=9)
        ax.grid(True, alpha=0.3)

    panel(axes[0], rt_med, rt_q1, rt_q3, "runtime (s)", baseline["rt"][0] if baseline else None, "{:.1f}s")
    panel(axes[1], bE_med, bE_q1, bE_q3, "board energy (J)", baseline["bE"][0] if baseline else None, "{:.0f}J")
    panel(axes[2], mW_med, mW_q1, mW_q3, "mean board power (W)", baseline["mW"][0] if baseline else None, "{:.0f}W")
    fig.suptitle(f"{bench}  ·  {short_control(knob)}   (median ± IQR across {stats[(bench, knob, levels[0])]['n']} repeats)", fontsize=11)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
    return True


def plot_cross_bench_control(knob, by_bench_levels, stats, out_path):
    """Overlay all 7 benches on one figure (% change vs each bench's own default).

    3 panels: Δruntime %, Δenergy %, Δmean-power %.
    """
    benches = sorted(by_bench_levels.keys())
    if not benches:
        return False

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2), constrained_layout=True)
    titles = ["Δ runtime (%)", "Δ board energy (%)", "Δ mean board power (%)"]
    metrics = ["rt", "bE", "mW"]

    # Build a per-bench level list -> use the union sorted
    all_levels = set()
    for b in benches:
        all_levels |= set(by_bench_levels[b])
    levels = sorted(all_levels, key=level_sort_key)
    levels_nodefault = [l for l in levels if l != "default"]
    if not levels_nodefault:
        plt.close(fig)
        return False
    x_labels = [short_level(l) for l in levels_nodefault]
    xs = list(range(len(levels_nodefault)))

    for col, (ax, title, mkey) in enumerate(zip(axes, titles, metrics)):
        for b in benches:
            baseline = stats.get((b, knob, "default"))
            if not baseline or baseline[mkey][0] is None:
                continue
            base_val = baseline[mkey][0]
            ys = []
            for l in levels_nodefault:
                s = stats.get((b, knob, l))
                v = s[mkey][0] if s else None
                if v is None or base_val == 0:
                    ys.append(None)
                else:
                    ys.append(100.0 * (v / base_val - 1.0))
            color = WORKLOAD_COLOR.get(baseline["workload"], "grey")
            valid = [(x, y) for x, y in zip(xs, ys) if y is not None]
            if valid:
                vx, vy = zip(*valid)
                ax.plot(vx, vy, marker="o", color=color, label=b, linewidth=1.4, markersize=4)
        ax.axhline(0, color="grey", linestyle="-", linewidth=0.6)
        # Slack budget reference lines on runtime panel
        if col == 0:
            ax.axhline(+5, color="red", linestyle=":", linewidth=0.8, alpha=0.5, label="±5 % slack")
            ax.axhline(-5, color="red", linestyle=":", linewidth=0.8, alpha=0.5)
        ax.set_xticks(xs)
        ax.set_xticklabels(x_labels, rotation=45, ha="right", fontsize=8)
        ax.set_ylabel(title, fontsize=9)
        ax.grid(True, alpha=0.3)
        if col == 2:
            ax.legend(fontsize=7, loc="center left", bbox_to_anchor=(1.0, 0.5))

    fig.suptitle(f"{short_control(knob)}  ·  response across all 7 benches", fontsize=12)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110, bbox_inches="tight")
    plt.close(fig)
    return True


def main():
    cells = load_cells()
    print(f"loaded {len(cells)} cells from {CELLS_CSV.name}")
    stats = stats_per_level(cells)

    # Group: (bench, knob) -> sorted levels
    levels_by_bench_knob = defaultdict(list)
    for (b, k, l) in stats:
        levels_by_bench_knob[(b, k)].append(l)
    for key in levels_by_bench_knob:
        levels_by_bench_knob[key].sort(key=level_sort_key)

    # All controls and all benches
    controls = sorted({k for (_, k, _) in stats})
    benches = sorted({b for (b, _, _) in stats})

    # 1) Per-bench-per-control panels
    n_per_bench = 0
    for (b, k), levels in sorted(levels_by_bench_knob.items()):
        baseline = stats.get((b, k, "default"))
        workload = baseline["workload"] if baseline else "unknown"
        color = WORKLOAD_COLOR.get(workload, "grey")
        out = PLOTS_DIR / "per_bench" / b / f"{short_control(k).replace(':', '_').replace('/', '_')}.png"
        if plot_per_bench_control(b, k, levels, stats, baseline, color, out):
            n_per_bench += 1
    print(f"per_bench panels: {n_per_bench} PNGs in {PLOTS_DIR}/per_bench/")

    # 2) Cross-bench overlay per control
    n_cross = 0
    for k in controls:
        by_bench_levels = {}
        for (b, kk), levels in levels_by_bench_knob.items():
            if kk == k:
                by_bench_levels[b] = levels
        out = PLOTS_DIR / "per_control" / f"{short_control(k).replace(':', '_').replace('/', '_')}.png"
        if plot_cross_bench_control(k, by_bench_levels, stats, out):
            n_cross += 1
    print(f"per_control overlays: {n_cross} PNGs in {PLOTS_DIR}/per_control/")

    # 3) Index markdown
    index = PLOTS_DIR / "index.md"
    lines = ["# Response-curve plots\n",
             f"Generated from `{CELLS_CSV.name}` ({len(cells)} cells, ~10 repeats per cell).\n",
             "\n## Per-control cross-bench overlays\n",
             "Compare how each control responds across the 7 workload classes.\n"]
    for k in controls:
        png = f"per_control/{short_control(k).replace(':', '_').replace('/', '_')}.png"
        if (PLOTS_DIR / png).exists():
            lines.append(f"### {k}\n")
            lines.append(f"![{k}]({png})\n")
    lines.append("\n## Per-(bench, control) detail panels\n")
    for b in benches:
        lines.append(f"\n### {b}\n")
        for k in controls:
            png = f"per_bench/{b}/{short_control(k).replace(':', '_').replace('/', '_')}.png"
            if (PLOTS_DIR / png).exists():
                lines.append(f"![{b} {k}]({png})\n")
    index.write_text("\n".join(lines), encoding="utf-8")
    print(f"index: {index}")


if __name__ == "__main__":
    main()
