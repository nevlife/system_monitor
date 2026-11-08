# system_monitor

A ROS2 package that collects local system metrics (CPU, memory, disk, network, GPU) and publishes them as ROS2 topics.

## Package Structure

```
system_monitor/
├── system_monitor/               # ROS2 package (ament_python)
│   ├── system_monitor/
│   │   ├── core/                 # Collection modules (no ROS2 dependency)
│   │   │   ├── cpu.py
│   │   │   ├── memory.py
│   │   │   ├── disk.py
│   │   │   ├── network.py
│   │   │   ├── gpu.py
│   │   │   ├── link.py
│   │   │   └── modem.py
│   │   ├── link_echo.py
│   │   └── system_monitor_node.py
│   ├── config/
│   │   └── system_monitor.param.yaml
│   ├── launch/
│   │   └── system_monitor.launch.py
│   └── test/
└── system_monitor_msgs/          # Custom message definitions
    └── msg/
        ├── CpuMetrics.msg
        ├── MemoryMetrics.msg
        ├── DiskMetrics.msg
        ├── DiskPartitionUsage.msg
        ├── NetworkMetrics.msg
        ├── NetworkInterface.msg
        ├── GpuMetrics.msg
        ├── GpuInfo.msg
        └── LinkQuality.msg
```

## Dependencies

```bash
rosdep install --from-paths system_monitor --ignore-src -y
```

- `python3-psutil`: CPU, memory, disk, network collection
- `python3-pynvml`: GPU collection. The node imports it at start-up, so it must be installed even when `enabled_gpu` is false.
- Linux only.

## Build & Run

```bash
cd ~/dev/ros2_ws
colcon build --symlink-install --packages-select system_monitor_msgs system_monitor
source install/setup.bash

ros2 launch system_monitor system_monitor.launch.py
```

## Parameters (system_monitor.param.yaml)

| Parameter            | Default     | Description                                                                                                                       |
| -------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `publish_rate`       | `1.0`       | Publish rate (Hz)                                                                                                                 |
| `enabled_cpu`        | `true`      | Enable CPU metrics                                                                                                                |
| `enabled_memory`     | `true`      | Enable memory metrics                                                                                                             |
| `enabled_disk`       | `true`      | Enable disk metrics                                                                                                               |
| `enabled_network`    | `true`      | Enable network metrics                                                                                                            |
| `enabled_gpu`        | `false`     | Enable GPU metrics                                                                                                                |
| `enabled_link`       | `false`     | Enable link quality towards a remote echo server                                                                                  |
| `link_host`          | `127.0.0.1` | Echo server address                                                                                                               |
| `link_port`          | `13440`     | Echo server UDP port                                                                                                              |
| `link_probe_rate`    | `20.0`      | Probes per second                                                                                                                 |
| `link_window_s`      | `5.0`       | Window the statistics cover (s)                                                                                                   |
| `link_map_path`      | `''`        | Radio map file, loaded at start and saved every minute and at exit; empty disables the map                                        |
| `link_map_cell_m`    | `5.0`       | Grid cell size of a new map (m)                                                                                                   |
| `link_map_max_age_s` | `2592000.0` | Samples older than this are ignored (s)                                                                                           |
| `link_horizon_s`     | `15.0`      | How far ahead the prediction looks (s)                                                                                            |
| `link_route_datum`   | `[]`        | Datum `[lat, lon]` of the route's map frame (UTM minus datum, as navsat_transform defines it); empty predicts straight ahead only |

## Published Topics

| Topic                     | Message Type                         | Description                       |
| ------------------------- | ------------------------------------ | --------------------------------- |
| `/system_monitor/cpu`     | `system_monitor_msgs/CpuMetrics`     | CPU metrics                       |
| `/system_monitor/memory`  | `system_monitor_msgs/MemoryMetrics`  | Memory metrics                    |
| `/system_monitor/disk`    | `system_monitor_msgs/DiskMetrics`    | Disk I/O and partitions           |
| `/system_monitor/network` | `system_monitor_msgs/NetworkMetrics` | Network interfaces                |
| `/system_monitor/gpu`     | `system_monitor_msgs/GpuMetrics`     | GPU metrics                       |
| `/system_monitor/link`    | `system_monitor_msgs/LinkQuality`    | Link quality and its likely cause |

## Message Definitions

### CpuMetrics

| Field                      | Type                      | Description                                       |
| -------------------------- | ------------------------- | ------------------------------------------------- |
| `stamp`                    | `builtin_interfaces/Time` | Timestamp                                         |
| `usage_percent`            | `float32`                 | Overall CPU usage (%)                             |
| `freq_current_mhz`         | `float32`                 | Current frequency (MHz)                           |
| `temperature_celsius`      | `float32`                 | Temperature in degrees Celsius, -1.0 if no sensor |
| `load_avg_1m/5m/15m`       | `float32`                 | Load average                                      |
| `iowait_seconds`           | `float64`                 | I/O wait time (s)                                 |
| `user/system/idle_seconds` | `float64`                 | Cumulative CPU time (s)                           |
| `ctx_switches`             | `int64`                   | Context switch count                              |
| `interrupts`               | `int64`                   | Interrupt count                                   |
| `soft_interrupts`          | `int64`                   | Soft interrupt count                              |

### MemoryMetrics

| Field                                              | Type                      | Description             |
| -------------------------------------------------- | ------------------------- | ----------------------- |
| `stamp`                                            | `builtin_interfaces/Time` | Timestamp               |
| `total/available/used/free_bytes`                  | `int64`                   | Memory size (bytes)     |
| `percent`                                          | `float32`                 | Usage (%)               |
| `active/inactive/buffers/cached/shared/slab_bytes` | `int64`                   | Detailed memory (bytes) |
| `swap_total/used/free_bytes`                       | `int64`                   | Swap size (bytes)       |
| `swap_percent`                                     | `float32`                 | Swap usage (%)          |

### DiskMetrics

| Field                   | Type                      | Description                        |
| ----------------------- | ------------------------- | ---------------------------------- |
| `stamp`                 | `builtin_interfaces/Time` | Timestamp                          |
| `partitions`            | `DiskPartitionUsage[]`    | Per-partition usage                |
| `io_read/write_count`   | `int64`                   | Cumulative read/write count        |
| `io_read/write_bytes`   | `int64`                   | Cumulative read/write size (bytes) |
| `io_read/write_time_ms` | `int64`                   | Cumulative read/write time (ms)    |
| `io_busy_time_ms`       | `int64`                   | Disk busy time (ms)                |

### DiskPartitionUsage

| Field                   | Type      | Description                         |
| ----------------------- | --------- | ----------------------------------- |
| `mountpoint`            | `string`  | Mount path                          |
| `total/used/free_bytes` | `int64`   | Size (bytes)                        |
| `percent`               | `float32` | Usage (%)                           |
| `accessible`            | `bool`    | Whether the partition is accessible |

### NetworkMetrics

| Field               | Type                      | Description                 |
| ------------------- | ------------------------- | --------------------------- |
| `stamp`             | `builtin_interfaces/Time` | Timestamp                   |
| `total_interfaces`  | `int32`                   | Total interface count       |
| `active_interfaces` | `int32`                   | Active (UP) interface count |
| `down_interfaces`   | `int32`                   | Inactive interface count    |
| `interfaces`        | `NetworkInterface[]`      | Per-interface details       |

### NetworkInterface

| Field                        | Type      | Description                  |
| ---------------------------- | --------- | ---------------------------- |
| `name`                       | `string`  | Interface name               |
| `is_up`                      | `bool`    | Whether the interface is up  |
| `mtu`                        | `int32`   | MTU (bytes)                  |
| `speed_mbps`                 | `int32`   | Link speed (Mbps)            |
| `input/output_bytes_per_sec` | `float64` | Current RX/TX rate (bytes/s) |
| `rx/tx_bytes`                | `int64`   | Cumulative RX/TX (bytes)     |
| `rx/tx_packets`              | `int64`   | Cumulative packet count      |
| `rx/tx_errors`               | `int64`   | Cumulative error count       |
| `rx/tx_dropped`              | `int64`   | Cumulative drop count        |

### GpuMetrics

| Field   | Type                      | Description  |
| ------- | ------------------------- | ------------ |
| `stamp` | `builtin_interfaces/Time` | Timestamp    |
| `gpus`  | `GpuInfo[]`               | Per-GPU info |

### GpuInfo

| Field                 | Type      | Description                          |
| --------------------- | --------- | ------------------------------------ |
| `index`               | `int32`   | GPU index                            |
| `utilization_percent` | `float32` | Utilization (%), -1.0 if unsupported |
| `memory_used_mb`      | `float32` | Used VRAM (MB)                       |
| `memory_total_mb`     | `float32` | Total VRAM (MB)                      |
| `temperature_celsius` | `float32` | Degrees Celsius, -1.0 if unsupported |
| `power_watts`         | `float32` | Power draw (W), -1.0 if unsupported  |

### LinkQuality

Probes are UDP datagrams sent on a fixed period (as irtt does) to `link_echo`, which returns each one to its sender and so also works when the vehicle is behind a cellular NAT. The echo appends its receive time, as STAMP (RFC 8762) reflectors do; the two clocks differ by an unknown but constant offset, so each direction's one-way delay above its own minimum is the queueing in that direction. Run it on the remote side with `ros2 run system_monitor link_echo --port 13440`, or copy `link_echo.py`, which needs only Python. Subscribes to `~/input/fix` (`sensor_msgs/NavSatFix`), `~/input/fix_velocity` (`geometry_msgs/TwistWithCovarianceStamped`, east and north in `linear.x/y`), `~/input/rtcm` (`rtcm_msgs/Message`) and `~/input/route` (`nav_msgs/Path`, transient local), of which the launch file connects the first three to the u-blox and NTRIP topics. `~/input/route` is left unconnected: any planner's path can be remapped to it, and without one the prediction looks straight ahead. None of them needs localization: the route is followed from the GPS fix through `link_route_datum`.

RTK corrections reach the vehicle over the same cellular link, about once a second, so they are a second link indicator that costs no probe traffic. When the fix is not RTK fixed, late corrections point at the link and fresh ones at the sky or the receiver. The u-blox driver reports RTK fixed as `STATUS_GBAS_FIX`.

| Field                                         | Type                      | Description                                                                                                                    |
| --------------------------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `stamp`                                       | `builtin_interfaces/Time` | Timestamp                                                                                                                      |
| `target`                                      | `string`                  | Echo server `host:port`                                                                                                        |
| `probes_sent/lost`                            | `uint32`                  | Probes in the window; lost means no reply within 1 s                                                                           |
| `loss_percent`                                | `float64`                 | Lost share of the probes old enough to judge (%)                                                                               |
| `rtt_p50/p95/max_ms`                          | `float64`                 | Round-trip time in the window (ms)                                                                                             |
| `rtt_min_ever_ms`                             | `float64`                 | Lowest round-trip time since start, the baseline for queueing (ms)                                                             |
| `jitter_ms`                                   | `float64`                 | Mean change between consecutive round-trip times (ms)                                                                          |
| `longest_outage_ms`                           | `float64`                 | Longest time without a reply in the window (ms)                                                                                |
| `uplink/downlink_queue_p95_ms`                | `float64`                 | One-way delay above its own minimum per direction (ms); the echo's clock offset cancels, so no clock synchronization is needed |
| `access_technology/operator_name/cell_id`     | `string`                  | From ModemManager, empty without a modem                                                                                       |
| `rsrp_dbm/rsrq_db/sinr_db`                    | `float64`                 | Serving cell signal (5G NR when reported, else LTE), NaN without a modem                                                       |
| `latitude/longitude`                          | `float64`                 | Last GPS fix, NaN before the first                                                                                             |
| `rtcm_age_s/rtcm_max_gap_s`                   | `float64`                 | Age of the newest RTK correction and the longest gap between corrections in the window (s), NaN without corrections            |
| `rtk`                                         | `string`                  | `FIXED`, `CORRECTIONS_LATE` (the link), `SKY_OR_RECEIVER`, `NO_CORRECTIONS`, or empty before the first fix                     |
| `predicted_degraded_in_s`                     | `float64`                 | Seconds until the first map cell ahead that was degraded, NaN if none                                                          |
| `predicted_rtt_p95_ms/loss_percent/outage_ms` | `float64`                 | Worst cell value ahead (90th percentile of its samples)                                                                        |
| `map_samples_ahead`                           | `uint32`                  | Map samples behind the prediction; 0 means the road ahead is unmapped                                                          |
| `prediction_source`                           | `string`                  | `route` (along `~/input/route`) or `velocity` (straight ahead)                                                                 |
| `diagnosis`                                   | `string`                  | `OK`, `NO_LINK`, `HANDOVER`, `WEAK_SIGNAL`, `INTERFERENCE`, `CONGESTION`, or `DEGRADED`                                        |

The link counts as degraded when loss is above 2%, the 95th percentile round trip is more than 100 ms above the baseline, or no reply came for more than 300 ms. The cause is then taken, in this order, from a cell id change, RSRP below -110 dBm, SINR below 0 dB, or else congestion when the signal is good. Without a modem the cause stays `DEGRADED`. A phone used as a USB tether reports no modem values. The ModemManager key names have not yet been checked against a real modem.

With `link_map_path` set, each sample is also stored in a radio environment map, a grid of cells that keep their newest 50 samples. Predictive QoS for tele-operated driving (5GAA) works the same way: it looks up what was measured at the places the vehicle is about to reach. The prediction follows the planned route when `link_route_datum` is set, a route has arrived and the vehicle is within 20 m of it; otherwise it looks straight ahead at the current velocity, which misses turns. A map only helps on roads driven before, and the thresholds above decide when a cell counts as degraded.
