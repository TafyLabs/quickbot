"""Robot-side bring-up: robot_state_publisher + create2_driver + depth-to-scan.

This is the Phase 3/4 entry point. The create2_driver_node is still a stub
until P3 lands; until then `ros2 launch quickbot_bringup robot.launch.py` will
launch robot_state_publisher only, so RViz/TF/calibration work can proceed.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
        DeclareLaunchArgument("enable_camera", default_value="false",
                              description="Set true once RealSense wrapper is installed."),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare("quickbot_description"), "launch", "description.launch.py",
                ]),
            ]),
        ),

        # create2_driver_node will be wired here in P3 — see
        # ws/src/create2_driver/create2_driver/driver_node.py.
    ])
