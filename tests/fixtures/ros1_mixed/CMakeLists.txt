cmake_minimum_required(VERSION 2.8.3)
project(mixed_pkg)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  rospy
  std_msgs
  sensor_msgs
  message_generation
)

add_message_files(FILES
  Alert.msg
)

generate_messages(
  DEPENDENCIES
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS roscpp rospy std_msgs sensor_msgs message_runtime
)

include_directories(${catkin_INCLUDE_DIRS})

add_executable(sensor_node src/sensor_node.cpp)
target_link_libraries(sensor_node ${catkin_LIBRARIES})
add_dependencies(sensor_node ${catkin_EXPORTED_TARGETS})

catkin_install_python(PROGRAMS
  scripts/monitor.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)

install(DIRECTORY launch/
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/launch
)
