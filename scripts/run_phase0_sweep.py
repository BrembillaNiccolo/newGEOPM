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
import signal
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


_domain_count_cache: Dict[str, int] = {}


def _discover_domain_counts_from_geopm() -> Dict[str, int]:
    """Ask `geopmread --domain` for the real per-domain instance counts.

    Output format example:
        board                     1
        package                   2
        core                    104
        cpu                     208
        gpu                       6
        gpu_chip                 12
    """
    invocation = geopm_tool_invocation("geopmread") if "geopm_tool_invocation" in globals() else None
    if invocation is None:
        invocation = ["geopmread"]  # best-effort
    try:
        proc = subprocess.run(
            invocation + ["--domain"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=10, check=False,
        )
        if proc.returncode != 0:
            return {}
        result = {}
        for line in proc.stdout.splitlines():
            parts = line.strip().split()
            if len(parts) == 2 and parts[1].isdigit():
                result[parts[0]] = int(parts[1])
        return result
    except Exception:
        return {}


def domain_count(domain: str) -> int:
    # 1) explicit env override always wins
    env_name = DOMAIN_COUNT_ENV.get(domain)
    if env_name and os.environ.get(env_name):
        return int(os.environ[env_name])
    # 2) cached geopmread --domain result
    if not _domain_count_cache:
        _domain_count_cache.update(_discover_domain_counts_from_geopm())
    if domain in _domain_count_cache:
        return _domain_count_cache[domain]
    # 3) static fallbacks (Aurora-shaped). NOTE: "core" used to fall back to
    #    os.cpu_count() which returns logical CPUs (208 on Xeon Max with HT),
    #    causing geopmread to fail on core 104+. We now divide cpu by 2 as
    #    a "probably right" heuristic when both geopmread and the env var are
    #    unavailable.
    cpu_n = max(1, os.cpu_count() or 1)
    fallback = {
        "board": 1, "package": 2,
        "cpu": cpu_n,
        "core": cpu_n // 2,    # assume 2-way SMT; better than 208 cores
        "gpu": 6, "gpu_chip": 12,
    }
    return fallback.get(domain, DOMAIN_COUNT_DEFAULT.get(domain, 1))


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
        errors = []  # type: List[Dict[str, Any]]
        min_floor_writes = []  # type: List[Dict[str, Any]]

        # If the knob declares a min_control, drop that MIN_CONTROL to its floor
        # across all instances BEFORE writing MAX. Otherwise MAX writes below the
        # current MIN are silently clamped by the driver (verified on Aurora:
        # GPU_CORE_FREQUENCY_MIN_CONTROL pinned MAX writes < 1.5 GHz to 1.5 GHz).
        # Originals are pushed onto restore_values so the cleanup pass restores
        # MAX first (LIFO), then MIN -- the correct order to avoid the inverse
        # clamping problem on restore.
        min_ctl_info = knob.get("min_control")
        if min_ctl_info:
            min_consecutive_failures = 0
            for instance in instances_for(knob):
                try:
                    orig_min = geopm_read(min_ctl_info["name"], knob["domain"], instance)
                except Exception as exc:
                    errors.append({"instance": instance, "phase": "read_min_original",
                                   "min_ctl": min_ctl_info["name"], "error": str(exc)[:200]})
                    min_consecutive_failures += 1
                    if min_consecutive_failures >= 2:
                        break
                    continue
                min_consecutive_failures = 0
                try:
                    geopm_write(min_ctl_info["name"], knob["domain"], instance,
                                float(min_ctl_info["floor_value"]))
                except Exception as exc:
                    errors.append({"instance": instance, "phase": "write_min_floor",
                                   "min_ctl": min_ctl_info["name"], "error": str(exc)[:200]})
                    continue
                self.restore_values.append({
                    "name": min_ctl_info["name"],
                    "domain": knob["domain"],
                    "instance": instance,
                    "value": orig_min,
                })
                min_floor_writes.append({
                    "domain": knob["domain"],
                    "instance": instance,
                    "min_ctl": min_ctl_info["name"],
                    "floor": float(min_ctl_info["floor_value"]),
                    "orig_min": orig_min,
                })

        consecutive_failures = 0
        for instance in instances_for(knob):
            # Per-instance try/except: if e.g. core 104 doesn't exist, log + break.
            # Without this, the first invalid instance kills the whole sweep at
            # this knob and every subsequent knob in sweep.json never runs.
            try:
                original = geopm_read(knob["name"], knob["domain"], instance)
            except Exception as exc:
                errors.append({"instance": instance, "phase": "read_original", "error": str(exc)[:200]})
                consecutive_failures += 1
                # Assume contiguous 0..N-1 indexing: 2 in a row means we're past N.
                if consecutive_failures >= 2:
                    break
                continue
            consecutive_failures = 0
            try:
                value = setting_for_level(level, knob, instance)
            except Exception as exc:
                errors.append({"instance": instance, "phase": "setting_for_level", "error": str(exc)[:200]})
                continue
            if value is None:
                continue
            try:
                geopm_write(knob["name"], knob["domain"], instance, value)
                readback = geopm_read(knob["name"], knob["domain"], instance)
            except Exception as exc:
                errors.append({"instance": instance, "phase": "write_or_readback", "error": str(exc)[:200]})
                continue
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
        entry = {"knob": knob["name"], "level": level["label"], "writes": writes}
        if min_floor_writes:
            entry["min_floor_writes"] = min_floor_writes
        if errors:
            entry["errors"] = errors[:10]  # cap log size
            entry["n_errors"] = len(errors)
        self.write_log.append(entry)

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
        path for path in run_dir.glob("geopmsession_trace.csv*")
        if path.is_file() and not path.name.endswith(".json")
    )
    if not trace_paths:
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
                    header = [part.strip().strip('"') for part in line.split(delimiter)]
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
            elif key == "GPU_ENERGY":
                # Board-level GPU_ENERGY is the SUM across 6 cards -> use it.
                # Per-tile GPU_CORE_ENERGY columns are also in the trace; skip them
                # to avoid double-counting (the card-level GPU_ENERGY already covers
                # the tiles underneath).
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


# Curated telemetry signal set for the geopmsession sidecar trace.
# Each line in geopmsession.signals is "SIGNAL DOMAIN INSTANCE".
# We query at board domain so the trace has one column per signal regardless
# of how many packages/chips exist; geopmsession skips signals it can't read.
PREFERRED_SIDECAR_SIGNALS = (
    "TIME",
    "BOARD_POWER",
    "BOARD_ENERGY",
    "CPU_POWER",
    "CPU_ENERGY",
    "DRAM_POWER",
    "DRAM_ENERGY",
    "GPU_POWER",            # native domain "gpu" (per-card); summed across 6 cards at board
    "GPU_ENERGY",           # native domain "gpu" (per-card); summed at board
    "CPU_FREQUENCY_STATUS",
    "CPU_UNCORE_FREQUENCY_STATUS",
    "CPU_PACKAGE_TEMPERATURE",
)

# Per-tile (gpu_chip) signals: emit one column per tile (12 columns each on Aurora)
# so we can see which tile is busy / hot / drawing energy. Otherwise board-level
# average hides per-tile imbalance and a single idle GPU tile vanishes in the mean.
PER_TILE_SIGNALS = (
    "GPU_UTILIZATION",
    "GPU_CORE_ACTIVITY",
    "GPU_UNCORE_ACTIVITY",
    "GPU_CORE_ENERGY",
    "GPU_CORE_FREQUENCY_STATUS",
)

# Aurora compute node = 6 PVC cards * 2 tiles. Override with GEOPM_DOMAIN_GPU_CHIP_COUNT
# if running on different hardware.
N_GPU_CHIPS_DEFAULT = 12


def _smoke_test_invocation(argv):
    try:
        proc = subprocess.run(
            argv + ["--help"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def geopm_tool_invocation(tool_name):
    """Return argv prefix for invoking a geopm tool that actually runs.

    Aurora ships /usr/bin/geopm{read,write,session} as Python entry-point
    scripts shebanged `#!/usr/bin/python3` (Python 3.6.15). With geopm modules
    loaded, PYTHONPATH includes setuptools built for Python 3.10 (walrus
    operator) so the shebang crashes with SyntaxError. Bypassing via the
    current interpreter (python/3.10.14 module) works there. On a stock
    environment without modules the bypass can fail because the loaded
    interpreter can't find the geopmdpy package - so probe both and pick
    whichever responds to --help.
    """
    path = shutil.which(tool_name)
    if path is None:
        return None
    candidates = []
    try:
        with open(path, "rb") as stream:
            head = stream.read(64)
        if head.startswith(b"#!") and b"python" in head:
            candidates.append([sys.executable, path])
    except OSError:
        pass
    candidates.append([path])
    for argv in candidates:
        if _smoke_test_invocation(argv):
            return argv
    return candidates[-1]  # Last-resort: return something so callers can attempt and log errors


def discover_readable_signals(candidates, domain="board", instance="0"):
    """Probe geopmread at the given domain:instance for each candidate; return the rc=0 ones."""
    invocation = geopm_tool_invocation("geopmread")
    if invocation is None:
        return []
    ok = []
    for sig in candidates:
        try:
            proc = subprocess.run(
                invocation + [sig, domain, str(instance)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if proc.returncode == 0:
                ok.append(sig)
        except (subprocess.TimeoutExpired, Exception):
            continue
    return ok


def write_signals_file(path, board_signals, per_tile_signals=None, n_gpu_chips=N_GPU_CHIPS_DEFAULT):
    """Write a geopmsession signals file.

    `board_signals`: list of signal names queried at board:0 (one column each).
    `per_tile_signals`: list of signal names queried at gpu_chip:0..n-1
                       (n_gpu_chips columns each).
    """
    per_tile_signals = per_tile_signals or []
    with path.open("w", encoding="utf-8") as stream:
        if not board_signals and not per_tile_signals:
            # Always include TIME so the trace at least has timestamps.
            stream.write("TIME board 0\n")
            return
        for sig in board_signals:
            stream.write(f"{sig} board 0\n")
        for sig in per_tile_signals:
            for chip in range(n_gpu_chips):
                stream.write(f"{sig} gpu_chip {chip}\n")


def geopmsession_available():
    """True only if geopmsession actually runs (smoke-tests --help).

    On Aurora, /usr/bin/geopmsession can be present but broken because the
    Python `geopmdpy` package isn't installed for the current interpreter
    (module hierarchy conflict: py-geopmdpy/3.2.2 needs oneapi/release/2025.3.1
    but our default stack uses oneapi/release/2025.2.0). Smoke-test rather
    than trust shutil.which().
    """
    invocation = geopm_tool_invocation("geopmsession")
    if invocation is None:
        return False
    return _smoke_test_invocation(invocation)


def start_geopmsession_sidecar(run_dir, period, bench_pid, signal_names, per_tile_signals=None, n_gpu_chips=N_GPU_CHIPS_DEFAULT):
    signals_path = run_dir / "geopmsession.signals"
    write_signals_file(signals_path, signal_names, per_tile_signals, n_gpu_chips)
    invocation = geopm_tool_invocation("geopmsession") or ["geopmsession"]
    cmd = invocation + [
        "-i", str(signals_path),
        "-p", f"{period:.6f}",
        "--pid", str(bench_pid),
        "-o", str(run_dir / "geopmsession_trace.csv"),
        "-r", str(run_dir / "geopmsession_report.yaml"),
    ]
    stdout_log = (run_dir / "geopmsession.stdout").open("w", encoding="utf-8")
    stderr_log = (run_dir / "geopmsession.stderr").open("w", encoding="utf-8")
    proc = subprocess.Popen(cmd, stdout=stdout_log, stderr=stderr_log, text=True)
    return proc, stdout_log, stderr_log, cmd


def stop_geopmsession_sidecar(proc, stdout_log, stderr_log, natural_exit_timeout=10):
    """Let geopmsession exit naturally first; only SIGTERM as fallback.

    geopmsession with --pid exits on its own once the tracked bench dies, and
    that natural-exit path is the only one that produces the YAML summary
    report (`-r FILE`). SIGTERM flushes the trace.csv buffer but skips the
    report write. So we wait up to `natural_exit_timeout` seconds for the
    --pid detector to fire, then escalate to SIGTERM then SIGKILL.
    """
    if proc.poll() is None:
        try:
            proc.wait(timeout=natural_exit_timeout)
        except subprocess.TimeoutExpired:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
    stdout_log.close()
    stderr_log.close()
    return proc.returncode


def build_walker_schedule(sweep, interval_s):
    flips = []
    for knob in sweep["knobs"]:
        for level in knob["levels"]:
            if level.get("kind") == "default":
                continue
            flips.append({"knob": knob, "level": level})
    return {"interval_s": interval_s, "flips": flips, "loop": False}


def start_knob_walker(args, sweep, run_dir):
    if args.knob_walker == "auto":
        schedule = build_walker_schedule(sweep, args.knob_walker_interval_s)
    else:
        schedule = json.loads(Path(args.knob_walker).read_text(encoding="utf-8"))
    schedule_path = run_dir / "knob_walker_schedule.json"
    dump_json(schedule_path, schedule)

    walker_cmd = [
        sys.executable,
        str(Path(__file__).with_name("knob_walker.py")),
        "--schedule", str(schedule_path),
        "--run-dir", str(run_dir),
        "--interval-s", f"{args.knob_walker_interval_s}",
    ]
    if args.apply_controls:
        walker_cmd.append("--apply-controls")

    stdout_log = (run_dir / "knob_walker.stdout").open("w", encoding="utf-8")
    stderr_log = (run_dir / "knob_walker.stderr").open("w", encoding="utf-8")
    walker = subprocess.Popen(walker_cmd, stdout=stdout_log, stderr=stderr_log, text=True)
    return walker, stdout_log, stderr_log


def stop_knob_walker(walker, stdout_log, stderr_log):
    if walker.poll() is None:
        walker.send_signal(signal.SIGTERM)
        try:
            walker.wait(timeout=60)
        except subprocess.TimeoutExpired:
            walker.kill()
            walker.wait(timeout=10)
    stdout_log.close()
    stderr_log.close()


def run_cell(args, registry, sweep, knob, level, variant_name, repeat):
    bench = sweep["benchmark"]
    entry = registry["benchmarks"][bench]
    variant = entry["variants"][variant_name]

    run_root = Path(args.run_root or f"experiments/phase1/{bench}/runs")
    if args.run_tag:
        safe_tag = args.run_tag.replace("/", "_")
        run_root = run_root / safe_tag
    cell_id = f"{variant_name}__{knob['name']}__{level['label']}__r{repeat}"
    safe_cell_id = cell_id.replace(":", "_").replace("/", "_")
    run_dir = run_root / safe_cell_id
    if args.clean and run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Plain mpiexec for the bench in both monitor and non-monitor modes.
    # Monitor mode wraps with a geopmsession sidecar (started after bench Popen).
    command, env = build_plain_command(entry, variant)
    sidecar_enabled = bool(args.geopm_monitor) and geopmsession_available()
    sidecar_skipped_reason = ""
    if args.geopm_monitor and not sidecar_enabled:
        sidecar_skipped_reason = "geopmsession not on PATH; running bench without telemetry sidecar"

    # When --knob-walker is active, the walker owns knob control; the per-cell
    # GeopmControlSession is bypassed so the two don't fight over geopmwrite.
    walker_driven = args.knob_walker is not None
    control_session = GeopmControlSession(args.apply_controls and not walker_driven)
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
        "sidecar_enabled": sidecar_enabled,
        "sidecar_skipped_reason": sidecar_skipped_reason,
        "knob_walker": walker_driven,
        "knob_walker_interval_s": args.knob_walker_interval_s if walker_driven else None,
    }
    dump_json(run_dir / "meta.json", meta)

    start = time.monotonic()
    return_code = -999
    stdout = ""
    stderr = ""
    restored = []  # type: List[Dict[str, Any]]
    walker = None
    walker_stdout = None
    walker_stderr = None
    sidecar = None
    sidecar_stdout = None
    sidecar_stderr = None
    sidecar_cmd = None
    sidecar_rc = None
    try:
        control_session.apply(knob, level)
        if walker_driven:
            walker, walker_stdout, walker_stderr = start_knob_walker(args, sweep, run_dir)
        if args.dry_run:
            # Give the walker a chance to log at least one flip even in dry-run.
            if walker_driven:
                time.sleep(max(1.0, args.knob_walker_interval_s))
            return_code = 0
            stdout = "dry_run=1\n"
        else:
            bench = None
            try:
                bench_stdout_path = run_dir / "stdout.log"
                bench_stderr_path = run_dir / "stderr.log"
                with bench_stdout_path.open("w", encoding="utf-8") as out_f, \
                     bench_stderr_path.open("w", encoding="utf-8") as err_f:
                    bench = subprocess.Popen(command, env=env, stdout=out_f, stderr=err_f, text=True)
                    if sidecar_enabled:
                        sidecar, sidecar_stdout, sidecar_stderr, sidecar_cmd = \
                            start_geopmsession_sidecar(
                                run_dir, args.geopm_period, bench.pid,
                                args._sidecar_signals,
                                args._sidecar_per_tile_signals,
                                args._sidecar_n_gpu_chips,
                            )
                    try:
                        return_code = bench.wait()
                    except KeyboardInterrupt:
                        # Interrupt during bench: terminate bench cleanly so subsequent
                        # processing (and the sidecar's SIGTERM in `finally`) still produces
                        # the geopmsession YAML report for whatever was sampled.
                        if bench.poll() is None:
                            bench.send_signal(signal.SIGTERM)
                            try:
                                return_code = bench.wait(timeout=30)
                            except subprocess.TimeoutExpired:
                                bench.kill()
                                return_code = bench.wait(timeout=10)
                        raise  # let main() see the interrupt
                stdout = bench_stdout_path.read_text(encoding="utf-8", errors="replace")
                stderr = bench_stderr_path.read_text(encoding="utf-8", errors="replace")
            except FileNotFoundError as exc:
                return_code = 127
                stderr = f"executable not found: {exc}\n"
            except KeyboardInterrupt:
                # re-raise after the with-block has closed the bench output files
                stdout = bench_stdout_path.read_text(encoding="utf-8", errors="replace") if bench_stdout_path.exists() else ""
                stderr = (bench_stderr_path.read_text(encoding="utf-8", errors="replace") if bench_stderr_path.exists() else "") + "\n[interrupted by signal]\n"
                raise
            except Exception as exc:
                return_code = -2
                stderr = f"launch error: {type(exc).__name__}: {exc}\n"
    finally:
        if sidecar is not None:
            sidecar_rc = stop_geopmsession_sidecar(sidecar, sidecar_stdout, sidecar_stderr)
        if walker is not None:
            stop_knob_walker(walker, walker_stdout, walker_stderr)
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
        "sidecar_command": format_command(sidecar_cmd) if sidecar_cmd else "",
        "sidecar_returncode": sidecar_rc,
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
    parser.add_argument("--run-tag", default="",
                        help="Optional subfolder under runs/ to isolate this submission's cells "
                             "(e.g. PBS job id). Lets you keep multiple runs and average across them.")
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
    parser.add_argument("--knob-walker", nargs="?", const="auto", default=None,
                        help="Run scripts/knob_walker.py alongside the benchmark. "
                             "Pass a schedule.json path, or omit value for 'auto' "
                             "(derive schedule from sweep.json non-default levels).")
    parser.add_argument("--knob-walker-interval-s", type=float, default=5.0,
                        help="Seconds to hold each knob flip when --knob-walker is active")
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

    # Resolve include_knobs: prepend the shared list's knobs to any per-sweep ones.
    include_ref = sweep.get("include_knobs")
    if include_ref:
        include_path = (sweep_path.parent / include_ref).resolve()
        included = load_json(include_path)
        sweep["knobs"] = list(included.get("knobs", [])) + list(sweep.get("knobs", []))
        sweep["_include_knobs_resolved"] = str(include_path)

    # One-shot signal discovery for the sidecar. Probe board signals at board:0 and
    # per-tile signals at gpu_chip:0; keep only the readable ones so geopmsession
    # doesn't bail on unknown names.
    args._sidecar_signals = []
    args._sidecar_per_tile_signals = []
    args._sidecar_n_gpu_chips = int(os.environ.get("GEOPM_DOMAIN_GPU_CHIP_COUNT", N_GPU_CHIPS_DEFAULT))
    if args.geopm_monitor and geopmsession_available():
        args._sidecar_signals = discover_readable_signals(PREFERRED_SIDECAR_SIGNALS)
        args._sidecar_per_tile_signals = discover_readable_signals(PER_TILE_SIGNALS, "gpu_chip", 0)
        total_cols = len(args._sidecar_signals) + len(args._sidecar_per_tile_signals) * args._sidecar_n_gpu_chips
        print(f"[sidecar] geopmsession will sample:")
        print(f"           board signals     {len(args._sidecar_signals)}/{len(PREFERRED_SIDECAR_SIGNALS)} : {args._sidecar_signals}")
        print(f"           per-tile signals  {len(args._sidecar_per_tile_signals)}/{len(PER_TILE_SIGNALS)} x {args._sidecar_n_gpu_chips} tiles : {args._sidecar_per_tile_signals}")
        print(f"           -> {total_cols} trace columns per row")

    # Convert SIGTERM/SIGINT into KeyboardInterrupt so per-cell `finally` blocks run.
    # That ensures: (1) the sidecar gets a clean SIGTERM and flushes its YAML report,
    # (2) any written knobs get restored, and (3) the partial summary CSV is still saved.
    # Without this, default SIGTERM kills Python before any cleanup -> orphan sidecar,
    # no YAML, no knob restore.
    def _shutdown_signal(signum, _frame):
        raise KeyboardInterrupt(f"received signal {signum}")
    signal.signal(signal.SIGTERM, _shutdown_signal)
    signal.signal(signal.SIGINT, _shutdown_signal)

    rows = []
    interrupted = False
    try:
        for knob, level, variant, repeat in iter_cells(args, sweep):
            print(f"[cell] {args.benchmark} variant={variant} knob={knob['name']} level={level['label']} repeat={repeat}")
            try:
                row = run_cell(args, registry, sweep, knob, level, variant, repeat)
            except KeyboardInterrupt:
                interrupted = True
                print("[interrupt] received SIGTERM/SIGINT mid-cell; current cell's sidecar was given SIGTERM and YAML should be flushed.", file=sys.stderr)
                break
            print(f"[done] rc={row['returncode']} runtime_s={row['runtime_s']} dir={row['run_dir']}")
            rows.append(row)
            if row["returncode"] != 0:
                print(f"[warn] non-zero return code for {row['run_dir']}", file=sys.stderr)
    finally:
        summary_path = Path(args.summary_csv) if args.summary_csv else Path(f"experiments/phase1/{args.benchmark}/last_run_summary.csv")
        write_summary_csv(summary_path, rows)
        print(f"[summary] {summary_path} ({'partial; interrupted' if interrupted else 'complete'})")
    return 130 if interrupted else (0 if all(row["returncode"] == 0 for row in rows) else 1)


if __name__ == "__main__":
    raise SystemExit(main())
