# Deferred from Phase 1 base suite

`gromacs/` should not be deleted. This marker means it is deferred from the reduced Phase 1 base characterization campaign.

GROMACS is the best first production application for later validation because it combines GPU compute, CPU work, and MPI communication. It is too complex for the initial knob-discovery pass, where the goal is to learn clean per-class knob effects.

Bring GROMACS back after the custom GEOPM agent exists, then use it to measure time-to-solution recovery under caps and always-on energy savings on a realistic MD workload.
