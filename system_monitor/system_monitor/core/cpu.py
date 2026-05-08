"""
CPU metrics collection.

Units:
- freq_current_mhz: MHz
- temperature_celsius: Celsius (°C)
- load_avg_1m/5m/15m: 1/5/15 minute averages
- user_seconds, system_seconds, idle_seconds, iowait_seconds: seconds
- ctx_switches, interrupts, soft_interrupts: count
- usage_percent: percentage (%)
"""

import psutil
import platform
from typing import TypedDict
import time

OS_TYPE = platform.system()


class CPUStatic(TypedDict):
    logical_cores: int
    physical_cores: int
    freq_min: float
    freq_max: float


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


def get_cpu_static_metadata() -> CPUStatic:
    freq = psutil.cpu_freq()
    return {
        'logical_cores': psutil.cpu_count(logical=True),
        'physical_cores': psutil.cpu_count(logical=False),
        'freq_min': freq.min,
        'freq_max': freq.max
    }


def get_cpu_dynamic_metrics() -> CPUDynamic:
    times = psutil.cpu_times()
    stats = psutil.cpu_stats()
    freq = psutil.cpu_freq()

    temperature_celsius = -1.0
    load_avg_1m = -1.0
    load_avg_5m = -1.0
    load_avg_15m = -1.0
    iowait_seconds = -1.0

    match OS_TYPE:
        case 'Linux':
            temps = psutil.sensors_temperatures()
            sensor_list = temps.get('coretemp', temps.get('cpu_thermal', temps.get('k10temp', temps.get('zenpower', []))))
            temperature_celsius = float(sensor_list[0].current) if sensor_list else -1.0
            load_avg = psutil.getloadavg()
            load_avg_1m, load_avg_5m, load_avg_15m = float(load_avg[0]), float(load_avg[1]), float(load_avg[2])
            iowait_seconds = float(times.iowait)
        case 'Darwin':
            load_avg = psutil.getloadavg()
            load_avg_1m, load_avg_5m, load_avg_15m = float(load_avg[0]), float(load_avg[1]), float(load_avg[2])
            iowait_seconds = float(times.iowait)
        case 'Windows':
            pass

    return {
        'usage_percent': psutil.cpu_percent(interval=None),
        'freq_current_mhz': freq.current,
        'temperature_celsius': temperature_celsius,
        'load_avg_1m': load_avg_1m,
        'load_avg_5m': load_avg_5m,
        'load_avg_15m': load_avg_15m,
        'iowait_seconds': iowait_seconds,
        'user_seconds': times.user,
        'system_seconds': times.system,
        'idle_seconds': times.idle,
        'ctx_switches': stats.ctx_switches,
        'interrupts': stats.interrupts,
        'soft_interrupts': stats.soft_interrupts
    }


if __name__ == "__main__":
    start_time = time.perf_counter()

    warmup()
    time.sleep(0.1)

    print("=== CPU Static Metadata ===")
    static = get_cpu_static_metadata()
    for key, value in static.items():
        print(f"{key}: {value}")

    print("\n=== CPU Dynamic Metrics ===")
    dynamic = get_cpu_dynamic_metrics()
    for key, value in dynamic.items():
        print(f"{key}: {value}")

    elapsed = time.perf_counter() - start_time
    print(f"\nTime taken: {elapsed:.4f} seconds")
