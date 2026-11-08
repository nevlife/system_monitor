#!/usr/bin/env python3
import math
import os
import time

from geometry_msgs.msg import TwistWithCovarianceStamped
from nav_msgs.msg import Path
import rclpy
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy
from rclpy.qos import HistoryPolicy
from rclpy.qos import QoSProfile
from rclpy.qos import ReliabilityPolicy
from rtcm_msgs.msg import Message as Rtcm
from sensor_msgs.msg import NavSatFix
from system_monitor.core import cpu
from system_monitor.core import disk
from system_monitor.core import link
from system_monitor.core import memory
from system_monitor.core import modem
from system_monitor.core import rtk
from system_monitor.core.gpu import GpuSampler
from system_monitor.core.map_frame import UtmMapFrame
from system_monitor.core.network import NetworkSampler
from system_monitor.core.radio_map import predict
from system_monitor.core.radio_map import RadioMap
from system_monitor.core.radio_map import route_offsets
from system_monitor.core.radio_map import velocity_offsets
from system_monitor_msgs.msg import CpuMetrics
from system_monitor_msgs.msg import DiskMetrics
from system_monitor_msgs.msg import DiskPartitionUsage
from system_monitor_msgs.msg import GpuInfo
from system_monitor_msgs.msg import GpuMetrics
from system_monitor_msgs.msg import LinkQuality
from system_monitor_msgs.msg import MemoryMetrics
from system_monitor_msgs.msg import NetworkInterface
from system_monitor_msgs.msg import NetworkMetrics


class SystemMonitorNode(Node):
    def __init__(self):
        super().__init__('system_monitor')

        rate = self.declare_parameter('publish_rate', Parameter.Type.DOUBLE).value
        self.enabled_cpu = self.declare_parameter('enabled_cpu', Parameter.Type.BOOL).value
        self.enabled_memory = self.declare_parameter('enabled_memory', Parameter.Type.BOOL).value
        self.enabled_disk = self.declare_parameter('enabled_disk', Parameter.Type.BOOL).value
        self.enabled_network = self.declare_parameter('enabled_network', Parameter.Type.BOOL).value
        self.enabled_gpu = self.declare_parameter('enabled_gpu', Parameter.Type.BOOL).value
        self.enabled_link = self.declare_parameter('enabled_link', Parameter.Type.BOOL).value

        if rate <= 0.0:
            raise ValueError(f'publish_rate must be > 0, got {rate}')

        qos = QoSProfile(
            depth=1,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
        )

        if self.enabled_cpu:
            self.cpu_pub = self.create_publisher(CpuMetrics, '~/output/cpu', qos)
            cpu.warmup()
        if self.enabled_memory:
            self.mem_pub = self.create_publisher(MemoryMetrics, '~/output/memory', qos)
        if self.enabled_disk:
            self.disk_pub = self.create_publisher(DiskMetrics, '~/output/disk', qos)

        self.network_sampler = NetworkSampler() if self.enabled_network else None
        if self.enabled_network:
            self.net_pub = self.create_publisher(NetworkMetrics, '~/output/network', qos)

        self.gpu_sampler = GpuSampler() if self.enabled_gpu else None
        if self.enabled_gpu:
            self.gpu_pub = self.create_publisher(GpuMetrics, '~/output/gpu', qos)

        self.prober = None
        if self.enabled_link:
            host = self.declare_parameter('link_host', Parameter.Type.STRING).value
            port = self.declare_parameter('link_port', Parameter.Type.INTEGER).value
            probe_rate = self.declare_parameter('link_probe_rate', Parameter.Type.DOUBLE).value
            window = self.declare_parameter('link_window_s', Parameter.Type.DOUBLE).value
            self.link_target = f'{host}:{port}'
            self.prober = link.LinkProber(host, port, probe_rate, window)
            self.link_pub = self.create_publisher(LinkQuality, '~/output/link', qos)
            self.fix = None
            self.last_cell = ''
            self.create_subscription(NavSatFix, '~/input/fix', self.on_fix, qos)
            self.velocity = (0.0, 0.0)
            self.create_subscription(
                TwistWithCovarianceStamped, '~/input/fix_velocity', self.on_velocity, qos)
            self.map_path = self.declare_parameter('link_map_path', Parameter.Type.STRING).value
            cell_m = self.declare_parameter('link_map_cell_m', Parameter.Type.DOUBLE).value
            max_age = self.declare_parameter('link_map_max_age_s', Parameter.Type.DOUBLE).value
            self.horizon = self.declare_parameter('link_horizon_s', Parameter.Type.DOUBLE).value
            self.radio_map = None
            self.map_updates = 0
            if self.map_path:
                self.radio_map = (RadioMap.load(self.map_path, max_age)
                                  if os.path.exists(self.map_path) else RadioMap(cell_m, max_age))
            # The route's frame is UTM minus this datum (navsat_transform's), so the GPS fix
            # places the vehicle on it without localization.
            datum = self.declare_parameter(
                'link_route_datum', Parameter.Type.DOUBLE_ARRAY).value
            self.map_frame = UtmMapFrame(datum[0], datum[1]) if len(datum) >= 2 else None
            self.route = []
            latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE,
                                 durability=DurabilityPolicy.TRANSIENT_LOCAL)
            self.create_subscription(Path, '~/input/route', self.on_route, latched)
            self.rtcm = rtk.RtcmTracker(window)
            self.create_subscription(Rtcm, '~/input/rtcm', self.on_rtcm, 10)

        period = 1.0 / rate
        self.timer = self.create_timer(period, self.publish)

        self.get_logger().info(
            f'System monitor started rate={rate}Hz '
            f'cpu={self.enabled_cpu} mem={self.enabled_memory} '
            f'disk={self.enabled_disk} net={self.enabled_network} gpu={self.enabled_gpu} '
            f'link={self.enabled_link}'
        )

    def destroy_node(self):
        if self.gpu_sampler is not None:
            self.gpu_sampler.close()
        if self.prober is not None:
            self.prober.close()
            if self.radio_map is not None:
                self.radio_map.save(self.map_path)
        super().destroy_node()

    def publish(self):
        stamp = self.get_clock().now().to_msg()
        if self.enabled_cpu:
            self.publish_cpu(stamp)
        if self.enabled_memory:
            self.publish_memory(stamp)
        if self.enabled_disk:
            self.publish_disk(stamp)
        if self.enabled_network:
            self.publish_network(stamp)
        if self.enabled_gpu:
            self.publish_gpu(stamp)
        if self.enabled_link:
            self.publish_link(stamp)

    def on_fix(self, msg):
        self.fix = msg

    def on_velocity(self, msg):
        v = msg.twist.twist.linear
        self.velocity = (v.x, v.y)

    def on_route(self, msg):
        self.route = [(p.pose.position.x, p.pose.position.y) for p in msg.poses]

    def on_rtcm(self, _msg):
        self.rtcm.add(time.monotonic())

    def publish_link(self, stamp):
        data = self.prober.sample()
        cell = modem.read()
        cell_changed = bool(self.last_cell) and cell['cell_id'] != self.last_cell
        self.last_cell = cell['cell_id']

        msg = LinkQuality()
        msg.stamp = stamp
        msg.target = self.link_target
        msg.probes_sent = data['probes_sent']
        msg.probes_lost = data['probes_lost']
        for key in ('loss_percent', 'rtt_p50_ms', 'rtt_p95_ms', 'rtt_max_ms', 'rtt_min_ever_ms',
                    'jitter_ms', 'longest_outage_ms', 'uplink_queue_p95_ms',
                    'downlink_queue_p95_ms'):
            setattr(msg, key, float(data[key]))
        for key in ('access_technology', 'operator_name', 'cell_id', 'rsrp_dbm', 'rsrq_db',
                    'sinr_db'):
            setattr(msg, key, cell[key])
        corrections = self.rtcm.sample(time.monotonic())
        msg.rtcm_age_s = corrections['rtcm_age_s']
        msg.rtcm_max_gap_s = corrections['rtcm_max_gap_s']
        msg.rtk = rtk.rtk_cause(self.fix.status.status if self.fix else None,
                                corrections['rtcm_age_s'])
        msg.latitude = self.fix.latitude if self.fix else math.nan
        msg.longitude = self.fix.longitude if self.fix else math.nan
        msg.diagnosis = link.diagnose(data, cell, cell_changed)
        self.update_map(msg, data)
        self.link_pub.publish(msg)

    def update_map(self, msg, data):
        msg.predicted_degraded_in_s = math.nan
        msg.predicted_rtt_p95_ms = math.nan
        msg.predicted_loss_percent = math.nan
        msg.predicted_outage_ms = math.nan
        if self.radio_map is None or math.isnan(msg.latitude):
            return
        now = self.get_clock().now().nanoseconds / 1e9
        east, north = self.velocity
        offsets = None
        if self.map_frame and self.route:
            here = self.map_frame.to_map(msg.latitude, msg.longitude)
            offsets = route_offsets(self.route, here, math.hypot(east, north), self.horizon, 1.0)
        msg.prediction_source = 'route' if offsets else 'velocity'
        if offsets is None:
            offsets = velocity_offsets(east, north, self.horizon, 1.0)
        pr = predict(self.radio_map, now, msg.latitude, msg.longitude, offsets,
                     lambda s: link.is_degraded(s, data['rtt_min_ever_ms']))
        msg.predicted_degraded_in_s = pr['degraded_in_s']
        msg.predicted_rtt_p95_ms = pr['worst_rtt_p95_ms']
        msg.predicted_loss_percent = pr['worst_loss_percent']
        msg.predicted_outage_ms = pr['worst_longest_outage_ms']
        msg.map_samples_ahead = pr['samples_ahead']
        if data['probes_sent']:
            self.radio_map.add(now, msg.latitude, msg.longitude, math.hypot(east, north), data)
        self.map_updates += 1
        if self.map_updates % 60 == 0:
            self.radio_map.save(self.map_path)

    def publish_cpu(self, stamp):
        data = cpu.get_cpu_dynamic_metrics()
        msg = CpuMetrics()
        msg.stamp = stamp
        msg.usage_percent = float(data['usage_percent'])
        msg.freq_current_mhz = float(data['freq_current_mhz'])
        msg.temperature_celsius = float(data['temperature_celsius'])
        msg.load_avg_1m = float(data['load_avg_1m'])
        msg.load_avg_5m = float(data['load_avg_5m'])
        msg.load_avg_15m = float(data['load_avg_15m'])
        msg.iowait_seconds = float(data['iowait_seconds'])
        msg.user_seconds = float(data['user_seconds'])
        msg.system_seconds = float(data['system_seconds'])
        msg.idle_seconds = float(data['idle_seconds'])
        msg.ctx_switches = int(data['ctx_switches'])
        msg.interrupts = int(data['interrupts'])
        msg.soft_interrupts = int(data['soft_interrupts'])
        self.cpu_pub.publish(msg)

    def publish_memory(self, stamp):
        data = memory.get_memory_dynamic_metrics()
        msg = MemoryMetrics()
        msg.stamp = stamp
        msg.total_bytes = int(data['total'])
        msg.available_bytes = int(data['available'])
        msg.used_bytes = int(data['used'])
        msg.free_bytes = int(data['free'])
        msg.percent = float(data['percent'])
        msg.active_bytes = int(data['active'])
        msg.inactive_bytes = int(data['inactive'])
        msg.buffers_bytes = int(data['buffers'])
        msg.cached_bytes = int(data['cached'])
        msg.shared_bytes = int(data['shared'])
        msg.slab_bytes = int(data['slab'])
        msg.swap_total_bytes = int(data['swap_total'])
        msg.swap_used_bytes = int(data['swap_used'])
        msg.swap_free_bytes = int(data['swap_free'])
        msg.swap_percent = float(data['swap_percent'])
        self.mem_pub.publish(msg)

    def publish_disk(self, stamp):
        partitions = disk.get_disk_usage_per_partition()
        io = disk.get_disk_io_total()

        msg = DiskMetrics()
        msg.stamp = stamp

        for p in partitions:
            part_msg = DiskPartitionUsage()
            part_msg.mountpoint = p['mountpoint']
            part_msg.total_bytes = int(p['total_bytes'])
            part_msg.used_bytes = int(p['used_bytes'])
            part_msg.free_bytes = int(p['free_bytes'])
            part_msg.percent = float(p['percent'])
            part_msg.accessible = bool(p['accessible'])
            msg.partitions.append(part_msg)

        msg.io_read_count = int(io['io_read_count'])
        msg.io_write_count = int(io['io_write_count'])
        msg.io_read_bytes = int(io['io_read_bytes'])
        msg.io_write_bytes = int(io['io_write_bytes'])
        msg.io_read_time_ms = int(io['io_read_time_ms'])
        msg.io_write_time_ms = int(io['io_write_time_ms'])
        msg.io_busy_time_ms = int(io['io_busy_time_ms'])
        self.disk_pub.publish(msg)

    def publish_network(self, stamp):
        data = self.network_sampler.sample()
        summary = data['summary']
        interfaces = data['interfaces']

        msg = NetworkMetrics()
        msg.stamp = stamp
        msg.total_interfaces = int(summary['total_interfaces'])
        msg.active_interfaces = int(summary['active_interfaces'])
        msg.down_interfaces = int(summary['down_interfaces'])

        for name, iface in interfaces.items():
            iface_msg = NetworkInterface()
            iface_msg.name = name
            iface_msg.is_up = bool(iface['is_up'])
            iface_msg.mtu = int(iface['mtu'])
            iface_msg.speed_mbps = int(iface['speed_mbps'])
            iface_msg.input_bytes_per_sec = float(iface['input_bytes_per_sec'])
            iface_msg.output_bytes_per_sec = float(iface['output_bytes_per_sec'])
            iface_msg.rx_bytes = int(iface['rx_bytes'])
            iface_msg.tx_bytes = int(iface['tx_bytes'])
            iface_msg.rx_packets = int(iface['rx_packets'])
            iface_msg.tx_packets = int(iface['tx_packets'])
            iface_msg.rx_errors = int(iface['rx_errors'])
            iface_msg.tx_errors = int(iface['tx_errors'])
            iface_msg.rx_dropped = int(iface['rx_dropped'])
            iface_msg.tx_dropped = int(iface['tx_dropped'])
            msg.interfaces.append(iface_msg)

        self.net_pub.publish(msg)

    def publish_gpu(self, stamp):
        data = self.gpu_sampler.sample()
        msg = GpuMetrics()
        msg.stamp = stamp

        for g in data['gpus']:
            gpu_msg = GpuInfo()
            gpu_msg.index = int(g['index'])
            gpu_msg.utilization_percent = float(g['utilization_percent'])
            gpu_msg.memory_used_mb = float(g['memory_used_mb'])
            gpu_msg.memory_total_mb = float(g['memory_total_mb'])
            gpu_msg.temperature_celsius = float(g['temperature_celsius'])
            gpu_msg.power_watts = float(g['power_watts'])
            msg.gpus.append(gpu_msg)

        self.gpu_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = SystemMonitorNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
