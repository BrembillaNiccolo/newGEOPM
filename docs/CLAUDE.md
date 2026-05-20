# docs/

Design documents and reference material. Living docs — update as Phase 1 results land.

## What's here

| File | Purpose | Owner phase |
|------|---------|-------------|
| `geopm-aurora.md` | GEOPM signal/control inventory specific to Aurora. The agent's source of truth. | Phase 0; updated whenever an open question resolves |
| `signals_and_controls/` | **Raw `geopmread/geopmwrite --info` dumps from Aurora.** Primary source for `geopm-aurora.md`. Reread when in doubt. | captured 2026-05-20 |
| `phase1-sweep-design.md` | Per-benchmark knob grids, repeats, output schema | Phase 0 |
| `agent-design.md` | Unified agent: features, actions, reward, LinUCB warm-start | Phase 0; revised after Phase 1 |
| `phase3-cap-design.md` | 3000 W cap experiment design | Phase 0 |
| `open-questions.md` | Things to verify on Aurora before relying on them | live; append resolutions |
| `glossary.md` | Terms (PVC, PL1/PL2, EDP, IPS, etc.) | live |

## Conventions

- Markdown only; no JSON/YAML data here (those go in `experiments/`).
- Cross-reference between docs by relative path (`docs/x.md` → `[x](x.md)` or `[../docs/x.md](../docs/x.md)`).
- When a signal or control name appears, spell it **exactly** as GEOPM does (case-sensitive in PIO).
- When updating after a verification on Aurora, append to the doc's "resolution log" if it has one (e.g. `open-questions.md`).

## Style

- Be specific. "verify on Aurora" tasks list the exact `geopmread`/`geopmwrite` command to run.
- Prefer tables to bullet lists when comparing options.
- Don't duplicate content across docs; link instead.
