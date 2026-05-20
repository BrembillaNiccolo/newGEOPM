# analysis/

Per-phase reports + Python analysis / plotting code.

## Planned contents

| Path | Phase | Contents |
|------|-------|----------|
| `phase1-report.md` | 1 | per-class signal detector, ranked knobs, Pareto-frontier table (seeds Phase 2 agent) |
| `phase3-report.md` | 3 | TTS/energy/EDP under uncapped vs `power_governor` vs `aurora_bandit` at 3000 W |
| `pareto/<bench>.csv` | 1 | non-dominated points in (energy, runtime) per benchmark |
| `notebooks/` | live | exploratory Jupyter notebooks |
| `plots/` | live | committed PNG/PDF figures used in reports |
| `scripts/` | live | reusable Python: trace parsing, Pareto computation, plotting |

## Metric definitions (canonical)

| Metric | Formula | Notes |
|--------|---------|-------|
| Energy (J) | `Σ over run of (CPU_ENERGY + DRAM_ENERGY + Σ_card GPU_ENERGY) deltas` | "component sum" — what GEOPM measures and controls |
| TTS (s) | wall-clock from first PIO sample to last | benchmark-internal time also recorded for sanity |
| EDP (J·s) | Energy × TTS | lower is better |
| IPS | `Σ instructions / TTS` | optional reward signal in agent |
| TTS recovery | `(TTS_us − TTS_uncapped) / (TTS_governor − TTS_uncapped)` | Phase 3 headline; ≤1.0 = matches governor; <1 = better; 0 = full recovery |
| Cap-utilization | `mean(node_power) / cap` | wasted-headroom indicator |
| Per-component split | `(E_cpu, E_dram, E_gpu) / E_total` | shows where the budget went |

## Plotting conventions

- Matplotlib (no Plotly / Bokeh — committed plots must render without JS).
- Color per workload class: GPU compute = red, CPU compute = orange, memory = blue, comm = green, mixed = grey.
- Always include IQR error bars; never show point estimates without spread.
- Save plots as both PNG (for embedding in MD) and PDF (for paper).

## Conventions

- One notebook per investigation; rename when shipped to `report.md`.
- Data lives in `experiments/`, code lives here. Never write raw run data into `analysis/`.
- All scripts should accept `experiments/phase{1,3}/<bench>/runs/` as input directory — keep them re-runnable.
