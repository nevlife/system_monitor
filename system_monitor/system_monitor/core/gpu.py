"""
GPU metrics collection using pynvml.

Units:
- utilization_percent: percentage (%)
- memory_used_mb, memory_total_mb: MB
- temperature_celsius: Celsius (°C)
- power_watts: Watts (W)

NVML is initialised once per GpuSampler instance and shut down via close().
"""

import platform
from typing import TypedDict, List, Dict, Any
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


class GpuSampler:
    def __init__(self) -> None:
        self._initialized = False
        self._handles: list = []

        if not _PYNVML_AVAILABLE:
            return

        try:
            pynvml.nvmlInit()
            self._initialized = True
            count = pynvml.nvmlDeviceGetCount()
            self._handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(count)]
        except Exception:
            self._initialized = False
            self._handles = []

    def close(self) -> None:
        if self._initialized:
            try:
                pynvml.nvmlShutdown()
            except Exception:
                pass
            self._initialized = False
            self._handles = []

    def static_metadata(self) -> GPUStatic:
        if not self._initialized:
            return {'count': 0, 'names': []}

        names: List[str] = []
        for handle in self._handles:
            try:
                name = pynvml.nvmlDeviceGetName(handle)
                if isinstance(name, bytes):
                    name = name.decode('utf-8')
                names.append(name)
            except pynvml.NVMLError:
                names.append('unknown')

        return {'count': len(self._handles), 'names': names}

    def sample(self) -> GPUDynamic:
        gpus: List[GPUInfo] = []

        if not self._initialized:
            return {'gpus': gpus}

        for i, handle in enumerate(self._handles):
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

        return {'gpus': gpus}


if __name__ == "__main__":
    start_time = time.perf_counter()

    sampler = GpuSampler()
    try:
        print("=== GPU Static Metadata ===")
        static = sampler.static_metadata()
        for key, value in static.items():
            print(f"{key}: {value}")

        print("\n=== GPU Dynamic Metrics ===")
        dynamic = sampler.sample()
        for key, value in dynamic.items():
            print(f"{key}: {value}")
    finally:
        sampler.close()

    elapsed = time.perf_counter() - start_time
    print(f"\nTime taken: {elapsed:.4f} seconds")
