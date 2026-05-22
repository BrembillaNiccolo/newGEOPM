#!/usr/bin/env python3
"""Sidecar that flips GEOPM knobs on a fixed cadence while a benchmark runs.

Reads a JSON schedule (list of (knob, level) flips), applies them in order
holding each for `interval_s`, logs every apply/restore to CSV, and always
restores originals on exit (SIGTERM/SIGINT/exception). In `--apply-controls`
mode it actually calls geopmread/geopmwrite; otherwise it logs `dry_run`
rows and keeps the same timing so traces line up with a real run.
"""

import argparse
import csv
import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_phase0_sweep as rps  # noqa: E402  (sys.path manipulation above)


LOG_FIELDS = [
    "t_unix_s",
    "t_wall_iso",
    "action",
    "knob",
    "domain",
    "instance",
    "requested",
    "readback",
    "status",
    "note",
]


def load_schedule(path):
    if path == "-":
        return json.loads(sys.stdin.read())
    return json.loads(Path(path).read_text(encoding="utf-8"))


def now_pair():
    t = time.time()
    return t, datetime.fromtimestamp(t, tz=timezone.utc).isoformat()


class WalkerLog:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self._stream = csv_path.open("w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._stream, fieldnames=LOG_FIELDS)
        self._writer.writeheader()
        self._stream.flush()

    def append(self, **row):
        full = {key: "" for key in LOG_FIELDS}
        full.update(row)
        self._writer.writerow(full)
        self._stream.flush()

    def close(self):
        self._stream.close()


def apply_flip(flip, idx, apply_controls, log, restore_stack, stop_flag):
    knob = flip["knob"]
    level = flip["level"]
    note = f"flip[{idx}]"
    is_default = level.get("kind") == "default"

    for instance in rps.instances_for(knob):
        if stop_flag["stop"]:
            return
        t_unix, t_iso = now_pair()
        original = None
        if apply_controls:
            try:
                original = rps.geopm_read(knob["name"], knob["domain"], instance)
            except Exception as exc:
                log.append(
                    t_unix_s=t_unix, t_wall_iso=t_iso, action="apply",
                    knob=knob["name"], domain=knob["domain"], instance=instance,
                    requested="", readback="", status="read_error",
                    note=f"{note}: {exc}",
                )
                continue

        if is_default:
            log.append(
                t_unix_s=t_unix, t_wall_iso=t_iso, action="apply",
                knob=knob["name"], domain=knob["domain"], instance=instance,
                requested="default", readback="" if original is None else original,
                status="ok" if apply_controls else "dry_run", note=note,
            )
            continue

        try:
            value = rps.setting_for_level(level, knob, instance)
        except Exception as exc:
            log.append(
                t_unix_s=t_unix, t_wall_iso=t_iso, action="apply",
                knob=knob["name"], domain=knob["domain"], instance=instance,
                requested="", readback="", status="compute_error",
                note=f"{note}: {exc}",
            )
            continue

        if not apply_controls:
            log.append(
                t_unix_s=t_unix, t_wall_iso=t_iso, action="apply",
                knob=knob["name"], domain=knob["domain"], instance=instance,
                requested=value, readback="", status="dry_run", note=note,
            )
            continue

        try:
            rps.geopm_write(knob["name"], knob["domain"], instance, value)
            readback = rps.geopm_read(knob["name"], knob["domain"], instance)
            status = "ok"
        except Exception as exc:
            readback = ""
            status = "write_error"
            log.append(
                t_unix_s=t_unix, t_wall_iso=t_iso, action="apply",
                knob=knob["name"], domain=knob["domain"], instance=instance,
                requested=value, readback=readback, status=status,
                note=f"{note}: {exc}",
            )
            continue

        restore_stack.append({
            "name": knob["name"],
            "domain": knob["domain"],
            "instance": instance,
            "original": original,
        })
        log.append(
            t_unix_s=t_unix, t_wall_iso=t_iso, action="apply",
            knob=knob["name"], domain=knob["domain"], instance=instance,
            requested=value, readback=readback, status=status, note=note,
        )


def restore_all(restore_stack, log, apply_controls):
    results = []
    if not apply_controls:
        return results
    for item in reversed(restore_stack):
        t_unix, t_iso = now_pair()
        try:
            rps.geopm_write(item["name"], item["domain"], item["instance"], item["original"])
            status = "ok"
            note = ""
        except Exception as exc:
            status = "restore_failed"
            note = str(exc)
        log.append(
            t_unix_s=t_unix, t_wall_iso=t_iso, action="restore",
            knob=item["name"], domain=item["domain"], instance=item["instance"],
            requested=item["original"], readback="", status=status, note=note,
        )
        results.append({**item, "status": status, "note": note})
    return results


def sleep_with_stop(seconds, stop_flag, slice_s=0.1):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if stop_flag["stop"]:
            return
        time.sleep(min(slice_s, end - time.monotonic()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", required=True,
                        help="Path to schedule JSON, or '-' for stdin")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--apply-controls", action="store_true")
    parser.add_argument("--interval-s", type=float, default=None,
                        help="Override interval_s from the schedule")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    args.run_dir.mkdir(parents=True, exist_ok=True)
    schedule = load_schedule(args.schedule)
    flips = schedule.get("flips", [])
    interval_s = args.interval_s if args.interval_s is not None else float(schedule.get("interval_s", 5.0))
    loop = bool(schedule.get("loop", False))

    log = WalkerLog(args.run_dir / "knob_walker_log.csv")
    restore_stack = []
    stop_flag = {"stop": False}

    def _handle_signal(signum, _frame):
        if not args.quiet:
            print(f"[knob_walker] received signal {signum}, stopping", file=sys.stderr)
        stop_flag["stop"] = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    started_unix, started_iso = now_pair()
    n_applied = 0
    err = None
    try:
        idx = 0
        while not stop_flag["stop"]:
            if idx >= len(flips):
                if not loop:
                    break
                idx = 0
            apply_flip(flips[idx], idx, args.apply_controls, log, restore_stack, stop_flag)
            n_applied += 1
            if not args.quiet:
                knob_name = flips[idx]["knob"]["name"]
                level_label = flips[idx]["level"].get("label", "?")
                print(f"[knob_walker] applied {knob_name}={level_label} (flip {idx})", file=sys.stderr)
            sleep_with_stop(interval_s, stop_flag)
            idx += 1
    except Exception as exc:
        err = repr(exc)
    finally:
        restore_results = restore_all(restore_stack, log, args.apply_controls)
        log.close()
        finished_unix, finished_iso = now_pair()
        meta = {
            "schedule_path": args.schedule,
            "interval_s": interval_s,
            "loop": loop,
            "apply_controls": args.apply_controls,
            "n_flips_in_schedule": len(flips),
            "n_applied": n_applied,
            "n_restored": len(restore_results),
            "restore_errors": [r for r in restore_results if r["status"] != "ok"],
            "started_unix": started_unix,
            "started_iso": started_iso,
            "finished_unix": finished_unix,
            "finished_iso": finished_iso,
            "stopped_by_signal": stop_flag["stop"],
            "exception": err,
        }
        (args.run_dir / "knob_walker_meta.json").write_text(
            json.dumps(meta, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )

    return 0 if err is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
