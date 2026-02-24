cmake_minimum_required(VERSION 3.0.2)
project(ros1_msgs)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  std_msgs
  message_generation
)

add_message_files(
  FILES
  Pose2D.msg
  StringArray.msg
)

add_service_files(
  FILES
  AddTwoInts.srv
)

add_action_files(
  FILES
  Fibonacci.action
)

generate_messages(
  DEPENDENCIES
  std_msgs
)

catkin_package(
  CATKIN_DEPENDS roscpp std_msgs message_runtime
)

add_executable(talker src/talker.cpp)
target_link_libraries(talker ${catkin_LIBRARIES})

add_library(mylib src/lib.cpp)
target_link_libraries(mylib ${catkin_LIBRARIES})

install(TARGETS talker mylib
  RUNTIME DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
  LIBRARY DESTINATION ${CATKIN_PACKAGE_LIB_DESTINATION}
)
