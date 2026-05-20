# Strict GEOPM Research Controls

| Category | Count |
| --- | ---: |
| frequency | 24 |
| power_energy | 11 |

| Name | Category | Domain | Units | Description | Why kept |
| --- | --- | --- | --- | --- | --- |
| BOARD_POWER_LIMIT_CONTROL | power_energy | board | watts | The average board power usage limit over the time window specified in the board PL1_TIME_WINDOW. | Directly supports power/energy accounting or power-cap experiments. |
| BOARD_POWER_TIME_WINDOW_CONTROL | power_energy | board | seconds | The time window associated with the board PL1_POWER_LIMIT | Directly supports power/energy accounting or power-cap experiments. |
| CPU_POWER_LIMIT_CONTROL | power_energy | package | watts | The average power usage limit over the time window specified in PL1_TIME_WINDOW. | Directly supports power/energy accounting or power-cap experiments. |
| CPU_POWER_TIME_WINDOW_CONTROL | power_energy | package | seconds | The time window associated with power limit 1. | Directly supports power/energy accounting or power-cap experiments. |
| DRAM_POWER_LIMIT_CONTROL | power_energy | package | watts | DRAM power limit in watts. | Directly supports power/energy accounting or power-cap experiments. |
| DRAM_POWER_TIME_WINDOW_CONTROL | power_energy | package | seconds | DRAM power limit time window in seconds. | Directly supports power/energy accounting or power-cap experiments. |
| POWERCAP::CPU_POWER_LIMIT | power_energy | package | watts | CPU power limit in watts. | Directly supports power/energy accounting or power-cap experiments. |
| POWERCAP::CPU_TIME_WINDOW | power_energy | package | seconds | CPU power limit time window in seconds. | Directly supports power/energy accounting or power-cap experiments. |
| POWERCAP::DRAM_POWER_LIMIT | power_energy | package | watts | DRAM power limit in watts. | Directly supports power/energy accounting or power-cap experiments. |
| POWERCAP::DRAM_TIME_WINDOW | power_energy | package | seconds | DRAM power limit time window in seconds. | Directly supports power/energy accounting or power-cap experiments. |
| CPU_FREQUENCY_MAX_CONTROL | frequency | core | hertz | Target operating frequency of the CPU based on the control register. When querying at a higher domain, if NaN is returned, query at its native domain. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_MIN_CONTROL | frequency | cpu | hertz | The minimum frequency allowed by the cpufreq scaling driver. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_DESIRED_CONTROL | frequency | cpu | hertz | The latest frequency request sent to the userspace scaling governor. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_GOVERNOR_CONTROL | frequency | cpu | none | The CPU frequency governor: 0=performance, 1=powersave, 2=ondemand, 3=conservative, 4=userspace, 5=schedutil. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_UNCORE_FREQUENCY_MAX_CONTROL | frequency | package | hertz | An upper limit for uncore frequency control. When querying at a higher domain, if NaN is returned, query at its native domain. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_UNCORE_FREQUENCY_MIN_CONTROL | frequency | package | hertz | A lower limit for uncore frequency control. When querying at a higher domain, if NaN is returned, query at its native domain. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_CORE_FREQUENCY_MAX_CONTROL | frequency | gpu_chip | hertz | User-configured requested power state (RPS) for maximum GPU frequency | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_CORE_FREQUENCY_MIN_CONTROL | frequency | gpu_chip | hertz | User-configured requested power state (RPS) for minimum GPU frequency | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_POWER_TIME_WINDOW_CONTROL | power_energy | gpu | seconds | Requested time window over which DRM::HWMON::POWER1_MAX is sustained on average | Directly supports power/energy accounting or power-cap experiments. |
| LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL | frequency |  |  | Performance Factor of the GPU Compute Hardware Domain. | Strictly selected control knob with plausible experimental value; verify safe ranges before writing. |
| SST::COREPRIORITY_ENABLE:ENABLE | frequency | package | none | SST-CP is enabled. Disabling this also disables SST::TURBO_ENABLE:ENABLE. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::TURBO_ENABLE:ENABLE | frequency | package | none | SST-TF is enabled. Enabling this also enables SST::COREPRIORITY_ENABLE:ENABLE. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:ASSOCIATION | frequency | core | none | Assigned core priority level | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:0:FREQUENCY_MAX | frequency | package | hertz | Maximum frequency of core priority level 0 | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:0:FREQUENCY_MIN | frequency | package | hertz | Minimum frequency of core priority level 0 | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:0:PRIORITY | frequency | package | none | Proportional priority for core priority level 0, ranging from 0 to 1. A lower value indicates a desire to receive a greater share of surplus power than priority groups with a higher value. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:1:FREQUENCY_MAX | frequency | package | hertz | Maximum frequency of core priority level 1 | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:1:FREQUENCY_MIN | frequency | package | hertz | Minimum frequency of core priority level 1 | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:1:PRIORITY | frequency | package | none | Proportional priority for core priority level 1, ranging from 0 to 1. A lower value indicates a desire to receive a greater share of surplus power than priority groups with a higher value. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:2:FREQUENCY_MAX | frequency | package | hertz | Maximum frequency of core priority level 2 | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:2:FREQUENCY_MIN | frequency | package | hertz | Minimum frequency of core priority level 2 | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:2:PRIORITY | frequency | package | none | Proportional priority for core priority level 2, ranging from 0 to 1. A lower value indicates a desire to receive a greater share of surplus power than priority groups with a higher value. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:3:FREQUENCY_MAX | frequency | package | hertz | Maximum frequency of core priority level 3 | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:3:FREQUENCY_MIN | frequency | package | hertz | Minimum frequency of core priority level 3 | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:3:PRIORITY | frequency | package | none | Proportional priority for core priority level 3, ranging from 0 to 1. A lower value indicates a desire to receive a greater share of surplus power than priority groups with a higher value. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
