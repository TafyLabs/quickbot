"""Robot-side bring-up: robot_state_publisher + create2_driver.

Gate G4 entry point. Adds the D455 + depth-to-scan in P4 (Gate G6) once the
RealSense wrapper is in the image.
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description() -> LaunchDescription:
    return LaunchDescription([
        DeclareLaunchArgument("serial_port", default_value="/dev/ttyUSB0"),
        DeclareLaunchArgument("params_file",
                              default_value="/config/create2_calibration.yaml"),
        DeclareLaunchArgument("enable_camera", default_value="false",
                              description="Set true once RealSense wrapper is installed."),

        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare("quickbot_description"),
                    "launch", "description.launch.py",
                ]),
            ]),
        ),

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
