
'''
Cross-platform network metrics collection using psutil.
Provides raw, non-converted values.
'''
import psutil
import time
from typing import Dict, Any

_previous_io_counters = psutil.net_io_counters(pernic=True)
_previous_time = time.time()

def get_network_info() -> Dict[str, Any]:
    """
    Gathers raw network information using psutil.
    Exception handling and type conversions are intentionally omitted as per request.
    """
    global _previous_io_counters, _previous_time

    current_io_counters = psutil.net_io_counters(pernic=True)
    current_time = time.time()

    time_delta = max(current_time - _previous_time, 1e-6)

    if_stats = psutil.net_if_stats()

    interfaces_data = {}
    summary_counts = {
        'total': 0,
        'active': 0,
        'down': 0,
    }

    for name, stats in if_stats.items():
        if name not in current_io_counters:
            continue

        summary_counts['total'] += 1
        is_up = stats.isup
        if is_up:
            summary_counts['active'] += 1
        else:
            summary_counts['down'] += 1

        current_io = current_io_counters[name]
        prev_io = _previous_io_counters.get(name, current_io)

        input_bytes_per_sec = (current_io.bytes_recv - prev_io.bytes_recv) / time_delta
        output_bytes_per_sec = (current_io.bytes_sent - prev_io.bytes_sent) / time_delta

        interfaces_data[name] = {
            'is_up': is_up,
            'mtu': stats.mtu,
            'speed_mbps': stats.speed,
            'input_bytes_per_sec': input_bytes_per_sec,
            'output_bytes_per_sec': output_bytes_per_sec,
            'rx_bytes': current_io.bytes_recv,
            'tx_bytes': current_io.bytes_sent,
            'rx_packets': current_io.packets_recv,
            'tx_packets': current_io.packets_sent,
            'rx_errors': current_io.errin,
            'tx_errors': current_io.errout,
            'rx_dropped': current_io.dropin,
            'tx_dropped': current_io.dropout,
        }

    summary = {
        'total_interfaces': summary_counts['total'],
        'active_interfaces': summary_counts['active'],
        'down_interfaces': summary_counts['down'],
    }

    _previous_io_counters = current_io_counters
    _previous_time = current_time

    return {
        'summary': summary,
        'interfaces': interfaces_data,
    }

if __name__ == '__main__':
    import json

    print("--- Gathering network info (first call establishes baseline) ---")
    get_network_info()

    print("Waiting 2 seconds to measure traffic...")
    time.sleep(2)

    print("\n--- Gathering network info (second call) ---")
    network_info = get_network_info()
    print(json.dumps(network_info, indent=2))
