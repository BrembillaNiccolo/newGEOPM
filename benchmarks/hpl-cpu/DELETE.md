# Deferred from Phase 1 base suite

`hpl-cpu/` should not be deleted. This marker means it is deferred from the reduced Phase 1 base characterization campaign.

HPL is a useful CPU headline benchmark, but it is expensive and needs careful input tuning. The first pass should use `cpu-dgemm/` as a cheaper and cleaner CPU compute anchor for `CPU_FREQUENCY_MAX_CONTROL` and `CPU_POWER_LIMIT_CONTROL`.

Bring HPL back after the CPU policy has been characterized on `cpu-dgemm/`, when the project needs a more recognizable CPU compute validation result.
