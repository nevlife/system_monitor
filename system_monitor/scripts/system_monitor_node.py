#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rclpy
from rclpy.node import Node
from builtin_interfaces.msg import Time

from system_monitor_msgs.msg import (
    CpuMetrics,
    MemoryMetrics,
    DiskMetrics,
    DiskPartitionUsage,
    NetworkMetrics,
    NetworkInterface,
    GpuMetrics,
    GpuInfo,
)

from system_monitor_core import cpu, memory, disk, network, gpu


def make_stamp(node: Node) -> Time:
    t = node.get_clock().now().to_msg()
    return t


class SystemMonitorNode(Node):
    def __init__(self):
        super().__init__('system_monitor')

        self.declare_parameter('publish_rate', 1.0)
        self.declare_parameter('enabled_cpu', True)
        self.declare_parameter('enabled_memory', True)
        self.declare_parameter('enabled_disk', True)
        self.declare_parameter('enabled_network', True)
        self.declare_parameter('enabled_gpu', False)

        rate = self.get_parameter('publish_rate').get_parameter_value().double_value
        self.enabled_cpu = self.get_parameter('enabled_cpu').get_parameter_value().bool_value
        self.enabled_memory = self.get_parameter('enabled_memory').get_parameter_value().bool_value
        self.enabled_disk = self.get_parameter('enabled_disk').get_parameter_value().bool_value
        self.enabled_network = self.get_parameter('enabled_network').get_parameter_value().bool_value
        self.enabled_gpu = self.get_parameter('enabled_gpu').get_parameter_value().bool_value

        qos = rclpy.qos.QoSProfile(depth=10)

        if self.enabled_cpu:
            self.cpu_pub = self.create_publisher(CpuMetrics, '/system_monitor/cpu', qos)
        if self.enabled_memory:
            self.mem_pub = self.create_publisher(MemoryMetrics, '/system_monitor/memory', qos)
        if self.enabled_disk:
            self.disk_pub = self.create_publisher(DiskMetrics, '/system_monitor/disk', qos)
        if self.enabled_network:
            self.net_pub = self.create_publisher(NetworkMetrics, '/system_monitor/network', qos)
        if self.enabled_gpu:
            self.gpu_pub = self.create_publisher(GpuMetrics, '/system_monitor/gpu', qos)

        if self.enabled_network:
            network.get_network_info()

        period = 1.0 / rate if rate > 0.0 else 1.0
        self.timer = self.create_timer(period, self.publish)

        self.get_logger().info(
            f'System monitor started rate={rate}Hz '
            f'cpu={self.enabled_cpu} mem={self.enabled_memory} '
            f'disk={self.enabled_disk} net={self.enabled_network} gpu={self.enabled_gpu}'
        )

    def publish(self):
        if self.enabled_cpu:
            self.publish_cpu()
        if self.enabled_memory:
            self.publish_memory()
        if self.enabled_disk:
            self.publish_disk()
        if self.enabled_network:
            self.publish_network()
        if self.enabled_gpu:
            self.publish_gpu()

    def publish_cpu(self):
        data = cpu.get_cpu_dynamic_metrics()
        msg = CpuMetrics()
        msg.stamp = make_stamp(self)
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

    def publish_memory(self):
        data = memory.get_memory_dynamic_metrics()
        msg = MemoryMetrics()
        msg.stamp = make_stamp(self)
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

    def publish_disk(self):
        partitions = disk.get_disk_usage_per_partition()
        io = disk.get_disk_io_total()

        msg = DiskMetrics()
        msg.stamp = make_stamp(self)

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

    def publish_network(self):
        data = network.get_network_info()
        summary = data['summary']
        interfaces = data['interfaces']

        msg = NetworkMetrics()
        msg.stamp = make_stamp(self)
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

    def publish_gpu(self):
        data = gpu.get_gpu_dynamic_metrics()
        msg = GpuMetrics()
        msg.stamp = make_stamp(self)

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
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
