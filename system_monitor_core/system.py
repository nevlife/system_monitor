"""
System metadata collection.

Units:
- boot_time: Unix timestamp (seconds since epoch)
- uptime: seconds
- user started: Unix timestamp
"""

import socket
import platform
import psutil
from datetime import datetime
from typing import TypedDict, List
import time

OS_TYPE = platform.system()


class OSInfo(TypedDict):
    system: str
    release: str
    version: str
    machine: str
    processor: str
    platform: str


class UserInfo(TypedDict):
    name: str
    terminal: str
    host: str
    started: float


class SystemStatic(TypedDict):
    hostname: str
    os: OSInfo
    python_version: str
    boot_time: float
    boot_time_iso: str


class SystemDynamic(TypedDict):
    timestamp: str
    uptime: float
    users: List[UserInfo]


def get_system_static_metadata() -> SystemStatic:
    boot_time = psutil.boot_time()

    return {
        'hostname': socket.gethostname(),
        'os': {
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'platform': platform.platform()
        },
        'python_version': platform.python_version(),
        'boot_time': boot_time,
        'boot_time_iso': datetime.fromtimestamp(boot_time).isoformat()
    }


def get_system_dynamic_metrics() -> SystemDynamic:
    users = []
    for user in psutil.users():
        users.append({
            'name': user.name,
            'terminal': user.terminal,
            'host': user.host,
            'started': user.started
        })

    return {
        'timestamp': datetime.now().isoformat(),
        'uptime': time.time() - psutil.boot_time(),
        'users': users
    }


if __name__ == "__main__":
    start_time = time.perf_counter()

    print("=== System Static Metadata ===")
    static = get_system_static_metadata()
    for key, value in static.items():
        print(f"{key}: {value}")

    print("\n=== System Dynamic Metrics ===")
    dynamic = get_system_dynamic_metrics()
    for key, value in dynamic.items():
        print(f"{key}: {value}")

    elapsed = time.perf_counter() - start_time
    print(f"\nTime taken: {elapsed:.4f} seconds")