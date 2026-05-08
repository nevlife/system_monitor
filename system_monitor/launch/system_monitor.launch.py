import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_system_monitor = get_package_share_directory('system_monitor')
    params_file = os.path.join(pkg_system_monitor, 'config', 'params.yaml')

    system_monitor_node = Node(
        package='system_monitor',
        executable='system_monitor_node',
        name='system_monitor',
        output='screen',
        parameters=[params_file],
    )

    return LaunchDescription([
        system_monitor_node,
    ])
