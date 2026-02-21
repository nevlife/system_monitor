"""
Memory metrics collection.

Units:
- total, available, used, free: bytes
- active, inactive, buffers, cached, shared, slab: bytes
- percent, swap_percent: percentage (%)
- swap_total, swap_used, swap_free: bytes
- swap_sin, swap_sout: bytes (cumulative)
"""

import psutil
import platform
from typing import TypedDict
import time

OS_TYPE = platform.system()


class MemoryStatic(TypedDict):
    total: int
    swap_total: int


class MemoryDynamic(TypedDict):
    total: int
    available: int
    used: int
    free: int
    percent: float
    active: int
    inactive: int
    buffers: int
    cached: int
    shared: int
    slab: int
    swap_total: int
    swap_used: int
    swap_free: int
    swap_percent: float
    swap_sin: int
    swap_sout: int


def get_memory_static_metadata() -> MemoryStatic:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        'total': vm.total,
        'swap_total': swap.total
    }


def get_memory_dynamic_metrics() -> MemoryDynamic:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    active = -1
    inactive = -1
    buffers = -1
    cached = -1
    shared = -1
    slab = -1
    swap_sin = -1
    swap_sout = -1

    match OS_TYPE:
        case 'Linux':
            active = vm.active
            inactive = vm.inactive
            buffers = vm.buffers
            cached = vm.cached
            shared = vm.shared
            slab = vm.slab
            swap_sin = swap.sin
            swap_sout = swap.sout
        case 'Darwin':
            active = vm.active
            inactive = vm.inactive
        case 'Windows':
            pass

    return {
        'total': vm.total,
        'available': vm.available,
        'used': vm.used,
        'free': vm.free,
        'percent': vm.percent,
        'active': active,
        'inactive': inactive,
        'buffers': buffers,
        'cached': cached,
        'shared': shared,
        'slab': slab,
        'swap_total': swap.total,
        'swap_used': swap.used,
        'swap_free': swap.free,
        'swap_percent': swap.percent,
        'swap_sin': swap_sin,
        'swap_sout': swap_sout
    }


if __name__ == "__main__":
    start_time = time.perf_counter()

    print("=== Memory Static Metadata ===")
    static = get_memory_static_metadata()
    for key, value in static.items():
        print(f"{key}: {value}")

    print("\n=== Memory Dynamic Metrics ===")
    dynamic = get_memory_dynamic_metrics()
    for key, value in dynamic.items():
        print(f"{key}: {value}")

    elapsed = time.perf_counter() - start_time
    print(f"\nTime taken: {elapsed:.4f} seconds")
