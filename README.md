# system_monitor

A ROS2 package that collects local system metrics (CPU, memory, disk, network, GPU) and publishes them as ROS2 topics.

## Package Structure

```
system_monitor/
├── system_monitor_core/          # Python collection modules (no ROS2 dependency)
│   ├── cpu.py
│   ├── memory.py
│   ├── disk.py
│   ├── network.py
│   ├── gpu.py
│   └── system.py
├── system_monitor/               # ROS2 package
│   ├── scripts/
│   │   └── system_monitor_node.py
│   ├── config/
│   │   └── params.yaml
│   └── launch/
│       └── system_monitor.launch.py
└── system_monitor_msgs/          # Custom message definitions
    └── msg/
        ├── CpuMetrics.msg
        ├── MemoryMetrics.msg
        ├── DiskMetrics.msg
        ├── DiskPartitionUsage.msg
        ├── NetworkMetrics.msg
        ├── NetworkInterface.msg
        ├── GpuMetrics.msg
        └── GpuInfo.msg
```

## Dependencies

```bash
pip install psutil nvidia-ml-py
```

- `psutil`: CPU, memory, disk, network collection
- `nvidia-ml-py` (`pynvml`): GPU collection (optional — safe to omit if no NVIDIA GPU)

## Build & Run

```bash
cd ~/dev/ros2_ws
colcon build --packages-select system_monitor_msgs system_monitor
source install/setup.bash

ros2 launch system_monitor system_monitor.launch.py
```

## Parameters (params.yaml)

| Parameter | Default | Description |
|---|---|---|
| `publish_rate` | `1.0` | Publish rate (Hz) |
| `enabled_cpu` | `true` | Enable CPU metrics |
| `enabled_memory` | `true` | Enable memory metrics |
| `enabled_disk` | `true` | Enable disk metrics |
| `enabled_network` | `true` | Enable network metrics |
| `enabled_gpu` | `true` | Enable GPU metrics |

## Published Topics

| Topic | Message Type | Description |
|---|---|---|
| `/system_monitor/cpu` | `system_monitor_msgs/CpuMetrics` | CPU metrics |
| `/system_monitor/memory` | `system_monitor_msgs/MemoryMetrics` | Memory metrics |
| `/system_monitor/disk` | `system_monitor_msgs/DiskMetrics` | Disk I/O and partitions |
| `/system_monitor/network` | `system_monitor_msgs/NetworkMetrics` | Network interfaces |
| `/system_monitor/gpu` | `system_monitor_msgs/GpuMetrics` | GPU metrics |

## Message Definitions

### CpuMetrics
| Field | Type | Description |
|---|---|---|
| `stamp` | `builtin_interfaces/Time` | Timestamp |
| `usage_percent` | `float32` | Overall CPU usage (%) |
| `freq_current_mhz` | `float32` | Current frequency (MHz) |
| `temperature_celsius` | `float32` | Temperature (°C), -1.0 if unavailable |
| `load_avg_1m/5m/15m` | `float32` | Load average, -1.0 on Windows |
| `iowait_seconds` | `float64` | I/O wait time (s), -1.0 if unavailable |
| `user/system/idle_seconds` | `float64` | Cumulative CPU time (s) |
| `ctx_switches` | `int64` | Context switch count |
| `interrupts` | `int64` | Interrupt count |
| `soft_interrupts` | `int64` | Soft interrupt count |

### MemoryMetrics
| Field | Type | Description |
|---|---|---|
| `stamp` | `builtin_interfaces/Time` | Timestamp |
| `total/available/used/free_bytes` | `int64` | Memory size (bytes) |
| `percent` | `float32` | Usage (%) |
| `active/inactive/buffers/cached/shared/slab_bytes` | `int64` | Detailed memory, -1 if unavailable |
| `swap_total/used/free_bytes` | `int64` | Swap size (bytes) |
| `swap_percent` | `float32` | Swap usage (%) |

### DiskMetrics
| Field | Type | Description |
|---|---|---|
| `stamp` | `builtin_interfaces/Time` | Timestamp |
| `partitions` | `DiskPartitionUsage[]` | Per-partition usage |
| `io_read/write_count` | `int64` | Cumulative read/write count |
| `io_read/write_bytes` | `int64` | Cumulative read/write size (bytes) |
| `io_read/write_time_ms` | `int64` | Cumulative read/write time (ms) |
| `io_busy_time_ms` | `int64` | Disk busy time (ms), Linux only |

### DiskPartitionUsage
| Field | Type | Description |
|---|---|---|
| `mountpoint` | `string` | Mount path |
| `total/used/free_bytes` | `int64` | Size (bytes) |
| `percent` | `float32` | Usage (%) |
| `accessible` | `bool` | Whether the partition is accessible |

### NetworkMetrics
| Field | Type | Description |
|---|---|---|
| `stamp` | `builtin_interfaces/Time` | Timestamp |
| `total_interfaces` | `int32` | Total interface count |
| `active_interfaces` | `int32` | Active (UP) interface count |
| `down_interfaces` | `int32` | Inactive interface count |
| `interfaces` | `NetworkInterface[]` | Per-interface details |

### NetworkInterface
| Field | Type | Description |
|---|---|---|
| `name` | `string` | Interface name |
| `is_up` | `bool` | Whether the interface is up |
| `mtu` | `int32` | MTU (bytes) |
| `speed_mbps` | `int32` | Link speed (Mbps) |
| `input/output_bytes_per_sec` | `float64` | Current RX/TX rate (bytes/s) |
| `rx/tx_bytes` | `int64` | Cumulative RX/TX (bytes) |
| `rx/tx_packets` | `int64` | Cumulative packet count |
| `rx/tx_errors` | `int64` | Cumulative error count |
| `rx/tx_dropped` | `int64` | Cumulative drop count |

### GpuMetrics
| Field | Type | Description |
|---|---|---|
| `stamp` | `builtin_interfaces/Time` | Timestamp |
| `gpus` | `GpuInfo[]` | Per-GPU info |

### GpuInfo
| Field | Type | Description |
|---|---|---|
| `index` | `int32` | GPU index |
| `utilization_percent` | `float32` | Utilization (%), -1.0 if unavailable |
| `memory_used_mb` | `float32` | Used VRAM (MB) |
| `memory_total_mb` | `float32` | Total VRAM (MB) |
| `temperature_celsius` | `float32` | Temperature (°C) |
| `power_watts` | `float32` | Power draw (W) |
