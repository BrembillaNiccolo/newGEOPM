# Deferred from Phase 1 base suite

`lammps/` should not be deleted. This marker means it is deferred from the reduced Phase 1 base characterization campaign.

LAMMPS and GROMACS are both useful production molecular dynamics workloads. Running both early would increase setup and analysis cost before the agent exists. Use `gromacs/` as the first real end-to-end MD application, then add LAMMPS later to test whether the results generalize to a second MD code and a different GPU backend profile.

Bring LAMMPS back for Phase 3 generality testing after GROMACS has validated the first production-app path.
