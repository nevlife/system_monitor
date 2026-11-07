"""
Disk metrics collection.

Units:
- total_bytes, used_bytes, free_bytes: bytes
- percent: percentage (%)
- io_read_count, io_write_count: count (cumulative)
- io_read_bytes, io_write_bytes: bytes (cumulative)
- io_read_time_ms, io_write_time_ms, io_busy_time_ms: milliseconds (cumulative)
"""

from typing import List, TypedDict

import psutil


class DiskPartitionUsage(TypedDict):
    mountpoint: str
    total_bytes: int
    used_bytes: int
    free_bytes: int
    percent: float
    accessible: bool


class DiskIOCounters(TypedDict):
    io_read_count: int
    io_write_count: int
    io_read_bytes: int
    io_write_bytes: int
    io_read_time_ms: int
    io_write_time_ms: int
    io_busy_time_ms: int


def get_disk_usage_per_partition() -> List[DiskPartitionUsage]:
    partitions = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        # A mount can deny this user access, or be unmounted after disk_partitions() listed it.
        except (PermissionError, FileNotFoundError):
            partitions.append(
                {
                    'mountpoint': part.mountpoint,
                    'total_bytes': 0,
                    'used_bytes': 0,
                    'free_bytes': 0,
                    'percent': 0.0,
                    'accessible': False,
                }
            )
            continue
        partitions.append(
            {
                'mountpoint': part.mountpoint,
                'total_bytes': usage.total,
                'used_bytes': usage.used,
                'free_bytes': usage.free,
                'percent': usage.percent,
                'accessible': True,
            }
        )
    return partitions


def get_disk_io_total() -> DiskIOCounters:
    io = psutil.disk_io_counters(perdisk=False)
    return {
        'io_read_count': io.read_count,
        'io_write_count': io.write_count,
        'io_read_bytes': io.read_bytes,
        'io_write_bytes': io.write_bytes,
        'io_read_time_ms': io.read_time,
        'io_write_time_ms': io.write_time,
        'io_busy_time_ms': io.busy_time,
    }
