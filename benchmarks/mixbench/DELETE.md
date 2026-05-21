# Deferred from Phase 1 base suite

`mixbench/` should not be deleted. This marker means it is deferred from the reduced Phase 1 base characterization campaign.

Mixbench is valuable because it sweeps arithmetic intensity and can produce roofline-style detector data. For the first pass, however, it overlaps with `dgemm-gpu/` for GPU compute-bound behavior and `babelstream/` for GPU memory-bound behavior.

Bring Mixbench back after the core GPU compute and GPU memory policies are stable, especially if the workload-class detector needs more data across intermediate arithmetic intensities.
