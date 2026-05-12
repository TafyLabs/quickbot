cmake_minimum_required(VERSION 3.8)
project(quickbot_nav)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY config maps rviz
  DESTINATION share/${PROJECT_NAME}
  OPTIONAL
)

ament_package()
