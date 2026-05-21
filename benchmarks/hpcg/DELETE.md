# Deferred from Phase 1 base suite

`hpcg/` should not be deleted. This marker means it is deferred from the reduced Phase 1 base characterization campaign.

HPCG is valuable because it mixes memory-bound sparse computation with communication phases. That is exactly why it should come after the base knob-discovery suite: it is better for validating whether the later GEOPM agent can combine policies across phases than for isolating which individual knobs matter.

Bring HPCG back after Phase 1 has ranked the base knobs and Phase 2 has an agent ready for mixed proxy-app validation.
