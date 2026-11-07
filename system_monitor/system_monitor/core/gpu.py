"""GPU metrics from NVML. NVML is initialised per GpuSampler and shut down by close()."""

from typing import List, TypedDict

import pynvml


class GPUInfo(TypedDict):
    index: int
    utilization_percent: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_celsius: float
    power_watts: float


class GPUDynamic(TypedDict):
    gpus: List[GPUInfo]


def read_or_unsupported(read, *args) -> float:
    # Utilization, temperature and power readings are optional in NVML; some boards
    # report NOT_SUPPORTED for them. Any other NVML error propagates.
    try:
        return float(read(*args))
    except pynvml.NVMLError_NotSupported:
        return -1.0


class GpuSampler:
    def __init__(self) -> None:
        pynvml.nvmlInit()
        count = pynvml.nvmlDeviceGetCount()
        self._handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(count)]

    def close(self) -> None:
        pynvml.nvmlShutdown()

    def sample(self) -> GPUDynamic:
        gpus: List[GPUInfo] = []
        for i, handle in enumerate(self._handles):
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            gpus.append(
                {
                    'index': i,
                    'utilization_percent': read_or_unsupported(
                        lambda h: pynvml.nvmlDeviceGetUtilizationRates(h).gpu, handle
                    ),
                    'memory_used_mb': mem.used / (1024 * 1024),
                    'memory_total_mb': mem.total / (1024 * 1024),
                    'temperature_celsius': read_or_unsupported(
                        pynvml.nvmlDeviceGetTemperature, handle, pynvml.NVML_TEMPERATURE_GPU
                    ),
                    'power_watts': read_or_unsupported(
                        lambda h: pynvml.nvmlDeviceGetPowerUsage(h) / 1000.0, handle
                    ),
                }
            )
        return {'gpus': gpus}
