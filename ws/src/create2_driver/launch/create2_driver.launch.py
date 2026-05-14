"""Stand-alone launch for the Create 2 driver. Loads calibration YAML if given."""
from pathlib import Path

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    default_params = str(Path("/config/create2_calibration.yaml"))

    return LaunchDescription([
        DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
        DeclareLaunchArgument("params_file", default_value=default_params,
                              description="YAML with create2_driver parameters."),

        Node(
            package="create2_driver",
            executable="create2_driver_node",
            name="create2_driver",
            output="screen",
            parameters=[LaunchConfiguration("params_file"), {
                "serial_port": LaunchConfiguration("serial_port"),
            }],
        ),
    ])
