"""CPU metrics from psutil. Times are cumulative seconds; usage is a percentage."""

from typing import TypedDict

import psutil

# The kernel driver that reports the package temperature depends on the CPU vendor
# (Intel, AMD, ARM boards), and a machine may have none of them.
TEMPERATURE_SENSORS = ('coretemp', 'cpu_thermal', 'k10temp', 'zenpower')


class CPUDynamic(TypedDict):
    usage_percent: float
    freq_current_mhz: float
    temperature_celsius: float
    load_avg_1m: float
    load_avg_5m: float
    load_avg_15m: float
    iowait_seconds: float
    user_seconds: float
    system_seconds: float
    idle_seconds: float
    ctx_switches: int
    interrupts: int
    soft_interrupts: int


def warmup() -> None:
    # Prime psutil's internal cpu_percent state so subsequent non-blocking
    # calls return a meaningful delta instead of 0.0.
    psutil.cpu_percent(interval=None)


def cpu_temperature(temps: dict) -> float:
    for name in TEMPERATURE_SENSORS:
        if temps.get(name):
            return float(temps[name][0].current)
    return -1.0


def get_cpu_dynamic_metrics() -> CPUDynamic:
    times = psutil.cpu_times()
    stats = psutil.cpu_stats()
    freq = psutil.cpu_freq()
    load_avg_1m, load_avg_5m, load_avg_15m = psutil.getloadavg()

    return {
        'usage_percent': psutil.cpu_percent(interval=None),
        'freq_current_mhz': freq.current,
        'temperature_celsius': cpu_temperature(psutil.sensors_temperatures()),
        'load_avg_1m': float(load_avg_1m),
        'load_avg_5m': float(load_avg_5m),
        'load_avg_15m': float(load_avg_15m),
        'iowait_seconds': float(times.iowait),
        'user_seconds': times.user,
        'system_seconds': times.system,
        'idle_seconds': times.idle,
        'ctx_switches': stats.ctx_switches,
        'interrupts': stats.interrupts,
        'soft_interrupts': stats.soft_interrupts,
    }
