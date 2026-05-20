# GEOPM Readable Signal Descriptions

| Name | Domain | Units | Description | Alias For |
| --- | --- | --- | --- | --- |
| BOARD_ENERGY | board | joules | An increasing meter of energy in Joules (U32.0) consumed by the board over time. | MSR::PLATFORM_ENERGY_STATUS:ENERGY |
| BOARD_POWER | board | watts | Average BOARD power over 40 ms or 8 control loop iterations | MSR::PLATFORM_ENERGY_STATUS:ENERGY rate of change; MSR::BOARD_POWER |
| BOARD_POWER_LIMIT_CONTROL | board | watts | The average board power usage limit over the time window specified in the board PL1_TIME_WINDOW. | MSR::PLATFORM_POWER_LIMIT:PL1_POWER_LIMIT |
| BOARD_POWER_TIME_WINDOW_CONTROL | board | seconds | The time window associated with the board PL1_POWER_LIMIT | MSR::PLATFORM_POWER_LIMIT:PL1_TIME_WINDOW |
| CPUFREQ::BIOS_LIMIT | cpu | hertz | Maximum CPU frequency, limited by BIOS settings. |  |
| CPUFREQ::CPUINFO_CUR_FREQ | cpu | hertz | The current operating frequency reported by the CPU hardware. |  |
| CPUFREQ::CPUINFO_MAX_FREQ | cpu | hertz | The maximum allowed frequency to set on the CPU. |  |
| CPUFREQ::CPUINFO_MIN_FREQ | cpu | hertz | The minimum allowed frequency to set on the CPU. |  |
| CPUFREQ::CPUINFO_TRANSITION_LATENCY | cpu | seconds | The time delay to switch from one P-State to another. |  |
| CPUFREQ::CPU_GOVERNOR | cpu | none | The CPU frequency governor: 0=performance, 1=powersave, 2=ondemand, 3=conservative, 4=userspace, 5=schedutil. |  |
| CPUFREQ::SCALING_CUR_FREQ | cpu | hertz | The current requested CPU frequency by the cpufreq scaling driver. |  |
| CPUFREQ::SCALING_MAX_FREQ | cpu | hertz | The maximum frequency allowed by the cpufreq scaling driver. |  |
| CPUFREQ::SCALING_MIN_FREQ | cpu | hertz | The minimum frequency allowed by the cpufreq scaling driver. |  |
| CPUFREQ::SCALING_SETSPEED | cpu | hertz | The latest frequency request sent to the userspace scaling governor. |  |
| CPUINFO::FREQ_MAX | cpu | hertz | Maximum processor frequency |  |
| CPUINFO::FREQ_MIN | cpu | hertz | Minimum processor frequency |  |
| CPUINFO::FREQ_STEP | cpu | hertz | Step size between processor frequency settings |  |
| CPUINFO::FREQ_STICKER | cpu | hertz | Processor base frequency |  |
| CPU_CORE_TEMPERATURE | core | celsius | Core temperature | Temperature derived from PROCHOT and MSR::THERM_STATUS:DIGITAL_READOUT |
| CPU_CYCLES_REFERENCE | cpu | none | A counter incrementing at the processor's base, maximum performance frequency. This counter cannot measure processor performance when the CPU is inactive. | MSR::MPERF:MCNT |
| CPU_CYCLES_THREAD | cpu | none | A counter incrementing at the processor's actual frequency. This counter cannot measure processor performance when the CPU is inactive. | MSR::APERF:ACNT |
| CPU_ENERGY | package | joules | An increasing meter of energy consumed by the package over time.  It will reset periodically due to roll-over. | MSR::PKG_ENERGY_STATUS:ENERGY |
| CPU_FREQUENCY_DESIRED_CONTROL | cpu | hertz | The latest frequency request sent to the userspace scaling governor. |  |
| CPU_FREQUENCY_GOVERNOR_CONTROL | cpu | none | The CPU frequency governor: 0=performance, 1=powersave, 2=ondemand, 3=conservative, 4=userspace, 5=schedutil. |  |
| CPU_FREQUENCY_MAX_AVAIL | package | hertz | Maximum processor frequency. | MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_0 |
| CPU_FREQUENCY_MAX_CONTROL | core | hertz | Target operating frequency of the CPU based on the control register. When querying at a higher domain, if NaN is returned, query at its native domain. | MSR::PERF_CTL:FREQ |
| CPU_FREQUENCY_MIN_AVAIL | cpu | hertz | Minimum processor frequency | CPUINFO::FREQ_MIN |
| CPU_FREQUENCY_MIN_CONTROL | cpu | hertz | The minimum frequency allowed by the cpufreq scaling driver. |  |
| CPU_FREQUENCY_STATUS | cpu | hertz | The current operating frequency of the CPU. | MSR::PERF_STATUS:FREQ |
| CPU_FREQUENCY_STEP | cpu | hertz | Step size between processor frequency settings | CPUINFO::FREQ_STEP |
| CPU_FREQUENCY_STICKER | cpu | hertz | Processor base frequency | CPUINFO::FREQ_STICKER |
| CPU_INSTRUCTIONS_RETIRED | cpu | none | The count of the number of instructions executed. Requires geopmwrite -e. | MSR::FIXED_CTR0:INST_RETIRED_ANY |
| CPU_MAX_ENERGY_RANGE | package | joules | Rollover value in units of joules. |  |
| CPU_PACKAGE_TEMPERATURE | package | celsius | Package temperature | Temperature derived from PROCHOT and MSR::PACKAGE_THERM_STATUS:DIGITAL_READOUT |
| CPU_POWER | package | watts | Average package power over 40 ms or 8 control loop iterations | CPU_ENERGY rate of change |
| CPU_POWER_LIMIT_CONTROL | package | watts | The average power usage limit over the time window specified in PL1_TIME_WINDOW. | MSR::PKG_POWER_LIMIT:PL1_POWER_LIMIT |
| CPU_POWER_LIMIT_DEFAULT | package | watts | Maximum power to stay within the thermal limits based on the design (TDP). | MSR::PKG_POWER_INFO:THERMAL_SPEC_POWER |
| CPU_POWER_MAX_AVAIL | package | watts | The maximum power limit based on the electrical specification. | MSR::PKG_POWER_INFO:MAX_POWER |
| CPU_POWER_MIN_AVAIL | package | watts | The minimum power limit based on the electrical specification. | MSR::PKG_POWER_INFO:MIN_POWER |
| CPU_POWER_TIME_WINDOW_CONTROL | package | seconds | The time window associated with power limit 1. | MSR::PKG_POWER_LIMIT:PL1_TIME_WINDOW |
| CPU_TIMESTAMP_COUNTER | cpu | none | An always running, monotonically increasing counter that is incremented at a constant rate.  For use as a wall clock timer. | MSR::TIME_STAMP_COUNTER:TIMESTAMP_COUNT |
| CPU_UNCORE_FREQUENCY_MAX_CONTROL | package | hertz | An upper limit for uncore frequency control. When querying at a higher domain, if NaN is returned, query at its native domain. | MSR::UNCORE_RATIO_LIMIT:MAX_RATIO |
| CPU_UNCORE_FREQUENCY_MIN_CONTROL | package | hertz | A lower limit for uncore frequency control. When querying at a higher domain, if NaN is returned, query at its native domain. | MSR::UNCORE_RATIO_LIMIT:MIN_RATIO |
| CPU_UNCORE_FREQUENCY_STATUS | package | hertz | The current uncore frequency. | MSR::UNCORE_PERF_STATUS:FREQ |
| DRAM_ENERGY | package | joules | An increasing meter of energy consumed by the DRAM over time.  It will reset periodically due to roll-over. | MSR::DRAM_ENERGY_STATUS:ENERGY |
| DRAM_POWER | package | watts | Average DRAM power over 40 ms or 8 control loop iterations | DRAM_ENERGY rate of change |
| DRAM_POWER_LIMIT_CONTROL | package | watts | DRAM power limit in watts. |  |
| DRAM_POWER_TIME_WINDOW_CONTROL | package | seconds | DRAM power limit time window in seconds. |  |
| DRM::BASE_ACT_FREQ | gpu_chip | hertz | Actual GPU base-die frequency selected by the power manager |  |
| DRM::BASE_FREQ_FACTOR_SCALE | gpu_chip | none | Scaling factor for DRM::BASE_FREQ_FACTOR_STEP |  |
| DRM::BASE_FREQ_FACTOR_STEP | gpu_chip | none | GPU base-die frequency factor scaled by 1/DRM::BASE_FREQ_FACTOR_SCALE |  |
| DRM::BASE_FREQ_FACTOR_STEP_DEFAULT | gpu_chip | none | The platform's default setting for DRM::BASE_FREQ_FACTOR_STEP |  |
| DRM::BASE_RP0_FREQ | gpu_chip | hertz | GPU base-die RP0 frequency |  |
| DRM::BASE_RPN_FREQ | gpu_chip | hertz | GPU base-die RPn frequency |  |
| DRM::HWMON::CURR1_CRIT | gpu | amperes | Critical current limit, influencing the power manager's throttling decisions |  |
| DRM::HWMON::ENERGY1_INPUT::GPU | gpu | joules | GPU card-level energy counter |  |
| DRM::HWMON::ENERGY1_INPUT::GPU_CHIP | gpu_chip | joules | GPU tile-level energy counter |  |
| DRM::HWMON::POWER1_MAX | gpu | watts | Requested power limit, sustained on average over DRM::HWMON::POWER1_MAX_INTERVAL |  |
| DRM::HWMON::POWER1_MAX_INTERVAL | gpu | seconds | Requested time window over which DRM::HWMON::POWER1_MAX is sustained on average |  |
| DRM::HWMON::POWER1_RATED_MAX | gpu | watts | Default thermal design power limit |  |
| DRM::MEDIA_ACT_FREQ | gpu_chip | hertz | Actual GPU media frequency |  |
| DRM::MEDIA_FREQ_FACTOR_SCALE | gpu_chip | none | Scaling factor for DRM::MEDIA_FREQ_FACTOR_STEP |  |
| DRM::MEDIA_FREQ_FACTOR_STEP | gpu_chip | none | GPU media frequency factor scaled by 1/DRM::MEDIA_FREQ_FACTOR_SCALE |  |
| DRM::MEDIA_FREQ_FACTOR_STEP_DEFAULT | gpu_chip | none | The platform's default setting for DRM::MEDIA_FREQ_FACTOR_STEP |  |
| DRM::MEDIA_RP0_FREQ | gpu_chip | hertz | GPU media RP0 frequency |  |
| DRM::MEDIA_RPN_FREQ | gpu_chip | hertz | GPU media RPn frequency |  |
| DRM::MEM_RP0_FREQ | gpu_chip | hertz | GPU memory-die RP0 frequency |  |
| DRM::MEM_RPN_FREQ | gpu_chip | hertz | GPU memory-die RPn frequency |  |
| DRM::PUNIT_REQ_FREQ | gpu_chip | hertz | PUnit requested GPU frequency |  |
| DRM::RAPL_PL1_FREQ | gpu_chip | hertz | GPU RAPL PL1 frequency |  |
| DRM::RC6_ENABLE | gpu_chip | none | Enable RC6 |  |
| DRM::RC6_RESIDENCY | gpu_chip | seconds | Time spent in RC6 state |  |
| DRM::RPS_ACT_FREQ | gpu_chip | hertz | Actual latest GPU frequency |  |
| DRM::RPS_BOOST_FREQ | gpu_chip | hertz | GPU boost frequency |  |
| DRM::RPS_CUR_FREQ | gpu_chip | hertz | Latest GPU frequency cached by the driver |  |
| DRM::RPS_MAX_FREQ | gpu_chip | hertz | User-configured requested power state (RPS) for maximum GPU frequency |  |
| DRM::RPS_MAX_FREQ_DEFAULT | gpu_chip | hertz | The platform's default setting for DRM::RPS_MAX_FREQ |  |
| DRM::RPS_MIN_FREQ | gpu_chip | hertz | User-configured requested power state (RPS) for minimum GPU frequency |  |
| DRM::RPS_MIN_FREQ_DEFAULT | gpu_chip | hertz | The platform's default setting for DRM::RPS_MIN_FREQ |  |
| DRM::RPS_RP0_FREQ | gpu_chip | hertz | Maximum non-overclocked GPU frequency |  |
| DRM::RPS_RP1_FREQ | gpu_chip | hertz | GPU RP1 nominal frequency |  |
| DRM::RPS_RPN_FREQ | gpu_chip | hertz | GPU minimum requestable frequency |  |
| DRM::THROTTLE_REASON_PL1 | gpu_chip | none | Whether the GPU is currently being throttled due to PL1 (average power) |  |
| DRM::THROTTLE_REASON_PL2 | gpu_chip | none | Whether the GPU is currently being throttled due to PL2 (burst power) |  |
| DRM::THROTTLE_REASON_PL4 | gpu_chip | none | Whether the GPU is currently being throttled due to PL4 (current) |  |
| DRM::THROTTLE_REASON_PROCHOT | gpu_chip | none | Whether the GPU is currently being throttled due to prochot |  |
| DRM::THROTTLE_REASON_RATL | gpu_chip | none | Whether the GPU is currently being throttled due to RATL |  |
| DRM::THROTTLE_REASON_STATUS | gpu_chip | none | Whether the GPU is currently being throttled for any reason |  |
| DRM::THROTTLE_REASON_THERMAL | gpu_chip | none | Whether the GPU is currently being throttled for thermal reasons |  |
| DRM::THROTTLE_REASON_VR_TDC | gpu_chip | none | Whether the GPU is currently being throttled for VR TDC reasons |  |
| GPU_CHIP_ENERGY | gpu_chip | joules | GPU tile-level energy counter |  |
| GPU_CORE_ACTIVITY |  |  | Utilization of the GPU Compute engines (EUs). Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. |  |
| GPU_CORE_ENERGY | gpu_chip | joules | GPU Compute Hardware Domain chip energy. | LEVELZERO::GPU_CORE_ENERGY |
| GPU_CORE_FREQUENCY_MAX_AVAIL | gpu_chip | hertz | The platform's default setting for DRM::RPS_MAX_FREQ |  |
| GPU_CORE_FREQUENCY_MAX_CONTROL | gpu_chip | hertz | User-configured requested power state (RPS) for maximum GPU frequency |  |
| GPU_CORE_FREQUENCY_MIN_AVAIL | gpu_chip | hertz | GPU minimum requestable frequency |  |
| GPU_CORE_FREQUENCY_MIN_CONTROL | gpu_chip | hertz | User-configured requested power state (RPS) for minimum GPU frequency |  |
| GPU_CORE_FREQUENCY_STATUS | gpu_chip | hertz | Latest GPU frequency cached by the driver |  |
| GPU_CORE_FREQUENCY_STEP |  |  | The compute domain frequency step size. |  |
| GPU_CORE_POWER | gpu_chip | watts | Average GPU power over 40 ms or 8 control loop iterations | LEVELZERO::GPU_CORE_POWER |
| GPU_ENERGY | gpu | joules | GPU card-level energy counter |  |
| GPU_POWER | gpu | watts | Average GPU power over 40 ms or 8 control loop iterations.  Derivative signal based on LEVELZERO::GPU_ENERGY. | LEVELZERO::GPU_POWER |
| GPU_POWER_LIMIT_CONTROL | gpu | watts | Requested power limit, sustained on average over DRM::HWMON::POWER1_MAX_INTERVAL |  |
| GPU_POWER_LIMIT_DEFAULT | gpu | watts | Default thermal design power limit |  |
| GPU_POWER_TIME_WINDOW_CONTROL | gpu | seconds | Requested time window over which DRM::HWMON::POWER1_MAX is sustained on average |  |
| GPU_RAS_COMPUTE_ERRCOUNT_CORRECTABLE | gpu_chip | none | Number of errors in compute accelerator hardware. | LEVELZERO::GPU_RAS_COMPUTE_ERRCOUNT_CORRECTABLE |
| GPU_RAS_COMPUTE_ERRCOUNT_UNCORRECTABLE | gpu_chip | none | Number of errors in compute accelerator hardware. | LEVELZERO::GPU_RAS_COMPUTE_ERRCOUNT_UNCORRECTABLE |
| GPU_RAS_NONCOMPUTE_ERRCOUNT_CORRECTABLE | gpu_chip | none | Number of errors in fixed-function accelerator hardware. | LEVELZERO::GPU_RAS_NONCOMPUTE_ERRCOUNT_CORRECTABLE |
| GPU_RAS_NONCOMPUTE_ERRCOUNT_UNCORRECTABLE | gpu_chip | none | Number of errors in fixed-function accelerator hardware. | LEVELZERO::GPU_RAS_NONCOMPUTE_ERRCOUNT_UNCORRECTABLE |
| GPU_UNCORE_ACTIVITY |  |  | Utilization of the GPU Copy engines. Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. |  |
| GPU_UTILIZATION |  |  | Utilization of all GPU engines. Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. |  |
| LEVELZERO::GPU_ACTIVE_TIME |  |  | Time that this resource is actively running a workload. |  |
| LEVELZERO::GPU_ACTIVE_TIME_TIMESTAMP |  |  | The timestamp for the LEVELZERO::GPU_ACTIVE_TIME. |  |
| LEVELZERO::GPU_CORE_ACTIVE_TIME |  |  | Time that the GPU compute engines (EUs) are actively running a workload. |  |
| LEVELZERO::GPU_CORE_ACTIVE_TIME_TIMESTAMP |  |  | The timestamp for the LEVELZERO::GPU_CORE_ACTIVE_TIME signal read. |  |
| LEVELZERO::GPU_CORE_ENERGY_TIMESTAMP |  |  | GPU compute hardware domain energy timestamp. |  |
| LEVELZERO::GPU_CORE_FREQUENCY_EFFICIENT | gpu_chip | hertz | The efficient minimum frequency of the GPU Compute Hardware. |  |
| LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR |  |  | Performance Factor of the GPU Compute Hardware Domain. |  |
| LEVELZERO::GPU_CORE_PERFORMANCE_FACTOR_CONTROL |  |  | Performance Factor of the GPU Compute Hardware Domain. |  |
| LEVELZERO::GPU_CORE_TEMPERATURE_MAXIMUM | gpu_chip | celsius | The maximum measured temperature across all sensors in the GPU accelerator. |  |
| LEVELZERO::GPU_CORE_THROTTLE_REASONS | gpu_chip | none | GPU Compute Hardware throttle reasons.  See oneAPI Level Zero Sysman Spec for decoding |  |
| LEVELZERO::GPU_CORE_UTILIZATION |  |  | Utilization of the GPU Compute engines (EUs). Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. |  |
| LEVELZERO::GPU_ENERGY_TIMESTAMP |  |  | Timestamp for the GPU energy read. |  |
| LEVELZERO::GPU_MEMORY_TEMPERATURE_MAXIMUM | gpu_chip | celsius | The maximum measured temperature across all sensors in the GPU memory. |  |
| LEVELZERO::GPU_POWER_LIMIT_MAX_AVAIL | gpu | watts | The maximum supported power limit. |  |
| LEVELZERO::GPU_RAS_CACHE_ERRCOUNT_CORRECTABLE | gpu_chip | none | Number of errors in caches. |  |
| LEVELZERO::GPU_RAS_CACHE_ERRCOUNT_UNCORRECTABLE | gpu_chip | none | Number of errors in caches. |  |
| LEVELZERO::GPU_RAS_DISPLAY_ERRCOUNT_CORRECTABLE | gpu_chip | none | Number of errors in display. |  |
| LEVELZERO::GPU_RAS_DISPLAY_ERRCOUNT_UNCORRECTABLE | gpu_chip | none | Number of errors in display. |  |
| LEVELZERO::GPU_RAS_DRIVER_ERRCOUNT_CORRECTABLE | gpu_chip | none | Number of low level driver communication errors. |  |
| LEVELZERO::GPU_RAS_DRIVER_ERRCOUNT_UNCORRECTABLE | gpu_chip | none | Number of low level driver communication errors. |  |
| LEVELZERO::GPU_RAS_PROGRAMMING_ERRCOUNT_CORRECTABLE | gpu_chip | none | Number of hardware exceptions generated by the hardware. |  |
| LEVELZERO::GPU_RAS_PROGRAMMING_ERRCOUNT_UNCORRECTABLE | gpu_chip | none | Number of hardware exceptions generated by the hardware. |  |
| LEVELZERO::GPU_RAS_RESET_COUNT_CORRECTABLE | gpu_chip | none | Number of accelerator engine resets by the driver. |  |
| LEVELZERO::GPU_RAS_RESET_COUNT_UNCORRECTABLE | gpu_chip | none | Number of accelerator engine resets by the driver. |  |
| LEVELZERO::GPU_UNCORE_ACTIVE_TIME |  |  | Time that the GPU copy engines are actively running a workload. |  |
| LEVELZERO::GPU_UNCORE_ACTIVE_TIME_TIMESTAMP |  |  | The timestamp for the LEVELZERO::GPU_UNCORE_ACTIVE_TIME signal read. |  |
| LEVELZERO::GPU_UNCORE_UTILIZATION |  |  | Utilization of the GPU Copy engines. Level Zero logical engines may map to the same hardware, resulting in a reduced signal range (i.e. less than 0 to 1) in some cases. |  |
| MSR::APERF:ACNT | cpu | none | A counter incrementing at the processor's actual frequency. This counter cannot measure processor performance when the CPU is inactive. |  |
| MSR::BOARD_ENERGY | board | joules | An increasing meter of energy in Joules (U32.0) consumed by the board over time. | MSR::PLATFORM_ENERGY_STATUS:ENERGY |
| MSR::BOARD_POWER | board | watts | Average BOARD power over 40 ms or 8 control loop iterations | MSR::PLATFORM_ENERGY_STATUS:ENERGY rate of change |
| MSR::CPU_SCALABILITY_RATIO | cpu | none | Measure of CPU Scalability as determined by the derivative of PCNT divided by the derivative of ACNT over 8 samples |  |
| MSR::DRAM_ENERGY_STATUS:ENERGY | package | joules | An increasing meter of energy consumed by the DRAM over time.  It will reset periodically due to roll-over. |  |
| MSR::DRAM_PERF_STATUS:THROTTLE_TIME | memory | seconds | The amount of time that the package was throttled below the requested frequency due to MSR::DRAM_POWER_LIMIT:POWER_LIMIT. |  |
| MSR::DRAM_POWER_INFO:MAX_POWER | memory | watts | The maximum DRAM power limit based on the electrical specification. |  |
| MSR::DRAM_POWER_INFO:MAX_TIME_WINDOW | memory | seconds | The maximum value accepted in MSR::DRAM_POWER_LIMIT:TIME_WINDOW. |  |
| MSR::DRAM_POWER_INFO:MIN_POWER | memory | watts | The minimum DRAM power limit based on the electrical specification. |  |
| MSR::DRAM_POWER_INFO:THERMAL_SPEC_POWER | memory | watts | Maximum DRAM power to stay within the thermal limits based on the design. |  |
| MSR::DRAM_POWER_LIMIT:ENABLE | memory | none | Enable the limit specified in POWER_LIMIT. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::DRAM_POWER_LIMIT:LOCK | memory | none | Ignore any changes to configuration in DRAM_POWER_LIMIT until the next reset. |  |
| MSR::DRAM_POWER_LIMIT:POWER_LIMIT | memory | watts | The average DRAM power usage limit over the time window specified in TIME_WINDOW. |  |
| MSR::DRAM_POWER_LIMIT:TIME_WINDOW | memory | seconds | The time window associated with the DRAM power limit. |  |
| MSR::FIXED_CTR0:INST_RETIRED_ANY | cpu | none | The count of the number of instructions executed. Requires geopmwrite -e. |  |
| MSR::FIXED_CTR1:CPU_CLK_UNHALTED_THREAD | cpu | none | The count of the number of cycles while the logical processor is not in a halt state.  The count rate may change based on core frequency.  Requires geopmwrite -e. |  |
| MSR::FIXED_CTR2:CPU_CLK_UNHALTED_REF_TSC | cpu | none | The count of the number of cycles while the logical processor is not in a halt state and not in a stop-clock state.  The count rate is fixed at the TIMESTAMP_COUNT rate.  Requires geopmwrite -e. |  |
| MSR::FIXED_CTR_CTRL:EN0_OS | cpu | none | Count MSR::FIXED_CTR0:INST_RETIRED_ANY events while in kernel mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set.  Requires geopmwrite -e. |  |
| MSR::FIXED_CTR_CTRL:EN0_PMI | cpu | none | If set, generate an interrupt when the MSR::FIXED_CTR0:INST_RETIRED_ANY counter overflows. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::FIXED_CTR_CTRL:EN0_USR | cpu | none | Count MSR::FIXED_CTR0:INST_RETIRED_ANY events while in user mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::FIXED_CTR_CTRL:EN1_OS | cpu | none | Count MSR::FIXED_CTR1:CPU_CLK_UNHALTED_THREAD events while in kernel mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::FIXED_CTR_CTRL:EN1_PMI | cpu | none | If set, generate an interrupt when the MSR::FIXED_CTR1:CPU_CLK_UNHALTED_THREAD counter overflows. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::FIXED_CTR_CTRL:EN1_USR | cpu | none | Count MSR::FIXED_CTR1:CPU_CLK_UNHALTED_THREAD events while in user mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::FIXED_CTR_CTRL:EN2_OS | cpu | none | Count MSR::FIXED_CTR2:CPU_CLK_UNHALTED_REF_TSC events while in kernel mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::FIXED_CTR_CTRL:EN2_PMI | cpu | none | If set, generate an interrupt when the MSR::FIXED_CTR2:CPU_CLK_UNHALTED_REF_TSC counter overflows. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::FIXED_CTR_CTRL:EN2_USR | cpu | none | Count MSR::FIXED_CTR2:CPU_CLK_UNHALTED_REF_TSC events while in user mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL0:ANYTHREAD | cpu | none | If set, increment event counts when the event occurs on any hardware thread from the configured thread's core. Otherwise, only increment event counts when the configured thread triggers the event. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL0:CMASK | cpu | none | Set a mask for instances where multiple events are counted in a single clock cycle. When zero, all events are counted. When non-zero, a single event is counted when the number of event occurrences is greater or equal to the set CMASK value. |  |
| MSR::IA32_PERFEVTSEL0:EDGE | cpu | none | When set, count rising edges of the event signal instead of counting all instances where the event is observed. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL0:EN | cpu | none | Enable the counters selected in MSR::IA32_PERFEVTSEL0 if both this and MSR::PERF_GLOBAL_CTRL:EN_PMC0 are set. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL0:EVENT_SELECT | cpu | none | Set an event code to select which event logic unit to monitor. This control combined with MSR::IA32_PERFEVTSEL0:UMASK defines which event to count. See https://download.01.org/perfmon for possible input values. Event counts are accumulated in MSR::IA32_PMC0:PERFCTR. |  |
| MSR::IA32_PERFEVTSEL0:INT | cpu | none | If set, generate an interrupt when the counter overflows. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL0:INV | cpu | none | Indicates whether non-zero MSR::IA32_PERFEVTSEL0:CMASK events should be inverted. When the CMASK is inverted, increment the event count when the number of occurrences is less than the configured cutoff, instead of the default behavior of counting when the number of occurrences is greater than or equal to the cutoff. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL0:OS | cpu | none | Count events while in kernel mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL0:PC | cpu | none | Only applicable prior to the Sandy Bridge microarchitecture. When set, the processor's PMi pins are toggled (on then off in back-to-back clock cycles) when an event is counted. When cleared, only event counter overflows toggle the PMi pins. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL0:UMASK | cpu | none | Set a unit mask to select which event condition to monitor. This control combined with MSR::IA32_PERFEVTSEL0:EVENT_SELECT defines which event to count. See https://download.01.org/perfmon for possible input values. Event counts are accumulated in MSR::IA32_PMC0:PERFCTR. |  |
| MSR::IA32_PERFEVTSEL0:USR | cpu | none | Count events while in user mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL1:ANYTHREAD | cpu | none | If set, increment event counts when the event occurs on any hardware thread from the configured thread's core. Otherwise, only increment event counts when the configured thread triggers the event. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL1:CMASK | cpu | none | Set a mask for instances where multiple events are counted in a single clock cycle. When zero, all events are counted. When non-zero, a single event is counted when the number of event occurrences is greater or equal to the set CMASK value. |  |
| MSR::IA32_PERFEVTSEL1:EDGE | cpu | none | When set, count rising edges of the event signal instead of counting all instances where the event is observed. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL1:EN | cpu | none | Enable the counters selected in MSR::IA32_PERFEVTSEL1 if both this and MSR::PERF_GLOBAL_CTRL:EN_PMC1 are set. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL1:EVENT_SELECT | cpu | none | Set an event code to select which event logic unit to monitor. This control combined with MSR::IA32_PERFEVTSEL1:UMASK defines which event to count. See https://download.01.org/perfmon for possible input values. Event counts are accumulated in MSR::IA32_PMC1:PERFCTR. |  |
| MSR::IA32_PERFEVTSEL1:INT | cpu | none | If set, generate an interrupt when the counter overflows. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL1:INV | cpu | none | Indicates whether non-zero MSR::IA32_PERFEVTSEL1:CMASK events should be inverted. When the CMASK is inverted, increment the event count when the number of occurrences is less than the configured cutoff, instead of the default behavior of counting when the number of occurrences is greater than or equal to the cutoff. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL1:OS | cpu | none | Count events while in kernel mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL1:PC | cpu | none | Only applicable prior to the Sandy Bridge microarchitecture. When set, the processor's PMi pins are toggled (on then off in back-to-back clock cycles) when an event is counted. When cleared, only event counter overflows toggle the PMi pins. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL1:UMASK | cpu | none | Set a unit mask to select which event condition to monitor. This control combined with MSR::IA32_PERFEVTSEL1:EVENT_SELECT defines which event to count. See https://download.01.org/perfmon for possible input values. Event counts are accumulated in MSR::IA32_PMC1:PERFCTR. |  |
| MSR::IA32_PERFEVTSEL1:USR | cpu | none | Count events while in user mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL2:ANYTHREAD | cpu | none | If set, increment event counts when the event occurs on any hardware thread from the configured thread's core. Otherwise, only increment event counts when the configured thread triggers the event. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL2:CMASK | cpu | none | Set a mask for instances where multiple events are counted in a single clock cycle. When zero, all events are counted. When non-zero, a single event is counted when the number of event occurrences is greater or equal to the set CMASK value. |  |
| MSR::IA32_PERFEVTSEL2:EDGE | cpu | none | When set, count rising edges of the event signal instead of counting all instances where the event is observed. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL2:EN | cpu | none | Enable the counters selected in MSR::IA32_PERFEVTSEL2 if both this and MSR::PERF_GLOBAL_CTRL:EN_PMC2 are set. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL2:EVENT_SELECT | cpu | none | Set an event code to select which event logic unit to monitor. This control combined with MSR::IA32_PERFEVTSEL2:UMASK defines which event to count. See https://download.01.org/perfmon for possible input values. Event counts are accumulated in MSR::IA32_PMC2:PERFCTR. |  |
| MSR::IA32_PERFEVTSEL2:INT | cpu | none | If set, generate an interrupt when the counter overflows. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL2:INV | cpu | none | Indicates whether non-zero MSR::IA32_PERFEVTSEL2:CMASK events should be inverted. When the CMASK is inverted, increment the event count when the number of occurrences is less than the configured cutoff, instead of the default behavior of counting when the number of occurrences is greater than or equal to the cutoff. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL2:OS | cpu | none | Count events while in kernel mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL2:PC | cpu | none | Only applicable prior to the Sandy Bridge microarchitecture. When set, the processor's PMi pins are toggled (on then off in back-to-back clock cycles) when an event is counted. When cleared, only event counter overflows toggle the PMi pins. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL2:UMASK | cpu | none | Set a unit mask to select which event condition to monitor. This control combined with MSR::IA32_PERFEVTSEL2:EVENT_SELECT defines which event to count. See https://download.01.org/perfmon for possible input values. Event counts are accumulated in MSR::IA32_PMC2:PERFCTR. |  |
| MSR::IA32_PERFEVTSEL2:USR | cpu | none | Count events while in user mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL3:ANYTHREAD | cpu | none | If set, increment event counts when the event occurs on any hardware thread from the configured thread's core. Otherwise, only increment event counts when the configured thread triggers the event. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL3:CMASK | cpu | none | Set a mask for instances where multiple events are counted in a single clock cycle. When zero, all events are counted. When non-zero, a single event is counted when the number of event occurrences is greater or equal to the set CMASK value. |  |
| MSR::IA32_PERFEVTSEL3:EDGE | cpu | none | When set, count rising edges of the event signal instead of counting all instances where the event is observed. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL3:EN | cpu | none | Enable the counters selected in MSR::IA32_PERFEVTSEL3 if both this and MSR::PERF_GLOBAL_CTRL:EN_PMC3 are set. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL3:EVENT_SELECT | cpu | none | Set an event code to select which event logic unit to monitor. This control combined with MSR::IA32_PERFEVTSEL3:UMASK defines which event to count. See https://download.01.org/perfmon for possible input values. Event counts are accumulated in MSR::IA32_PMC3:PERFCTR. |  |
| MSR::IA32_PERFEVTSEL3:INT | cpu | none | If set, generate an interrupt when the counter overflows. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL3:INV | cpu | none | Indicates whether non-zero MSR::IA32_PERFEVTSEL3:CMASK events should be inverted. When the CMASK is inverted, increment the event count when the number of occurrences is less than the configured cutoff, instead of the default behavior of counting when the number of occurrences is greater than or equal to the cutoff. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL3:OS | cpu | none | Count events while in kernel mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL3:PC | cpu | none | Only applicable prior to the Sandy Bridge microarchitecture. When set, the processor's PMi pins are toggled (on then off in back-to-back clock cycles) when an event is counted. When cleared, only event counter overflows toggle the PMi pins. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PERFEVTSEL3:UMASK | cpu | none | Set a unit mask to select which event condition to monitor. This control combined with MSR::IA32_PERFEVTSEL3:EVENT_SELECT defines which event to count. See https://download.01.org/perfmon for possible input values. Event counts are accumulated in MSR::IA32_PMC3:PERFCTR. |  |
| MSR::IA32_PERFEVTSEL3:USR | cpu | none | Count events while in user mode. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::IA32_PMC0:PERFCTR | cpu | none | The count of events detected by MSR::IA32_PERFEVTSEL0. |  |
| MSR::IA32_PMC1:PERFCTR | cpu | none | The count of events detected by MSR::IA32_PERFEVTSEL1. |  |
| MSR::IA32_PMC2:PERFCTR | cpu | none | The count of events detected by MSR::IA32_PERFEVTSEL2. |  |
| MSR::IA32_PMC3:PERFCTR | cpu | none | The count of events detected by MSR::IA32_PERFEVTSEL3. |  |
| MSR::MISC_ENABLE:ENHANCED_SPEEDSTEP_TECH_ENABLE | package | none | Enable software control of P-States. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::MISC_ENABLE:FAST_STRINGS_ENABLE | package | none | Enable software control of the fast string feature for REP MOVS/STORS When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::MISC_ENABLE:LIMIT_CPUID_MAXVAL | package | none | Indicates whether the operating system does not support usage of the CPUID instruction with functions that require EAX values great than 2. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::MISC_ENABLE:TURBO_MODE_DISABLE | package | none | Indicates whether opportunistic operating frequency above the processor's base frequency is disabled. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::MISC_FEATURE_CONTROL:DCU_HW_PREFETCHER_DISABLE | cpu | none | Disable for the L1 data cache prefetcher When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::MISC_FEATURE_CONTROL:DCU_IP_PREFETCHER_DISABLE | cpu | none | Disable for the L1 data cache instruction pointer prefetcher When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::MISC_FEATURE_CONTROL:L2_ADJACENT_PREFETCHER_DISABLE | cpu | none | Disable for the L2 adjacent cache line prefetcher When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::MISC_FEATURE_CONTROL:L2_HW_PREFETCHER_DISABLE | cpu | none | Disable for the L2 hardware prefetcher. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::MPERF:MCNT | cpu | none | A counter incrementing at the processor's base, maximum performance frequency. This counter cannot measure processor performance when the CPU is inactive. |  |
| MSR::PACKAGE_THERM_INTERRUPT:THRESH_1 | package | celsius | The temperature at or above which the MSR::THERM_STATUS:THERMAL_THRESH_1_STATUS indicator is set, in degrees below MSR::TEMPERATURE_TARGET:PROCHOT_MIN. |  |
| MSR::PACKAGE_THERM_INTERRUPT:THRESH_2 | package | celsius | The temperature at or above which the MSR::THERM_STATUS:THERMAL_THRESH_2_STATUS indicator is set, in degrees below MSR::TEMPERATURE_TARGET:PROCHOT_MIN. |  |
| MSR::PACKAGE_THERM_STATUS:CRITICAL_TEMP_LOG | package | none | Indicates whether the package's on-die sensor has read a critical temperature since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:CRITICAL_TEMP_STATUS | package | none | Indicates whether the package's on-die sensor reads a critical temperature and the system cannot guarantee reliable operation. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:DIGITAL_READOUT | package | celsius | The temperature reading on this package's on-die sensor, in degrees below MSR::TEMPERATURE_TARGET:PROCHOT_MIN. |  |
| MSR::PACKAGE_THERM_STATUS:POWER_LIMIT_STATUS | package | none | Indicates whether requested P-States or requested clock duty cycles are not met due to a package power limit. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:POWER_NOTIFICATION_LOG | package | none | Indicates whether requested P-States or requested clock duty cycles were not met due to a package power limit at some point since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:PROCHOT_EVENT | package | none | Indicates whether a package high temperature (PROCHOT) or forced power reduction (FORCEPR) is being externally asserted. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:PROCHOT_LOG | package | none | Indicates whether a package high temperature (PROCHOT) or forced power reduction (FORCEPR) has been externally asserted since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:THERMAL_STATUS_FLAG | package | none | Indicates whether the package's on-die sensor reads a high temperature (PROCHOT). When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:THERMAL_STATUS_LOG | package | none | Indicates whether the package's on-die sensor has read a high temperature (PROCHOT) since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:THERMAL_THRESH_1_LOG | package | none | Indicates whether the package's on-die sensor has read equal to or hotter than the threshold in MSR::PACKAGE_THERM_INTERRUPT:THRESH_1 since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:THERMAL_THRESH_1_STATUS | package | none | Indicates whether the package's on-die sensor reads equal to or hotter than the threshold in MSR::PACKAGE_THERM_INTERRUPT:THRESH_1. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:THERMAL_THRESH_2_LOG | package | none | Indicates whether the package's on-die sensor has read equal to or hotter than the threshold in MSR::PACKAGE_THERM_INTERRUPT:THRESH_2 since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PACKAGE_THERM_STATUS:THERMAL_THRESH_2_STATUS | package | none | Indicates whether the package's on-die sensor reads equal to or hotter than the threshold in MSR::PACKAGE_THERM_INTERRUPT:THRESH_2. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PERF_CTL:FREQ | core | hertz | Target operating frequency of the CPU based on the control register. When querying at a higher domain, if NaN is returned, query at its native domain. |  |
| MSR::PERF_GLOBAL_CTRL:EN_FIXED_CTR0 | cpu | none | Enable the MSR::FIXED_CTR0:INST_RETIRED_ANY counter. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PERF_GLOBAL_CTRL:EN_FIXED_CTR1 | cpu | none | Enable the MSR::FIXED_CTR1:CPU_CLK_UNHALTED_THREAD counter. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PERF_GLOBAL_CTRL:EN_FIXED_CTR2 | cpu | none | Enable the MSR::FIXED_CTR2:CPU_CLK_UNHALTED_REF_TSC counter. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PERF_GLOBAL_CTRL:EN_PMC0 | cpu | none | Enable programmable counter 0 if both this and MSR::IA32_PERFEVTSEL0:EN are set. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PERF_GLOBAL_CTRL:EN_PMC1 | cpu | none | Enable programmable counter 1 if both this and MSR::IA32_PERFEVTSEL1:EN are set. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PERF_GLOBAL_CTRL:EN_PMC2 | cpu | none | Enable programmable counter 2 if both this and MSR::IA32_PERFEVTSEL2:EN are set. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PERF_GLOBAL_CTRL:EN_PMC3 | cpu | none | Enable programmable counter 3 if both this and MSR::IA32_PERFEVTSEL3:EN are set. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PERF_GLOBAL_OVF_CTRL:CLEAR_OVF_FIXED_CTR0 | cpu | none | Write 1 to clear the global status bit for MSR::FIXED_CTR0:INST_RETIRED_ANY overflow. |  |
| MSR::PERF_GLOBAL_OVF_CTRL:CLEAR_OVF_FIXED_CTR1 | cpu | none | Write 1 to clear the global status bit for MSR::FIXED_CTR1:CPU_CLK_UNHALTED_THREAD overflow. |  |
| MSR::PERF_GLOBAL_OVF_CTRL:CLEAR_OVF_FIXED_CTR2 | cpu | none | Write 1 to clear the global status bit for MSR::FIXED_CTR2:CPU_CLK_UNHALTED_REF_TSC overflow. |  |
| MSR::PERF_GLOBAL_OVF_CTRL:CLEAR_OVF_PMC0 | cpu | none | Write 1 to clear the global status bit for PMC0 overflow. |  |
| MSR::PERF_GLOBAL_OVF_CTRL:CLEAR_OVF_PMC1 | cpu | none | Write 1 to clear the global status bit for PMC1 overflow. |  |
| MSR::PERF_GLOBAL_OVF_CTRL:CLEAR_OVF_PMC2 | cpu | none | Write 1 to clear the global status bit for PMC2 overflow. |  |
| MSR::PERF_GLOBAL_OVF_CTRL:CLEAR_OVF_PMC3 | cpu | none | Write 1 to clear the global status bit for PMC3 overflow. |  |
| MSR::PERF_STATUS:FREQ | cpu | hertz | The current operating frequency of the CPU. |  |
| MSR::PKG_ENERGY_STATUS:ENERGY | package | joules | An increasing meter of energy consumed by the package over time.  It will reset periodically due to roll-over. |  |
| MSR::PKG_POWER_INFO:MAX_POWER | package | watts | The maximum power limit based on the electrical specification. |  |
| MSR::PKG_POWER_INFO:MAX_TIME_WINDOW | package | seconds | The maximum time accepted in MSR::PKG_POWER_LIMIT:PL1_TIME_WINDOW and MSR::PKG_POWER_LIMIT:PL2_TIME_WINDOW. |  |
| MSR::PKG_POWER_INFO:MIN_POWER | package | watts | The minimum power limit based on the electrical specification. |  |
| MSR::PKG_POWER_INFO:THERMAL_SPEC_POWER | package | watts | Maximum power to stay within the thermal limits based on the design (TDP). |  |
| MSR::PKG_POWER_LIMIT:LOCK | package | none | Ignore any changes to PL1 and PL2 configuration in PKG_POWER_LIMIT until the next reset. |  |
| MSR::PKG_POWER_LIMIT:PL1_CLAMP_ENABLE | package | none | Allow processor cores to go below the requested P-State or T-State to achieve the requested PL1_POWER_LIMIT. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PKG_POWER_LIMIT:PL1_LIMIT_ENABLE | package | none | Enable the limit specified in PL1_POWER_LIMIT. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PKG_POWER_LIMIT:PL1_POWER_LIMIT | package | watts | The average power usage limit over the time window specified in PL1_TIME_WINDOW. |  |
| MSR::PKG_POWER_LIMIT:PL1_TIME_WINDOW | package | seconds | The time window associated with power limit 1. |  |
| MSR::PKG_POWER_LIMIT:PL2_CLAMP_ENABLE | package | none | Allow processor cores to go below the requested P-State or T-State to achieve the requested PL2_POWER_LIMIT. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PKG_POWER_LIMIT:PL2_LIMIT_ENABLE | package | none | Enable the limit specified in PL2_POWER_LIMIT. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PKG_POWER_LIMIT:PL2_POWER_LIMIT | package | watts | The average power usage limit over the time window specified in PL2_TIME_WINDOW. |  |
| MSR::PKG_POWER_LIMIT:PL2_TIME_WINDOW | package | seconds | The time window associated with power limit 2. |  |
| MSR::PLATFORM_ENERGY_STATUS:ENERGY | board | joules | An increasing meter of energy in Joules (U32.0) consumed by the board over time. |  |
| MSR::PLATFORM_INFO:MAX_EFFICIENCY_RATIO | package | hertz | The minimum operating frequency of the processor. |  |
| MSR::PLATFORM_INFO:MAX_NON_TURBO_RATIO | package | hertz | The processor's maximum non-turbo frequency. |  |
| MSR::PLATFORM_INFO:PROGRAMMABLE_RATIO_LIMITS_TURBO_MODE | package | none | Indicates whether the MSR::TURBO_RATIO_LIMIT:* signals are also available as controls. |  |
| MSR::PLATFORM_INFO:PROGRAMMABLE_TCC_ACTIVATION_OFFSET | package | none | Indicates whether the platform permits writes to MSR::TEMPERATURE_TARGET:TCC_ACTIVE_OFFSET. |  |
| MSR::PLATFORM_INFO:PROGRAMMABLE_TDP_LIMITS_TURBO_MODE | package | none | Indicates whether this platform supports programmable TDP limits for turbo mode. |  |
| MSR::PLATFORM_POWER_LIMIT:LOCK | board | none | Ignore any changes to PL1 and PL2 configuration in PLATFORM_POWER_LIMIT until the next reset. |  |
| MSR::PLATFORM_POWER_LIMIT:PL1_CLAMP_ENABLE | board | none | Allow hardware to go below the requested P-State to achieve the requested board PL1_POWER_LIMIT. |  |
| MSR::PLATFORM_POWER_LIMIT:PL1_LIMIT_ENABLE | board | none | Enable the limit specified in board PL1_POWER_LIMIT. |  |
| MSR::PLATFORM_POWER_LIMIT:PL1_POWER_LIMIT | board | watts | The average board power usage limit over the time window specified in the board PL1_TIME_WINDOW. |  |
| MSR::PLATFORM_POWER_LIMIT:PL1_TIME_WINDOW | board | seconds | The time window associated with the board PL1_POWER_LIMIT |  |
| MSR::PM_ENABLE:HWP_ENABLE | package | none | Indicates HWP enabled status.  Once enabled a system reset is required to disable. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::PPERF:PCNT | cpu | none | A filtered counter of MSR::APERF:ACNT that only increments for cycles the hardware expects are productive toward instruction execution. This counter cannot measure processor performance when the CPU is inactive. |  |
| MSR::PQR_ASSOC:RMID | cpu | none | The resource monitoring identifier (RMID) currently associated with this CPU. Multiple CPUs are permitted to map to the same RMID. RMID-based resource monitoring interfaces track each monitored resource by a CPU package, RMID pair. |  |
| MSR::QM_CTR:ERROR | package | none | Indicates an unsupported configuration in MSR::QM_EVTSEL:*, and that MSR::QM_CTR:RM_DATA does not contain valid data. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::QM_CTR:RM_DATA | package | none | The raw counted value for the MSR::QM_EVTSEL:* configuration. Configurations that report bandwidth metrics report a raw value based on an implementation-specific counter. If reading a bandwidth metric, read the QM_CTR_SCALED alias instead. |  |
| MSR::QM_CTR:UNAVAILABLE | package | none | Indicates that no monitoring data is available, and MSR::QM_CTR:RM_DATA does not contain valid data. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::QM_CTR_SCALED | package | none | Resource Monitor Data converted to bytes | MSR::QM_CTR:RM_DATA multiplied by 114688 (provided by cpuid) |
| MSR::QM_CTR_SCALED_RATE | package | none | Resource Monitor Data converted to bytes/second | MSR::QM_CTR_SCALED rate of change |
| MSR::QM_EVTSEL:EVENT_ID | package | none | Set an event code to choose which resource is monitored in MSR::QM_CTR:RM_DATA. Refer to the Intel(R) 64 and IA-32 Architectures Software Developer's Manual for more information about how to use this MSR with Cache Monitoring Technology and Memory Bandwidth Monitoring. Event counts are accumulated in MSR::QM_CTR::RM_DATA. |  |
| MSR::QM_EVTSEL:RMID | package | none | Specify which resource monitoring identifier (RMID) must be active to update MSR::QM_CTR:RM_DATA. Associate RMIDs with CPUs by writing to MSR::PQR_ASSOC:RMID. |  |
| MSR::RAPL_POWER_UNIT:ENERGY | package | joules | The resolution of RAPL energy interfaces. |  |
| MSR::RAPL_POWER_UNIT:POWER | package | watts | The resolution of RAPL power interfaces. |  |
| MSR::RAPL_POWER_UNIT:TIME | package | seconds | The resolution of RAPL time interfaces. |  |
| MSR::TEMPERATURE_TARGET:PROCHOT_MIN | core | celsius | The lowest temperature considered a high temperature. Measured temperatures at or above this value will generate a PROCHOT event. |  |
| MSR::TEMPERATURE_TARGET:TCC_ACTIVE_OFFSET | core | celsius | An offset to subtract from MSR::TEMPERATURE_TARGET:PROCHOT_MIN as the cutoff to generate a PROCHOT event. |  |
| MSR::THERM_INTERRUPT:THRESH_1 | core | celsius | The temperature at or above which the MSR::THERM_STATUS:THERMAL_THRESH_1_STATUS indicator is set, in degrees below MSR::TEMPERATURE_TARGET:PROCHOT_MIN. |  |
| MSR::THERM_INTERRUPT:THRESH_2 | core | celsius | The temperature at or above which the MSR::THERM_STATUS:THERMAL_THRESH_2_STATUS indicator is set, in degrees below MSR::TEMPERATURE_TARGET:PROCHOT_MIN. |  |
| MSR::THERM_STATUS:CRITICAL_TEMP_LOG | core | none | Indicates whether the core's on-die sensor has read a critical temperature since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:CRITICAL_TEMP_STATUS | core | none | Indicates whether the core's on-die sensor reads a critical temperature and the system cannot guarantee reliable operation. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:DIGITAL_READOUT | core | celsius | The temperature reading on this core's on-die sensor, in degrees below MSR::TEMPERATURE_TARGET:PROCHOT_MIN. |  |
| MSR::THERM_STATUS:POWER_LIMIT_STATUS | core | none | Indicates whether requested P-States or requested clock duty cycles are not met. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:POWER_NOTIFICATION_LOG | core | none | Indicates whether requested P-States or requested clock duty cycles were not met at some point since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:PROCHOT_EVENT | core | none | Indicates whether a high temperature (PROCHOT) or forced power reduction (FORCEPR) is being externally asserted. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:PROCHOT_LOG | core | none | Indicates whether a high temperature (PROCHOT) or forced power reduction (FORCEPR) has been externally asserted since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:READING_VALID | core | none | Indicates whether MSR::THERM_STATUS:DIGITAL_READOUT contains a valid temperature readout. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:RESOLUTION | core | celsius | The resolution of the sensor that measures MSR::THERM_STATUS:DIGITAL_READOUT temperature. |  |
| MSR::THERM_STATUS:THERMAL_STATUS_FLAG | core | none | Indicates whether the core's on-die sensor reads a high temperature (PROCHOT). When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:THERMAL_STATUS_LOG | core | none | Indicates whether the core's on-die sensor has read a high temperature (PROCHOT) since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:THERMAL_THRESH_1_LOG | core | none | Indicates whether the core's on-die sensor has read equal to or hotter than the threshold in MSR::THERM_INTERRUPT:THRESH_1 since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:THERMAL_THRESH_1_STATUS | core | none | Indicates whether the core's on-die sensor reads equal to or hotter than the threshold in MSR::THERM_INTERRUPT:THRESH_1. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:THERMAL_THRESH_2_LOG | core | none | Indicates whether the core's on-die sensor has read equal to or hotter than the threshold in MSR::THERM_INTERRUPT:THRESH_2 since the last time a zero was written to this control. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::THERM_STATUS:THERMAL_THRESH_2_STATUS | core | none | Indicates whether the core's on-die sensor reads equal to or hotter than the threshold in MSR::THERM_INTERRUPT:THRESH_2. When reading at a higher level domain than its native domain, it aggregates as the count of all such bits that have been set. |  |
| MSR::TIME | board | seconds | Time in seconds used to calculate power |  |
| MSR::TIME_STAMP_COUNTER:TIMESTAMP_COUNT | cpu | none | An always running, monotonically increasing counter that is incremented at a constant rate.  For use as a wall clock timer. |  |
| MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_0 | package | hertz | Maximum turbo frequency with up to MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_0 active cores. |  |
| MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_1 | package | hertz | Maximum turbo frequency with more than MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_0 and up to MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_1 active cores. |  |
| MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_2 | package | hertz | Maximum turbo frequency with more than MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_1 and up to MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_2 active cores. |  |
| MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_3 | package | hertz | Maximum turbo frequency with more than MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_2 and up to MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_3 active cores. |  |
| MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_4 | package | hertz | Maximum turbo frequency with more than MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_3 and up to MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_4 active cores. |  |
| MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_5 | package | hertz | Maximum turbo frequency with more than MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_4 and up to MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_5 active cores. |  |
| MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_6 | package | hertz | Maximum turbo frequency with more than MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_5 and up to MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_6 active cores. |  |
| MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_7 | package | hertz | Maximum turbo frequency with more than MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_6 and up to MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_7 active cores. |  |
| MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_0 | package | none | Maximum number of active cores for a maximum turbo frequency of MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_0. |  |
| MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_1 | package | none | Maximum number of active cores for a maximum turbo frequency of MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_1. |  |
| MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_2 | package | none | Maximum number of active cores for a maximum turbo frequency of MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_2. |  |
| MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_3 | package | none | Maximum number of active cores for a maximum turbo frequency of MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_3. |  |
| MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_4 | package | none | Maximum number of active cores for a maximum turbo frequency of MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_4. |  |
| MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_5 | package | none | Maximum number of active cores for a maximum turbo frequency of MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_5. |  |
| MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_6 | package | none | Maximum number of active cores for a maximum turbo frequency of MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_6. |  |
| MSR::TURBO_RATIO_LIMIT_CORES:NUMCORE_7 | package | none | Maximum number of active cores for a maximum turbo frequency of MSR::TURBO_RATIO_LIMIT:MAX_RATIO_LIMIT_7. |  |
| MSR::UNCORE_PERF_STATUS:FREQ | package | hertz | The current uncore frequency. |  |
| MSR::UNCORE_RATIO_LIMIT:MAX_RATIO | package | hertz | An upper limit for uncore frequency control. When querying at a higher domain, if NaN is returned, query at its native domain. |  |
| MSR::UNCORE_RATIO_LIMIT:MIN_RATIO | package | hertz | A lower limit for uncore frequency control. When querying at a higher domain, if NaN is returned, query at its native domain. |  |
| POWERCAP::CPU_ENERGY_CONSUMED | package | joules | CPU energy consumed in joules. |  |
| POWERCAP::CPU_MAX_ENERGY_RANGE | package | joules | Rollover value in units of joules. |  |
| POWERCAP::CPU_POWER_LIMIT | package | watts | CPU power limit in watts. |  |
| POWERCAP::CPU_TIME_WINDOW | package | seconds | CPU power limit time window in seconds. |  |
| POWERCAP::DRAM_ENERGY_CONSUMED | package | joules | DRAM energy consumed in joules. |  |
| POWERCAP::DRAM_POWER_LIMIT | package | watts | DRAM power limit in watts. |  |
| POWERCAP::DRAM_TIME_WINDOW | package | seconds | DRAM power limit time window in seconds. |  |
| SST::CONFIG_LEVEL:LEVEL | package | none | SST configuration level |  |
| SST::COREPRIORITY:0:FREQUENCY_MAX | package | hertz | Maximum frequency of core priority level 0 |  |
| SST::COREPRIORITY:0:FREQUENCY_MIN | package | hertz | Minimum frequency of core priority level 0 |  |
| SST::COREPRIORITY:0:PRIORITY | package | none | Proportional priority for core priority level 0, ranging from 0 to 1. A lower value indicates a desire to receive a greater share of surplus power than priority groups with a higher value. |  |
| SST::COREPRIORITY:1:FREQUENCY_MAX | package | hertz | Maximum frequency of core priority level 1 |  |
| SST::COREPRIORITY:1:FREQUENCY_MIN | package | hertz | Minimum frequency of core priority level 1 |  |
| SST::COREPRIORITY:1:PRIORITY | package | none | Proportional priority for core priority level 1, ranging from 0 to 1. A lower value indicates a desire to receive a greater share of surplus power than priority groups with a higher value. |  |
| SST::COREPRIORITY:2:FREQUENCY_MAX | package | hertz | Maximum frequency of core priority level 2 |  |
| SST::COREPRIORITY:2:FREQUENCY_MIN | package | hertz | Minimum frequency of core priority level 2 |  |
| SST::COREPRIORITY:2:PRIORITY | package | none | Proportional priority for core priority level 2, ranging from 0 to 1. A lower value indicates a desire to receive a greater share of surplus power than priority groups with a higher value. |  |
| SST::COREPRIORITY:3:FREQUENCY_MAX | package | hertz | Maximum frequency of core priority level 3 |  |
| SST::COREPRIORITY:3:FREQUENCY_MIN | package | hertz | Minimum frequency of core priority level 3 |  |
| SST::COREPRIORITY:3:PRIORITY | package | none | Proportional priority for core priority level 3, ranging from 0 to 1. A lower value indicates a desire to receive a greater share of surplus power than priority groups with a higher value. |  |
| SST::COREPRIORITY:ASSOCIATION | core | none | Assigned core priority level |  |
| SST::COREPRIORITY_ENABLE:ENABLE | package | none | SST-CP is enabled. Disabling this also disables SST::TURBO_ENABLE:ENABLE. |  |
| SST::COREPRIORITY_SUPPORT:CAPABILITIES | package | none | SST-CP is supported |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX2:0 | package | hertz | High-priority turbo frequency for bucket 0 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX2:1 | package | hertz | High-priority turbo frequency for bucket 1 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX2:2 | package | hertz | High-priority turbo frequency for bucket 2 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX2:3 | package | hertz | High-priority turbo frequency for bucket 3 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX2:4 | package | hertz | High-priority turbo frequency for bucket 4 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX2:5 | package | hertz | High-priority turbo frequency for bucket 5 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX2:6 | package | hertz | High-priority turbo frequency for bucket 6 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX2:7 | package | hertz | High-priority turbo frequency for bucket 7 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX512:0 | package | hertz | High-priority turbo frequency for bucket 0 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX512:1 | package | hertz | High-priority turbo frequency for bucket 1 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX512:2 | package | hertz | High-priority turbo frequency for bucket 2 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX512:3 | package | hertz | High-priority turbo frequency for bucket 3 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX512:4 | package | hertz | High-priority turbo frequency for bucket 4 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX512:5 | package | hertz | High-priority turbo frequency for bucket 5 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX512:6 | package | hertz | High-priority turbo frequency for bucket 6 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_AVX512:7 | package | hertz | High-priority turbo frequency for bucket 7 at the AVX2 license level |  |
| SST::HIGHPRIORITY_FREQUENCY_SSE:0 | package | hertz | High-priority turbo frequency for bucket 0 at the SSE license level |  |
| SST::HIGHPRIORITY_FREQUENCY_SSE:1 | package | hertz | High-priority turbo frequency for bucket 1 at the SSE license level |  |
| SST::HIGHPRIORITY_FREQUENCY_SSE:2 | package | hertz | High-priority turbo frequency for bucket 2 at the SSE license level |  |
| SST::HIGHPRIORITY_FREQUENCY_SSE:3 | package | hertz | High-priority turbo frequency for bucket 3 at the SSE license level |  |
| SST::HIGHPRIORITY_FREQUENCY_SSE:4 | package | hertz | High-priority turbo frequency for bucket 4 at the SSE license level |  |
| SST::HIGHPRIORITY_FREQUENCY_SSE:5 | package | hertz | High-priority turbo frequency for bucket 5 at the SSE license level |  |
| SST::HIGHPRIORITY_FREQUENCY_SSE:6 | package | hertz | High-priority turbo frequency for bucket 6 at the SSE license level |  |
| SST::HIGHPRIORITY_FREQUENCY_SSE:7 | package | hertz | High-priority turbo frequency for bucket 7 at the SSE license level |  |
| SST::HIGHPRIORITY_NCORES:0 | package | none | Count of high-priority turbo frequency cores in bucket 0 |  |
| SST::HIGHPRIORITY_NCORES:1 | package | none | Count of high-priority turbo frequency cores in bucket 1 |  |
| SST::HIGHPRIORITY_NCORES:2 | package | none | Count of high-priority turbo frequency cores in bucket 2 |  |
| SST::HIGHPRIORITY_NCORES:3 | package | none | Count of high-priority turbo frequency cores in bucket 3 |  |
| SST::HIGHPRIORITY_NCORES:4 | package | none | Count of high-priority turbo frequency cores in bucket 4 |  |
| SST::HIGHPRIORITY_NCORES:5 | package | none | Count of high-priority turbo frequency cores in bucket 5 |  |
| SST::HIGHPRIORITY_NCORES:6 | package | none | Count of high-priority turbo frequency cores in bucket 6 |  |
| SST::HIGHPRIORITY_NCORES:7 | package | none | Count of high-priority turbo frequency cores in bucket 7 |  |
| SST::LOWPRIORITY_FREQUENCY:AVX2 | package | hertz | Low-priority turbo frequency at the AVX2 license level |  |
| SST::LOWPRIORITY_FREQUENCY:AVX512 | package | hertz | Low-priority turbo frequency at the AVX512 license level |  |
| SST::LOWPRIORITY_FREQUENCY:SSE | package | hertz | Low-priority turbo frequency at the SSE license level |  |
| SST::TURBOFREQ_SUPPORT:SUPPORTED | package | none | SST-TF is supported |  |
| SST::TURBO_ENABLE:ENABLE | package | none | SST-TF is enabled. Enabling this also enables SST::COREPRIORITY_ENABLE:ENABLE. |  |
| TIME | cpu | seconds | Time since the start of application profiling. | TIME::ELAPSED |
| TIME::ELAPSED | cpu | seconds | Time since the start of application profiling. |  |
