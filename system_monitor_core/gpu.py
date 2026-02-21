"""
GPU metrics collection using pynvml.

Units:
- utilization_percent: percentage (%)
- memory_used_mb, memory_total_mb: MB
- temperature_celsius: Celsius (°C)
- power_watts: Watts (W)
"""

import platform
from typing import TypedDict, List
import time

try:
    import pynvml
    _PYNVML_AVAILABLE = True
except ImportError:
    _PYNVML_AVAILABLE = False

OS_TYPE = platform.system()


class GPUInfo(TypedDict):
    index: int
    utilization_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_celsius: float
    power_watts: float


class GPUStatic(TypedDict):
    count: int
    names: List[str]


class GPUDynamic(TypedDict):
    gpus: List[GPUInfo]


def get_gpu_static_metadata() -> GPUStatic:
    count = 0
    names = []

    if not _PYNVML_AVAILABLE:
        return {'count': count, 'names': names}

    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes):
                name = name.decode('utf-8')
            names.append(name)
        pynvml.nvmlShutdown()
    except Exception:
        pass

    return {'count': count, 'names': names}


def get_gpu_dynamic_metrics() -> GPUDynamic:
    gpus = []

    if not _PYNVML_AVAILABLE:
        return {'gpus': gpus}

    try:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()

        for i in range(count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)

            try:
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                utilization_percent = float(util.gpu)
            except pynvml.NVMLError:
                utilization_percent = -1.0

            try:
                mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
                memory_used_mb = mem.used / (1024 * 1024)
                memory_total_mb = mem.total / (1024 * 1024)
            except pynvml.NVMLError:
                memory_used_mb = -1.0
                memory_total_mb = -1.0

            try:
                temperature_celsius = float(
                    pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                )
            except pynvml.NVMLError:
                temperature_celsius = -1.0

            try:
                power_watts = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
            except pynvml.NVMLError:
                power_watts = -1.0

            gpus.append({
                'index': i,
                'utilization_percent': utilization_percent,
                'memory_used_mb': memory_used_mb,
                'memory_total_mb': memory_total_mb,
                'temperature_celsius': temperature_celsius,
                'power_watts': power_watts,
            })

        pynvml.nvmlShutdown()
    except Exception:
        pass

    return {'gpus': gpus}


if __name__ == "__main__":
    start_time = time.perf_counter()

    def print_with_type(prefix, value):
        print(f"{prefix}: {value} (type={type(value).__name__})")

    print("=== GPU Static Metadata ===")
    static = get_gpu_static_metadata()
    print_with_type("static", static)
    for key, value in static.items():
        print_with_type(f"static.{key}", value)
        if isinstance(value, list):
            for idx, item in enumerate(value):
                print_with_type(f"static.{key}[{idx}]", item)

    print("\n=== GPU Dynamic Metrics ===")
    dynamic = get_gpu_dynamic_metrics()
    print_with_type("dynamic", dynamic)
    for key, value in dynamic.items():
        print_with_type(f"dynamic.{key}", value)
        if isinstance(value, list):
            for idx, item in enumerate(value):
                print_with_type(f"dynamic.{key}[{idx}]", item)
                if isinstance(item, dict):
                    for sub_key, sub_value in item.items():
                        print_with_type(f"dynamic.{key}[{idx}].{sub_key}", sub_value)

    elapsed = time.perf_counter() - start_time
    print(f"\nTime taken: {elapsed:.4f} seconds")
