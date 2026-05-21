# Deferred from Phase 1 base suite

`quicksilver/` should not be deleted. This marker means it is deferred from the reduced Phase 1 base characterization campaign.

Quicksilver is a strong communication-imbalance validation workload, but it is noisier and more complex than OSU for the first pass. Start with OSU collectives and the `mpi-idle-wait/` synthetic benchmark to isolate communication slack before moving to an imbalanced proxy app.

Bring Quicksilver back once the communication detector and CPU-throttling policy are stable enough to test against a realistic load-imbalance workload.
