"""Publish robot_description from the QuickBot Xacro file."""
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description() -> LaunchDescription:
    share = Path(get_package_share_directory("quickbot_description"))
    default_urdf = str(share / "urdf" / "quickbot.urdf.xacro")

    return LaunchDescription([
        DeclareLaunchArgument("urdf", default_value=default_urdf),
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[{
                "robot_description": ParameterValue(
                    Command(["xacro ", LaunchConfiguration("urdf")]),
                    value_type=str,
                ),
                "use_sim_time": False,
            }],
        ),
    ])
