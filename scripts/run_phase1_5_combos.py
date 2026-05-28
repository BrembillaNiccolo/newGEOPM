#!/usr/bin/env python3
"""Run Phase 1.5 knob-combination cells for one benchmark.

Each cell = one combo (a list of (knob, value) writes) applied as a single
tuple, then the benchmark runs once with the geopmsession sidecar capturing
per-tick telemetry.

Differs from scripts/run_phase0_sweep.py in two ways:
  1. Cells iterate over the combos list in experiments/phase1_5/combos.json
     rather than the (knob, level) cross-product in strict_knobs.json.
  2. Min-control floors are dropped once before each combo's writes if any
     write touches a *_MAX_CONTROL signal that has a matching *_MIN_CONTROL.

Output layout mirrors Phase 0 so analysis scripts can be reused:
  experiments/phase1_5/<bench>/runs/<RUN_TAG>/<combo_label>__r<repeat>/
"""

import argparse
import json
import os
import platform
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Reuse the well-tested utilities from the Phase 0 runner.
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from run_phase0_sweep import (  # noqa: E402
    build_plain_command,
    discover_readable_signals,
    dump_json,
    format_command,
    geopm_read,
    geopm_tool_invocation,
    geopm_write,
    geopmsession_available,
    load_json,
    parse_key_value_metrics,
    parse_trace_energy,
    require_tool,
    shell_expand,
    start_geopmsession_sidecar,
    stop_geopmsession_sidecar,
    PER_TILE_SIGNALS,
    PREFERRED_SIDECAR_SIGNALS,
    N_GPU_CHIPS_DEFAULT,
    domain_count,
)


def apply_combo(combo, min_floors, apply_controls):
    """Apply one combo's writes. Returns (write_log, restore_list).

    write_log: list of dicts for meta.json.
    restore_list: list of (name, domain, idx, original_value) to write back
                  in reverse on combo end.

    Order of operations per combo:
      1. For every *_MIN_CONTROL listed in min_floors, save its current value
         and write the floor (across all domain instances).
      2. For each write in combo['writes'], save the current MAX value and
         write the combo's requested value.
    Reverse on restore.
    """
    write_log = []
    restore_list = []

    if not apply_controls:
        write_log.append({"combo": combo["label"], "skipped":
                          "controls disabled; pass --apply-controls on Aurora"})
        return write_log, restore_list

    require_tool("geopmread")
    require_tool("geopmwrite")

    combo_knob_names = {w["name"] for w in combo["writes"]}

    # 1. Drop MIN floors (only if any of this combo's writes is a corresponding MAX).
    #    Mapping: CPU_FREQUENCY_MAX_CONTROL -> CPU_FREQUENCY_MIN_CONTROL, etc.
    floor_pairs = {
        "CPU_FREQUENCY_MAX_CONTROL":        "CPU_FREQUENCY_MIN_CONTROL",
        "CPU_UNCORE_FREQUENCY_MAX_CONTROL": "CPU_UNCORE_FREQUENCY_MIN_CONTROL",
        "GPU_CORE_FREQUENCY_MAX_CONTROL":   "GPU_CORE_FREQUENCY_MIN_CONTROL",
    }
    needed_min_ctls = {floor_pairs[k] for k in combo_knob_names if k in floor_pairs}

    for floor in min_floors:
        if floor["name"] not in needed_min_ctls:
            continue
        n = domain_count(floor["domain"])
        instances = list(range(n)) if n else [0]
        for inst in instances:
            try:
                orig = geopm_read(floor["name"], floor["domain"], inst)
                geopm_write(floor["name"], floor["domain"], inst,
                            float(floor["value"]))
                restore_list.append({
                    "name": floor["name"],
                    "domain": floor["domain"],
                    "instance": inst,
                    "value": orig,
                    "kind": "min_floor",
                })
                write_log.append({
                    "phase": "min_floor",
                    "knob": floor["name"],
                    "domain": floor["domain"],
                    "instance": inst,
                    "requested": floor["value"],
                    "orig": orig,
                })
            except Exception as exc:
                write_log.append({
                    "phase": "min_floor",
                    "knob": floor["name"],
                    "instance": inst,
                    "error": str(exc)[:200],
                })

    # 2. Apply each MAX write across all instances of its domain.
    for w in combo["writes"]:
        n = domain_count(w["domain"])
        instances = list(range(n)) if n else [0]
        for inst in instances:
            try:
                orig = geopm_read(w["name"], w["domain"], inst)
                geopm_write(w["name"], w["domain"], inst, float(w["value"]))
                readback = geopm_read(w["name"], w["domain"], inst)
                restore_list.append({
                    "name": w["name"],
                    "domain": w["domain"],
                    "instance": inst,
                    "value": orig,
                    "kind": "max",
                })
                write_log.append({
                    "phase": "combo_write",
                    "knob": w["name"],
                    "domain": w["domain"],
                    "instance": inst,
                    "requested": float(w["value"]),
                    "readback": readback,
                    "orig": orig,
                })
            except Exception as exc:
                write_log.append({
                    "phase": "combo_write",
                    "knob": w["name"],
                    "instance": inst,
                    "error": str(exc)[:200],
                })

    return write_log, restore_list


def restore_combo(restore_list, apply_controls):
    """Restore originals in reverse order (LIFO).

    Order matters: combo writes restore FIRST (so MAX returns to its original
    ceiling), THEN min_floor entries restore (so MIN returns to original floor).
    That avoids the inverse clamping problem on the restore path.
    """
    restored = []
    if not apply_controls:
        return restored
    for item in reversed(restore_list):
        try:
            geopm_write(item["name"], item["domain"], item["instance"],
                        item["value"])
            restored.append({**item, "status": "restored"})
        except Exception as exc:
            restored.append({**item, "status": "restore_failed",
                             "error": str(exc)[:200]})
    return restored


def run_cell(args, registry, combos_doc, combo, variant_name, repeat):
    bench = args.benchmark
    entry = registry["benchmarks"][bench]
    variant = entry["variants"][variant_name]

    run_root = Path(args.run_root or f"experiments/phase1_5/{bench}/runs")
    if args.run_tag:
        safe_tag = args.run_tag.replace("/", "_")
        run_root = run_root / safe_tag
    cell_id = f"{combo['label']}__r{repeat}"
    safe_cell_id = cell_id.replace(":", "_").replace("/", "_")
    run_dir = run_root / safe_cell_id
    if args.clean and run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    command, env = build_plain_command(entry, variant)
    sidecar_enabled = bool(args.geopm_monitor) and geopmsession_available()

    meta = {
        "benchmark": bench,
        "workload_type": entry["workload_type"],
        "variant": variant_name,
        "combo_label": combo["label"],
        "class_hint": combo.get("class_hint", ""),
        "block": combo.get("_block", ""),
        "writes_def": combo["writes"],
        "repeat": repeat,
        "command": format_command(command),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "platform": platform.platform(),
        "apply_controls": args.apply_controls,
        "geopm_monitor": args.geopm_monitor,
        "sidecar_enabled": sidecar_enabled,
    }
    dump_json(run_dir / "meta.json", meta)

    start = time.monotonic()
    return_code = -999
    stdout = ""
    stderr = ""
    restored = []
    sidecar = None
    sidecar_stdout = None
    sidecar_stderr = None
    sidecar_cmd = None
    sidecar_rc = None
    write_log = []
    restore_list = []

    try:
        write_log, restore_list = apply_combo(combo,
                                              combos_doc["min_control_floors"],
                                              args.apply_controls)

        if args.dry_run:
            return_code = 0
            stdout = "dry_run=1\n"
        else:
            bench_proc = None
            try:
                bench_stdout_path = run_dir / "stdout.log"
                bench_stderr_path = run_dir / "stderr.log"
                with bench_stdout_path.open("w", encoding="utf-8") as out_f, \
                     bench_stderr_path.open("w", encoding="utf-8") as err_f:
                    bench_proc = subprocess.Popen(command, env=env,
                                                  stdout=out_f, stderr=err_f,
                                                  text=True)
                    if sidecar_enabled:
                        sidecar, sidecar_stdout, sidecar_stderr, sidecar_cmd = \
                            start_geopmsession_sidecar(
                                run_dir, args.geopm_period, bench_proc.pid,
                                args._sidecar_signals,
                                args._sidecar_per_tile_signals,
                                args._sidecar_n_gpu_chips,
                            )
                    try:
                        return_code = bench_proc.wait()
                    except KeyboardInterrupt:
                        if bench_proc.poll() is None:
                            bench_proc.send_signal(signal.SIGTERM)
                            try:
                                return_code = bench_proc.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                bench_proc.kill()
                                return_code = bench_proc.wait(timeout=10)
                        raise
                stdout = bench_stdout_path.read_text(encoding="utf-8",
                                                     errors="replace")
                stderr = bench_stderr_path.read_text(encoding="utf-8",
                                                     errors="replace")
            except FileNotFoundError as exc:
                return_code = 127
                stderr = f"executable not found: {exc}\n"
            except KeyboardInterrupt:
                raise
            except Exception as exc:
                return_code = -2
                stderr = f"launch error: {type(exc).__name__}: {exc}\n"
    finally:
        if sidecar is not None:
            sidecar_rc = stop_geopmsession_sidecar(sidecar, sidecar_stdout,
                                                   sidecar_stderr)
        restored = restore_combo(restore_list, args.apply_controls)

    elapsed = time.monotonic() - start
    (run_dir / "stdout.log").write_text(stdout, encoding="utf-8")
    (run_dir / "stderr.log").write_text(stderr, encoding="utf-8")

    metrics = parse_key_value_metrics(stdout)
    metrics.update(parse_trace_energy(run_dir))
    metrics.setdefault("runtime_s", elapsed)
    metrics["process_returncode"] = return_code
    metrics["wall_clock_s"] = elapsed
    dump_json(run_dir / "metrics.json", metrics)

    meta.update({
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "returncode": return_code,
        "control_writes": write_log,
        "control_restore": restored,
        "metrics_path": str(run_dir / "metrics.json"),
        "sidecar_command": format_command(sidecar_cmd) if sidecar_cmd else "",
        "sidecar_returncode": sidecar_rc,
    })
    dump_json(run_dir / "meta.json", meta)

    return {
        "run_dir": str(run_dir),
        "benchmark": bench,
        "workload_type": entry["workload_type"],
        "variant": variant_name,
        "combo_label": combo["label"],
        "block": combo.get("_block", ""),
        "class_hint": combo.get("class_hint", ""),
        "repeat": repeat,
        "returncode": return_code,
        "runtime_s": metrics.get("runtime_s", ""),
        "energy_j": metrics.get("energy_j", ""),
        "component_energy_j": metrics.get("component_energy_j", ""),
        "wall_clock_s": elapsed,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark")
    parser.add_argument("--registry", default="benchmarks/registry.json")
    parser.add_argument("--combos",   default="experiments/phase1_5/combos.json")
    parser.add_argument("--variant",  default="all_tiles_15s")
    parser.add_argument("--repeats",  type=int, default=10)
    parser.add_argument("--run-root", default="")
    parser.add_argument("--run-tag",  default="")
    parser.add_argument("--combo-label", default="",
                        help="Run only this combo label (e.g. for re-runs)")
    parser.add_argument("--combo-blocks", default="",
                        help="Comma-separated block prefixes to keep "
                             "(e.g. 'B,C,D,E' to skip block A). The combo's "
                             "_block field is split on '_' and the first piece "
                             "is matched. Empty = all blocks.")
    parser.add_argument("--max-cells", type=int, default=None)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply-controls", action="store_true")
    parser.add_argument("--geopm-monitor", action="store_true")
    parser.add_argument("--geopm-period",  type=float, default=0.05)
    parser.add_argument("--summary-csv", default="")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    registry = load_json(Path(args.registry))
    if args.benchmark not in registry["benchmarks"]:
        raise SystemExit(f"Unknown benchmark {args.benchmark!r}. "
                         f"Known: {sorted(registry['benchmarks'])}")
    combos_doc = load_json(Path(args.combos))

    # Phase 1.5b: optional block filter so we can re-run only the missing
    # interaction blocks without re-running Block A.
    # Accept either ',' or ':' as separator. ':' is preferred when this gets
    # passed through qsub -v, because qsub uses comma to separate variables
    # and would otherwise split "COMBO_BLOCKS=B,C" into two assignments.
    if args.combo_blocks:
        sep_chars = "," if "," in args.combo_blocks else ":"
        wanted = {b.strip() for b in args.combo_blocks.replace(":", ",").split(",")
                  if b.strip()}
        before = len(combos_doc["combos"])
        combos_doc["combos"] = [
            c for c in combos_doc["combos"]
            if c.get("_block", "").split("_", 1)[0] in wanted
        ]
        print(f"[filter] --combo-blocks={sorted(wanted)} kept "
              f"{len(combos_doc['combos'])}/{before} combos")

    # One-shot signal discovery (same as Phase 0 runner).
    args._sidecar_signals = []
    args._sidecar_per_tile_signals = []
    args._sidecar_n_gpu_chips = int(os.environ.get(
        "GEOPM_DOMAIN_GPU_CHIP_COUNT", N_GPU_CHIPS_DEFAULT))
    if args.geopm_monitor and geopmsession_available():
        args._sidecar_signals = discover_readable_signals(
            PREFERRED_SIDECAR_SIGNALS)
        args._sidecar_per_tile_signals = discover_readable_signals(
            PER_TILE_SIGNALS, "gpu_chip", 0)

    def _shutdown_signal(signum, _frame):
        raise KeyboardInterrupt(f"received signal {signum}")
    signal.signal(signal.SIGTERM, _shutdown_signal)
    signal.signal(signal.SIGINT, _shutdown_signal)

    rows = []
    interrupted = False
    cells_run = 0
    try:
        for combo in combos_doc["combos"]:
            if args.combo_label and combo["label"] != args.combo_label:
                continue
            for repeat in range(args.repeats):
                if args.max_cells is not None and cells_run >= args.max_cells:
                    break
                cells_run += 1
                print(f"[cell] {args.benchmark} combo={combo['label']} "
                      f"repeat={repeat}")
                try:
                    row = run_cell(args, registry, combos_doc, combo,
                                   args.variant, repeat)
                except KeyboardInterrupt:
                    interrupted = True
                    print("[interrupt] mid-cell; sidecar got SIGTERM, "
                          "report flushed", file=sys.stderr)
                    break
                print(f"[done] rc={row['returncode']} "
                      f"runtime_s={row['runtime_s']} dir={row['run_dir']}")
                rows.append(row)
                if row["returncode"] != 0:
                    print(f"[warn] non-zero return code for {row['run_dir']}",
                          file=sys.stderr)
            if interrupted:
                break
    finally:
        summary_path = (Path(args.summary_csv) if args.summary_csv else
                        Path(f"experiments/phase1_5/{args.benchmark}/"
                             f"last_run_summary.csv"))
        if rows:
            import csv
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            with summary_path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
            print(f"[summary] {summary_path} "
                  f"({'partial; interrupted' if interrupted else 'complete'})")

    return 130 if interrupted else (
        0 if all(r["returncode"] == 0 for r in rows) else 1)


if __name__ == "__main__":
    raise SystemExit(main())
