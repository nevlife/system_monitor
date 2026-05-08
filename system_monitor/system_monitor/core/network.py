"""
Cross-platform network metrics collection using psutil.

Per-second throughput is computed from the delta between successive samples,
so consumers must hold a NetworkSampler instance across calls.
"""

import psutil
import time
from typing import Dict, Any


class NetworkSampler:
    def __init__(self) -> None:
        self._prev_io = psutil.net_io_counters(pernic=True)
        self._prev_time = time.monotonic()

    def sample(self) -> Dict[str, Any]:
        current_io = psutil.net_io_counters(pernic=True)
        current_time = time.monotonic()
        time_delta = max(current_time - self._prev_time, 1e-6)

        if_stats = psutil.net_if_stats()

        interfaces_data: Dict[str, Any] = {}
        total = 0
        active = 0
        down = 0

        for name, stats in if_stats.items():
            if name not in current_io:
                continue

            total += 1
            if stats.isup:
                active += 1
            else:
                down += 1

            cur = current_io[name]
            prev = self._prev_io.get(name, cur)

            interfaces_data[name] = {
                'is_up': stats.isup,
                'mtu': stats.mtu,
                'speed_mbps': stats.speed,
                'input_bytes_per_sec': (cur.bytes_recv - prev.bytes_recv) / time_delta,
                'output_bytes_per_sec': (cur.bytes_sent - prev.bytes_sent) / time_delta,
                'rx_bytes': cur.bytes_recv,
                'tx_bytes': cur.bytes_sent,
                'rx_packets': cur.packets_recv,
                'tx_packets': cur.packets_sent,
                'rx_errors': cur.errin,
                'tx_errors': cur.errout,
                'rx_dropped': cur.dropin,
                'tx_dropped': cur.dropout,
            }

        self._prev_io = current_io
        self._prev_time = current_time

        return {
            'summary': {
                'total_interfaces': total,
                'active_interfaces': active,
                'down_interfaces': down,
            },
            'interfaces': interfaces_data,
        }


if __name__ == '__main__':
    import json

    print("--- Creating sampler (establishes baseline) ---")
    sampler = NetworkSampler()

    print("Waiting 2 seconds to measure traffic...")
    time.sleep(2)

    print("\n--- Sampling network info ---")
    network_info = sampler.sample()
    print(json.dumps(network_info, indent=2))
