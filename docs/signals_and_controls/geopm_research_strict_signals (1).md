# Strict GEOPM Research Signals

| Category | Count |
| --- | ---: |
| frequency | 24 |
| power_energy | 25 |
| thermal_throttle | 14 |
| time | 1 |
| utilization_activity | 6 |

| Name | Category | Domain | Units | Description | Why kept |
| --- | --- | --- | --- | --- | --- |
| TIME | time | cpu | seconds | Time since the start of application profiling. | Strictly selected signal with plausible experimental value. |
| BOARD_POWER | power_energy | board | watts | Average BOARD power over 40 ms or 8 control loop iterations | Directly supports power/energy accounting or power-cap experiments. |
| BOARD_ENERGY | power_energy | board | joules | An increasing meter of energy in Joules (U32.0) consumed by the board over time. | Directly supports power/energy accounting or power-cap experiments. |
| BOARD_POWER_LIMIT_CONTROL | power_energy | board | watts | The average board power usage limit over the time window specified in the board PL1_TIME_WINDOW. | Directly supports power/energy accounting or power-cap experiments. |
| BOARD_POWER_TIME_WINDOW_CONTROL | power_energy | board | seconds | The time window associated with the board PL1_POWER_LIMIT | Directly supports power/energy accounting or power-cap experiments. |
| CPU_POWER | power_energy | package | watts | Average package power over 40 ms or 8 control loop iterations | Directly supports power/energy accounting or power-cap experiments. |
| CPU_ENERGY | power_energy | package | joules | An increasing meter of energy consumed by the package over time.  It will reset periodically due to roll-over. | Directly supports power/energy accounting or power-cap experiments. |
| CPU_MAX_ENERGY_RANGE | power_energy | package | joules | Rollover value in units of joules. | Directly supports power/energy accounting or power-cap experiments. |
| CPU_POWER_LIMIT_CONTROL | power_energy | package | watts | The average power usage limit over the time window specified in PL1_TIME_WINDOW. | Directly supports power/energy accounting or power-cap experiments. |
| CPU_POWER_LIMIT_DEFAULT | power_energy | package | watts | Maximum power to stay within the thermal limits based on the design (TDP). | Directly supports power/energy accounting or power-cap experiments. |
| CPU_POWER_MAX_AVAIL | power_energy | package | watts | The maximum power limit based on the electrical specification. | Directly supports power/energy accounting or power-cap experiments. |
| CPU_POWER_MIN_AVAIL | power_energy | package | watts | The minimum power limit based on the electrical specification. | Directly supports power/energy accounting or power-cap experiments. |
| CPU_POWER_TIME_WINDOW_CONTROL | power_energy | package | seconds | The time window associated with power limit 1. | Directly supports power/energy accounting or power-cap experiments. |
| CPU_PACKAGE_TEMPERATURE | thermal_throttle | package | celsius | Package temperature | Useful for identifying thermal or power-limit throttling. |
| CPU_CORE_TEMPERATURE | thermal_throttle | core | celsius | Core temperature | Useful for identifying thermal or power-limit throttling. |
| CPU_FREQUENCY_STATUS | frequency | cpu | hertz | The current operating frequency of the CPU. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_MAX_AVAIL | frequency | package | hertz | Maximum processor frequency. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_MIN_AVAIL | frequency | cpu | hertz | Minimum processor frequency | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_STEP | frequency | cpu | hertz | Step size between processor frequency settings | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_STICKER | frequency | cpu | hertz | Processor base frequency | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_MAX_CONTROL | frequency | core | hertz | Target operating frequency of the CPU based on the control register. When querying at a higher domain, if NaN is returned, query at its native domain. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_MIN_CONTROL | frequency | cpu | hertz | The minimum frequency allowed by the cpufreq scaling driver. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_DESIRED_CONTROL | frequency | cpu | hertz | The latest frequency request sent to the userspace scaling governor. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_FREQUENCY_GOVERNOR_CONTROL | frequency | cpu | none | The CPU frequency governor: 0=performance, 1=powersave, 2=ondemand, 3=conservative, 4=userspace, 5=schedutil. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_UNCORE_FREQUENCY_STATUS | frequency | package | hertz | The current uncore frequency. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_UNCORE_FREQUENCY_MAX_CONTROL | frequency | package | hertz | An upper limit for uncore frequency control. When querying at a higher domain, if NaN is returned, query at its native domain. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_UNCORE_FREQUENCY_MIN_CONTROL | frequency | package | hertz | A lower limit for uncore frequency control. When querying at a higher domain, if NaN is returned, query at its native domain. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| CPU_CYCLES_THREAD | utilization_activity | cpu | none | A counter incrementing at the processor's actual frequency. This counter cannot measure processor performance when the CPU is inactive. | Connects workload activity/performance behavior to power draw. |
| CPU_CYCLES_REFERENCE | utilization_activity | cpu | none | A counter incrementing at the processor's base, maximum performance frequency. This counter cannot measure processor performance when the CPU is inactive. | Connects workload activity/performance behavior to power draw. |
| CPU_INSTRUCTIONS_RETIRED | utilization_activity | cpu | none | The count of the number of instructions executed. Requires geopmwrite -e. | Connects workload activity/performance behavior to power draw. |
| DRAM_POWER | power_energy | package | watts | Average DRAM power over 40 ms or 8 control loop iterations | Directly supports power/energy accounting or power-cap experiments. |
| DRAM_ENERGY | power_energy | package | joules | An increasing meter of energy consumed by the DRAM over time.  It will reset periodically due to roll-over. | Directly supports power/energy accounting or power-cap experiments. |
| DRAM_POWER_LIMIT_CONTROL | power_energy | package | watts | DRAM power limit in watts. | Directly supports power/energy accounting or power-cap experiments. |
| DRAM_POWER_TIME_WINDOW_CONTROL | power_energy | package | seconds | DRAM power limit time window in seconds. | Directly supports power/energy accounting or power-cap experiments. |
| MSR::DRAM_PERF_STATUS:THROTTLE_TIME | thermal_throttle | memory | seconds | The amount of time that the package was throttled below the requested frequency due to MSR::DRAM_POWER_LIMIT:POWER_LIMIT. | Useful for identifying thermal or power-limit throttling. |
| GPU_POWER | power_energy | gpu | watts | Average GPU power over 40 ms or 8 control loop iterations.  Derivative signal based on LEVELZERO::GPU_ENERGY. | Directly supports power/energy accounting or power-cap experiments. |
| GPU_ENERGY | power_energy | gpu | joules | GPU card-level energy counter | Directly supports power/energy accounting or power-cap experiments. |
| GPU_POWER_LIMIT_CONTROL | power_energy | gpu | watts | Requested power limit, sustained on average over DRM::HWMON::POWER1_MAX_INTERVAL | Directly supports power/energy accounting or power-cap experiments. |
| GPU_POWER_LIMIT_DEFAULT | power_energy | gpu | watts | Default thermal design power limit | Directly supports power/energy accounting or power-cap experiments. |
| GPU_POWER_TIME_WINDOW_CONTROL | power_energy | gpu | seconds | Requested time window over which DRM::HWMON::POWER1_MAX is sustained on average | Directly supports power/energy accounting or power-cap experiments. |
| GPU_CORE_POWER | power_energy | gpu_chip | watts | Average GPU power over 40 ms or 8 control loop iterations | Directly supports power/energy accounting or power-cap experiments. |
| GPU_CORE_ENERGY | power_energy | gpu_chip | joules | GPU Compute Hardware Domain chip energy. | Directly supports power/energy accounting or power-cap experiments. |
| GPU_CHIP_ENERGY | power_energy | gpu_chip | joules | GPU tile-level energy counter | Directly supports power/energy accounting or power-cap experiments. |
| GPU_CORE_FREQUENCY_STATUS | frequency | gpu_chip | hertz | Latest GPU frequency cached by the driver | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_CORE_FREQUENCY_MAX_AVAIL | frequency | gpu_chip | hertz | The platform's default setting for DRM::RPS_MAX_FREQ | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_CORE_FREQUENCY_MIN_AVAIL | frequency | gpu_chip | hertz | GPU minimum requestable frequency | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_CORE_FREQUENCY_STEP | frequency |  |  | The compute domain frequency step size. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_CORE_FREQUENCY_MAX_CONTROL | frequency | gpu_chip | hertz | User-configured requested power state (RPS) for maximum GPU frequency | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_CORE_FREQUENCY_MIN_CONTROL | frequency | gpu_chip | hertz | User-configured requested power state (RPS) for minimum GPU frequency | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| GPU_UTILIZATION | utilization_activity |  |  | Utilization of all GPU engines. Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. | Connects workload activity/performance behavior to power draw. |
| GPU_CORE_ACTIVITY | utilization_activity |  |  | Utilization of the GPU Compute engines (EUs). Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. | Connects workload activity/performance behavior to power draw. |
| GPU_UNCORE_ACTIVITY | frequency |  |  | Utilization of the GPU Copy engines. Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| LEVELZERO::GPU_CORE_UTILIZATION | utilization_activity |  |  | Utilization of the GPU Compute engines (EUs). Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. | Connects workload activity/performance behavior to power draw. |
| LEVELZERO::GPU_UNCORE_UTILIZATION | frequency |  |  | Utilization of the GPU Copy engines. Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| LEVELZERO::GPU_CORE_TEMPERATURE_MAXIMUM | thermal_throttle | gpu_chip | celsius | The maximum measured temperature across all sensors in the GPU accelerator. | Useful for identifying thermal or power-limit throttling. |
| LEVELZERO::GPU_MEMORY_TEMPERATURE_MAXIMUM | thermal_throttle | gpu_chip | celsius | The maximum measured temperature across all sensors in the GPU memory. | Useful for identifying thermal or power-limit throttling. |
| LEVELZERO::GPU_POWER_LIMIT_MAX_AVAIL | power_energy | gpu | watts | The maximum supported power limit. | Directly supports power/energy accounting or power-cap experiments. |
| LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR | frequency |  |  | Performance Factor of the GPU Compute Hardware Domain. | Strictly selected signal with plausible experimental value. |
| DRM::THROTTLE_REASON_STATUS | thermal_throttle | gpu_chip | none | Whether the GPU is currently being throttled for any reason | Useful for identifying thermal or power-limit throttling. |
| DRM::THROTTLE_REASON_PL1 | thermal_throttle | gpu_chip | none | Whether the GPU is currently being throttled due to PL1 (average power) | Useful for identifying thermal or power-limit throttling. |
| DRM::THROTTLE_REASON_PL2 | thermal_throttle | gpu_chip | none | Whether the GPU is currently being throttled due to PL2 (burst power) | Useful for identifying thermal or power-limit throttling. |
| DRM::THROTTLE_REASON_PL4 | thermal_throttle | gpu_chip | none | Whether the GPU is currently being throttled due to PL4 (current) | Useful for identifying thermal or power-limit throttling. |
| DRM::THROTTLE_REASON_THERMAL | thermal_throttle | gpu_chip | none | Whether the GPU is currently being throttled for thermal reasons | Useful for identifying thermal or power-limit throttling. |
| DRM::THROTTLE_REASON_PROCHOT | thermal_throttle | gpu_chip | none | Whether the GPU is currently being throttled due to prochot | Useful for identifying thermal or power-limit throttling. |
| DRM::THROTTLE_REASON_RATL | thermal_throttle | gpu_chip | none | Whether the GPU is currently being throttled due to RATL | Useful for identifying thermal or power-limit throttling. |
| DRM::THROTTLE_REASON_VR_TDC | thermal_throttle | gpu_chip | none | Whether the GPU is currently being throttled for VR TDC reasons | Useful for identifying thermal or power-limit throttling. |
| LEVELZERO::GPU_CORE_THROTTLE_REASONS | thermal_throttle | gpu_chip | none | GPU Compute Hardware throttle reasons.  See oneAPI Level Zero Sysman Spec for decoding | Useful for identifying thermal or power-limit throttling. |
| SST::COREPRIORITY_ENABLE:ENABLE | frequency | package | none | SST-CP is enabled. Disabling this also disables SST::TURBO_ENABLE:ENABLE. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::TURBO_ENABLE:ENABLE | frequency | package | none | SST-TF is enabled. Enabling this also enables SST::COREPRIORITY_ENABLE:ENABLE. | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
| SST::COREPRIORITY:ASSOCIATION | frequency | core | none | Assigned core priority level | Useful for CPU/GPU/uncore frequency, turbo, or priority-control studies. |
