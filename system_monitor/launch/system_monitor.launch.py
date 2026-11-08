import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_system_monitor = get_package_share_directory('system_monitor')
    params_file = os.path.join(pkg_system_monitor, 'config', 'system_monitor.param.yaml')

    system_monitor_node = Node(
        package='system_monitor',
        executable='system_monitor_node',
        name='system_monitor',
        output='screen',
        parameters=[params_file],
        remappings=[(f'~/output/{t}', t) for t in ('cpu', 'memory', 'disk', 'network', 'gpu', 'link')]
        + [('~/input/fix', '/ublox_gps_node/fix'),
           ('~/input/fix_velocity', '/ublox_gps_node/fix_velocity'),
           ('~/input/route', '/route'),
           ('~/input/rtcm', '/rtcm')],
    )

    return LaunchDescription(
        [
            system_monitor_node,
        ]
    )
