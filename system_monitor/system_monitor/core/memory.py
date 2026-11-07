"""Memory metrics from psutil. Sizes are bytes; swap_sin and swap_sout are cumulative."""

from typing import TypedDict

import psutil


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


def get_memory_dynamic_metrics() -> MemoryDynamic:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()

    return {
        'total': vm.total,
        'available': vm.available,
        'used': vm.used,
        'free': vm.free,
        'percent': vm.percent,
        'active': vm.active,
        'inactive': vm.inactive,
        'buffers': vm.buffers,
        'cached': vm.cached,
        'shared': vm.shared,
        'slab': vm.slab,
        'swap_total': swap.total,
        'swap_used': swap.used,
        'swap_free': swap.free,
        'swap_percent': swap.percent,
        'swap_sin': swap.sin,
        'swap_sout': swap.sout,
    }
