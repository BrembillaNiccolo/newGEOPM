#!/usr/bin/env python3
"""Run a small Phase 0/1 benchmark cell and optionally apply GEOPM controls.

The default mode is safe for a laptop/login node: no GEOPM writes, just run the
benchmark and capture metrics. On Aurora, add --apply-controls to test one knob
level with geopmwrite, then restore the values read before the run.
"""

import argparse
import csv
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple


_VAR_WITH_DEFAULT = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*):-([^}]*)\}")


DOMAIN_COUNT_ENV = {
    "board": "GEOPM_DOMAIN_BOARD_COUNT",
    "package": "GEOPM_DOMAIN_PACKAGE_COUNT",
    "core": "GEOPM_DOMAIN_CORE_COUNT",
    "cpu": "GEOPM_DOMAIN_CPU_COUNT",
    "gpu": "GEOPM_DOMAIN_GPU_COUNT",
    "gpu_chip": "GEOPM_DOMAIN_GPU_CHIP_COUNT",
}

DOMAIN_COUNT_DEFAULT = {
    "board": 1,
    "package": 2,
    "core": max(1, os.cpu_count() or 1),
    "cpu": max(1, os.cpu_count() or 1),
    "gpu": 6,
    "gpu_chip": 12,
}


def load_json(path):
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def dump_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_command(args, env=None, check=True):
    return subprocess.run(args, env=env, text=True, capture_output=True, check=check)


def shell_expand(text: str) -> str:
    text = _VAR_WITH_DEFAULT.sub(lambda m: os.environ.get(m.group(1), m.group(2)), text)
    return os.path.expandvars(text)


def split_words(text):
    if not text:
        return []
    return [shell_expand(token) for token in shlex.split(text)]


def format_command(tokens):
    return " ".join(shlex.quote(token) for token in tokens)


def domain_count(domain: str) -> int:
    env_name = DOMAIN_COUNT_ENV.get(domain)
    if env_name and os.environ.get(env_name):
        return int(os.environ[env_name])
    return DOMAIN_COUNT_DEFAULT.get(domain, 1)


def instances_for(knob):
    requested = knob.get("instances", "auto")
    domain = knob["domain"]
    if requested == "auto":
        return list(range(domain_count(domain)))
    if isinstance(requested, int):
        return [requested]
    if isinstance(requested, list):
        return [int(value) for value in requested]
    raise ValueError(f"Unsupported instances field for {knob['name']}: {requested!r}")


def parse_float(text: str) -> float:
    for token in text.replace(",", " ").split():
        try:
            return float(token)
        except ValueError:
            continue
    raise ValueError(f"No float found in output: {text!r}")


def require_tool(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"{name} not found in PATH")


def geopm_read(name: str, domain: str, instance: int) -> float:
    proc = run_command(["geopmread", name, domain, str(instance)], check=True)
    return parse_float(proc.stdout)


def geopm_write(name: str, domain: str, instance: int, value: float) -> None:
    run_command(["geopmwrite", name, domain, str(instance), f"{value:.12g}"], check=True)


def read_with_fallback(signal: str, domain: str, instance: int) -> float:
    candidates = [(domain, instance)]  # type: List[Tuple[str, int]]
    if domain in {"core", "cpu"}:
        candidates.extend([("package", min(instance, domain_count("package") - 1)), ("cpu", instance)])
    if domain == "gpu_chip":
        candidates.extend([("gpu", min(instance // 2, domain_count("gpu") - 1))])
    candidates.append(("board", 0))

    errors = []  # type: List[str]
    for cand_domain, cand_instance in candidates:
        try:
            return geopm_read(signal, cand_domain, max(0, cand_instance))
        except Exception as exc:  # GEOPM signal domains differ by platform/build.
            errors.append(f"{cand_domain}:{cand_instance}: {exc}")
    raise RuntimeError(f"Could not read {signal}; tried {', '.join(errors)}")


def setting_for_level(level, knob, instance):
    kind = level["kind"]
    domain = knob["domain"]
    if kind == "default":
        return None
    if kind == "literal":
        return float(level["value"])
    if kind == "scale_signal":
        base = read_with_fallback(level["signal"], domain, instance)
        return base * float(level["scale"])
    if kind == "scale_readback":
        base = geopm_read(knob["name"], domain, instance)
        return base * float(level["scale"])
    if kind == "fraction_range":
        lo = read_with_fallback(level["min_signal"], domain, instance)
        hi = read_with_fallback(level["max_signal"], domain, instance)
        return lo + float(level["fraction"]) * (hi - lo)
    raise ValueError(f"Unsupported level kind: {kind}")


class GeopmControlSession:
    def __init__(self, apply_controls: bool):
        self.apply_controls = apply_controls
        self.restore_values = []  # type: List[Dict[str, Any]]
        self.write_log = []  # type: List[Dict[str, Any]]

    def apply(self, knob, level):
        if level["kind"] == "default":
            self.write_log.append({"knob": knob["name"], "level": level["label"], "writes": []})
            return
        if not self.apply_controls:
            self.write_log.append({
                "knob": knob["name"],
                "level": level["label"],
                "skipped": "controls disabled; pass --apply-controls on Aurora",
            })
            return

        require_tool("geopmread")
        require_tool("geopmwrite")

        writes = []  # type: List[Dict[str, Any]]
        for instance in instances_for(knob):
            original = geopm_read(knob["name"], knob["domain"], instance)
            value = setting_for_level(level, knob, instance)
            if value is None:
                continue
            geopm_write(knob["name"], knob["domain"], instance, value)
            readback = geopm_read(knob["name"], knob["domain"], instance)
            self.restore_values.append({
                "name": knob["name"],
                "domain": knob["domain"],
                "instance": instance,
                "value": original,
            })
            writes.append({
                "domain": knob["domain"],
                "instance": instance,
                "requested": value,
                "readback": readback,
            })
        self.write_log.append({"knob": knob["name"], "level": level["label"], "writes": writes})

    def restore(self):
        restored = []  # type: List[Dict[str, Any]]
        if not self.apply_controls:
            return restored
        for item in reversed(self.restore_values):
            try:
                geopm_write(item["name"], item["domain"], item["instance"], item["value"])
                restored.append({**item, "status": "restored"})
            except Exception as exc:
                restored.append({**item, "status": "restore_failed", "error": str(exc)})
        return restored


def parse_key_value_metrics(stdout):
    metrics = {}  # type: Dict[str, Any]
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        try:
            if any(ch in value for ch in ".eE"):
                metrics[key] = float(value)
            else:
                metrics[key] = int(value)
        except ValueError:
            metrics[key] = value
    return metrics


def parse_trace_energy(run_dir):
    trace_paths = sorted(
        path for path in run_dir.glob("trace.csv*")
        if path.is_file() and not path.name.endswith(".json")
    )
    if not trace_paths:
        trace_paths = sorted(run_dir.glob("geopm.trace*"))

    cpu_energy = 0.0
    dram_energy = 0.0
    gpu_energy = 0.0
    board_energy = 0.0
    trace_runtime = 0.0
    parsed_files = 0

    for path in trace_paths:
        header = None
        first = None
        last = None
        with path.open("r", encoding="utf-8", errors="replace") as stream:
            for raw_line in stream:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if header is None:
                    delimiter = "|" if "|" in line else ","
                    header = [part.strip() for part in line.split(delimiter)]
                    continue
                values = line.split(delimiter)
                if len(values) != len(header):
                    continue
                row = {}
                for key, value in zip(header, values):
                    try:
                        row[key] = float(value)
                    except ValueError:
                        pass
                if "TIME" not in row:
                    continue
                if first is None:
                    first = row
                last = row
        if not first or not last:
            continue

        parsed_files += 1
        trace_runtime = max(trace_runtime, last.get("TIME", 0.0) - first.get("TIME", 0.0))
        for key in set(first) & set(last):
            if not key.endswith("ENERGY"):
                continue
            delta = last[key] - first[key]
            if delta < 0:
                continue
            if key == "CPU_ENERGY":
                cpu_energy += delta
            elif key == "DRAM_ENERGY":
                dram_energy += delta
            elif "GPU" in key:
                gpu_energy += delta
            elif key == "BOARD_ENERGY":
                board_energy += delta

    if parsed_files == 0:
        return {}

    component_energy = cpu_energy + dram_energy + gpu_energy
    out = {
        "trace_files": parsed_files,
        "trace_runtime_s": trace_runtime,
        "cpu_energy_j": cpu_energy,
        "dram_energy_j": dram_energy,
        "gpu_energy_j": gpu_energy,
        "component_energy_j": component_energy,
    }
    if board_energy > 0.0:
        out["board_energy_j"] = board_energy
    if component_energy > 0.0:
        out["energy_j"] = component_energy
    elif board_energy > 0.0:
        out["energy_j"] = board_energy
    return out


def build_plain_command(entry, variant):
    env = os.environ.copy()
    env.update({key: shell_expand(value) for key, value in entry.get("default_env", {}).items()})
    env.update({key: shell_expand(value) for key, value in variant.get("env", {}).items()})

    launcher = split_words(variant.get("launcher"))
    prefix = split_words(variant.get("prefix"))
    binary = split_words(entry["binary"])
    args = split_words(variant.get("args"))
    return launcher + prefix + binary + args, env


def build_geopm_monitor_command(entry, variant, run_dir, period):
    env = os.environ.copy()
    env.update({key: shell_expand(value) for key, value in entry.get("default_env", {}).items()})
    env.update({key: shell_expand(value) for key, value in variant.get("env", {}).items()})

    launcher = split_words(variant.get("launcher")) or ["mpiexec", "-n", "1"]
    prefix = split_words(variant.get("prefix"))
    binary = split_words(entry["binary"])
    args = split_words(variant.get("args"))
    return (
        ["geopmlaunch", launcher[0],
         "--geopm-agent=monitor",
         f"--geopm-report={run_dir / 'report.yaml'}",
         f"--geopm-trace={run_dir / 'trace.csv'}",
         f"--geopm-period={period:.6f}",
         "--"]
        + launcher[1:]
        + prefix
        + binary
        + args,
        env,
    )


def run_cell(args, registry, sweep, knob, level, variant_name, repeat):
    bench = sweep["benchmark"]
    entry = registry["benchmarks"][bench]
    variant = entry["variants"][variant_name]

    run_root = Path(args.run_root or f"experiments/phase1/{bench}/runs")
    cell_id = f"{variant_name}__{knob['name']}__{level['label']}__r{repeat}"
    safe_cell_id = cell_id.replace(":", "_").replace("/", "_")
    run_dir = run_root / safe_cell_id
    if args.clean and run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.geopm_monitor:
        command, env = build_geopm_monitor_command(entry, variant, run_dir, args.geopm_period)
    else:
        command, env = build_plain_command(entry, variant)

    control_session = GeopmControlSession(args.apply_controls)
    meta = {  # type: Dict[str, Any]
        "benchmark": bench,
        "workload_type": entry["workload_type"],
        "variant": variant_name,
        "knob": knob["name"],
        "knob_domain": knob["domain"],
        "knob_reason": knob.get("reason", ""),
        "level": level,
        "repeat": repeat,
        "runtime_slack": sweep.get("runtime_slack"),
        "command": format_command(command),
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "host": platform.node(),
        "platform": platform.platform(),
        "apply_controls": args.apply_controls,
        "geopm_monitor": args.geopm_monitor,
    }
    dump_json(run_dir / "meta.json", meta)

    start = time.monotonic()
    return_code = -999
    stdout = ""
    stderr = ""
    restored = []  # type: List[Dict[str, Any]]
    try:
        control_session.apply(knob, level)
        if args.dry_run:
            return_code = 0
            stdout = "dry_run=1\n"
        else:
            proc = subprocess.run(command, env=env, text=True, capture_output=True)
            return_code = proc.returncode
            stdout = proc.stdout
            stderr = proc.stderr
    finally:
        restored = control_session.restore()

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
        "control_writes": control_session.write_log,
        "control_restore": restored,
        "metrics_path": str(run_dir / "metrics.json"),
    })
    dump_json(run_dir / "meta.json", meta)

    summary = {
        "run_dir": str(run_dir),
        "benchmark": bench,
        "workload_type": entry["workload_type"],
        "variant": variant_name,
        "knob": knob["name"],
        "level": level["label"],
        "repeat": repeat,
        "returncode": return_code,
        "runtime_s": metrics.get("runtime_s", ""),
        "energy_j": metrics.get("energy_j", ""),
        "component_energy_j": metrics.get("component_energy_j", ""),
        "wall_clock_s": elapsed,
        "avg_gflops": metrics.get("avg_gflops", ""),
        "best_gflops": metrics.get("best_gflops", ""),
    }
    return summary


def iter_cells(args, sweep):
    variants = [args.variant] if args.variant else sweep["variants"]
    cells = []  # type: List[Tuple[Dict[str, Any], Dict[str, Any], str, int]]
    for knob in sweep["knobs"]:
        if args.knob and knob["name"] != args.knob:
            continue
        for level in knob["levels"]:
            if args.level and level["label"] != args.level:
                continue
            for variant in variants:
                repeat_range = [args.repeat] if args.repeat is not None else range(sweep.get("repeats", 1))
                for repeat in repeat_range:
                    cells.append((knob, level, variant, int(repeat)))
    if args.max_cells is not None:
        cells = cells[:args.max_cells]
    return cells


def write_summary_csv(path, rows):
    if not rows:
        return
    keys = list(rows[0].keys())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("benchmark", help="Benchmark name from benchmarks/registry.json")
    parser.add_argument("--registry", default="benchmarks/registry.json")
    parser.add_argument("--sweep", help="Sweep JSON path; default experiments/phase1/<benchmark>/sweep.json")
    parser.add_argument("--run-root", help="Override runs output directory")
    parser.add_argument("--variant", help="Run only one variant")
    parser.add_argument("--knob", help="Run only one knob")
    parser.add_argument("--level", help="Run only one level label")
    parser.add_argument("--repeat", type=int, help="Run only one repeat index")
    parser.add_argument("--max-cells", type=int, help="Limit number of cells, useful for smoke tests")
    parser.add_argument("--clean", action="store_true", help="Delete an existing cell directory before running")
    parser.add_argument("--dry-run", action="store_true", help="Write metadata without launching benchmark")
    parser.add_argument("--apply-controls", action="store_true", help="Actually write GEOPM controls with geopmwrite")
    parser.add_argument("--geopm-monitor", action="store_true", help="Wrap run in geopmlaunch monitor and emit trace/report")
    parser.add_argument("--geopm-period", type=float, default=0.02)
    parser.add_argument("--summary-csv", default="", help="Optional path for a CSV summary of launched cells")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)

    registry = load_json(Path(args.registry))
    if args.benchmark not in registry["benchmarks"]:
        known = ", ".join(sorted(registry["benchmarks"]))
        raise SystemExit(f"Unknown benchmark {args.benchmark!r}. Known: {known}")

    sweep_path = Path(args.sweep or f"experiments/phase1/{args.benchmark}/sweep.json")
    sweep = load_json(sweep_path)
    if sweep["benchmark"] != args.benchmark:
        raise SystemExit(f"Sweep file {sweep_path} is for {sweep['benchmark']}, not {args.benchmark}")

    rows = []
    for knob, level, variant, repeat in iter_cells(args, sweep):
        print(f"[cell] {args.benchmark} variant={variant} knob={knob['name']} level={level['label']} repeat={repeat}")
        row = run_cell(args, registry, sweep, knob, level, variant, repeat)
        print(f"[done] rc={row['returncode']} runtime_s={row['runtime_s']} dir={row['run_dir']}")
        rows.append(row)
        if row["returncode"] != 0:
            print(f"[warn] non-zero return code for {row['run_dir']}", file=sys.stderr)

    summary_path = Path(args.summary_csv) if args.summary_csv else Path(f"experiments/phase1/{args.benchmark}/last_run_summary.csv")
    write_summary_csv(summary_path, rows)
    print(f"[summary] {summary_path}")
    return 0 if all(row["returncode"] == 0 for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
