cmake_minimum_required(VERSION 3.8)
project(quickbot_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY urdf launch rviz
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL
)

ament_package()
