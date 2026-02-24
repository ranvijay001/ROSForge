"""Extended unit tests for rosforge.knowledge.api_mappings - expanded mappings."""

from __future__ import annotations

import pytest

from rosforge.knowledge.api_mappings import (
    ROSCPP_TO_RCLCPP,
    ROSPY_TO_RCLPY,
    get_mapping,
)


class TestRoscppExpandedMappings:
    def test_at_least_80_entries(self):
        assert len(ROSCPP_TO_RCLCPP) >= 80

    def test_shutdown_mapped(self):
        assert "ros::shutdown" in ROSCPP_TO_RCLCPP

    def test_stream_logging_info(self):
        assert ROSCPP_TO_RCLCPP["ROS_INFO_STREAM"] == "RCLCPP_INFO_STREAM"

    def test_stream_logging_warn(self):
        assert ROSCPP_TO_RCLCPP["ROS_WARN_STREAM"] == "RCLCPP_WARN_STREAM"

    def test_stream_logging_error(self):
        assert ROSCPP_TO_RCLCPP["ROS_ERROR_STREAM"] == "RCLCPP_ERROR_STREAM"

    def test_stream_logging_debug(self):
        assert ROSCPP_TO_RCLCPP["ROS_DEBUG_STREAM"] == "RCLCPP_DEBUG_STREAM"

    def test_fatal_logging(self):
        assert "ROS_FATAL" in ROSCPP_TO_RCLCPP

    def test_once_logging(self):
        assert "ROS_INFO_ONCE" in ROSCPP_TO_RCLCPP

    def test_throttle_logging(self):
        assert "ROS_INFO_THROTTLE" in ROSCPP_TO_RCLCPP

    def test_ros_time_type(self):
        assert "ros::Time" in ROSCPP_TO_RCLCPP

    def test_ros_timer(self):
        assert "ros::Timer" in ROSCPP_TO_RCLCPP

    def test_create_timer(self):
        assert "nh.createTimer" in ROSCPP_TO_RCLCPP

    def test_param_set(self):
        assert "ros::param::set" in ROSCPP_TO_RCLCPP

    def test_param_has(self):
        assert "ros::param::has" in ROSCPP_TO_RCLCPP

    def test_nh_set_param(self):
        assert "nh.setParam" in ROSCPP_TO_RCLCPP

    def test_nh_has_param(self):
        assert "nh.hasParam" in ROSCPP_TO_RCLCPP

    def test_tf_header_included(self):
        assert "tf/transform_broadcaster.h" in ROSCPP_TO_RCLCPP

    def test_tf_broadcaster(self):
        assert "tf::TransformBroadcaster" in ROSCPP_TO_RCLCPP

    def test_tf_listener(self):
        assert "tf::TransformListener" in ROSCPP_TO_RCLCPP

    def test_tf_stamped_transform(self):
        assert "tf::StampedTransform" in ROSCPP_TO_RCLCPP

    def test_tf2_ros_broadcaster(self):
        assert "tf2_ros::TransformBroadcaster" in ROSCPP_TO_RCLCPP

    def test_tf2_ros_listener(self):
        assert "tf2_ros::TransformListener" in ROSCPP_TO_RCLCPP

    def test_tf2_ros_buffer(self):
        assert "tf2_ros::Buffer" in ROSCPP_TO_RCLCPP

    def test_actionlib_header(self):
        assert "actionlib/simple_action_client.h" in ROSCPP_TO_RCLCPP

    def test_actionlib_simple_client(self):
        assert "actionlib::SimpleActionClient" in ROSCPP_TO_RCLCPP
        assert ROSCPP_TO_RCLCPP["actionlib::SimpleActionClient"] == "rclcpp_action::Client"

    def test_actionlib_simple_server(self):
        assert "actionlib::SimpleActionServer" in ROSCPP_TO_RCLCPP
        assert ROSCPP_TO_RCLCPP["actionlib::SimpleActionServer"] == "rclcpp_action::Server"

    def test_pluginlib_header(self):
        assert "pluginlib/class_loader.h" in ROSCPP_TO_RCLCPP

    def test_pluginlib_class_loader(self):
        assert "pluginlib::ClassLoader" in ROSCPP_TO_RCLCPP

    def test_image_transport_header(self):
        assert "image_transport/image_transport.h" in ROSCPP_TO_RCLCPP

    def test_image_transport_publisher(self):
        assert "image_transport::Publisher" in ROSCPP_TO_RCLCPP

    def test_diagnostic_updater_header(self):
        assert "diagnostic_updater/diagnostic_updater.h" in ROSCPP_TO_RCLCPP

    def test_diagnostic_updater_class(self):
        assert "diagnostic_updater::Updater" in ROSCPP_TO_RCLCPP

    def test_async_spinner_mapped(self):
        assert "ros::AsyncSpinner" in ROSCPP_TO_RCLCPP

    def test_boost_shared_ptr_mapped(self):
        assert "boost::shared_ptr" in ROSCPP_TO_RCLCPP
        assert ROSCPP_TO_RCLCPP["boost::shared_ptr"] == "std::shared_ptr"

    def test_boost_make_shared_mapped(self):
        assert "boost::make_shared" in ROSCPP_TO_RCLCPP
        assert ROSCPP_TO_RCLCPP["boost::make_shared"] == "std::make_shared"

    def test_wait_for_shutdown(self):
        assert "ros::waitForShutdown" in ROSCPP_TO_RCLCPP


class TestRospyExpandedMappings:
    def test_at_least_50_entries(self):
        assert len(ROSPY_TO_RCLPY) >= 50

    def test_logfatal_mapped(self):
        assert "rospy.logfatal" in ROSPY_TO_RCLPY
        assert ROSPY_TO_RCLPY["rospy.logfatal"] == "node.get_logger().fatal"

    def test_loginfo_once(self):
        assert "rospy.loginfo_once" in ROSPY_TO_RCLPY

    def test_logwarn_once(self):
        assert "rospy.logwarn_once" in ROSPY_TO_RCLPY

    def test_logerr_once(self):
        assert "rospy.logerr_once" in ROSPY_TO_RCLPY

    def test_loginfo_throttle(self):
        assert "rospy.loginfo_throttle" in ROSPY_TO_RCLPY

    def test_ros_time_type(self):
        assert "rospy.Time" in ROSPY_TO_RCLPY
        assert ROSPY_TO_RCLPY["rospy.Time"] == "rclpy.time.Time"

    def test_get_time(self):
        assert "rospy.get_time" in ROSPY_TO_RCLPY

    def test_get_rostime(self):
        assert "rospy.get_rostime" in ROSPY_TO_RCLPY

    def test_delete_param(self):
        assert "rospy.delete_param" in ROSPY_TO_RCLPY

    def test_search_param(self):
        assert "rospy.search_param" in ROSPY_TO_RCLPY

    def test_wait_for_service(self):
        assert "rospy.wait_for_service" in ROSPY_TO_RCLPY

    def test_get_namespace(self):
        assert "rospy.get_namespace" in ROSPY_TO_RCLPY

    def test_on_shutdown(self):
        assert "rospy.on_shutdown" in ROSPY_TO_RCLPY

    def test_tf_broadcaster(self):
        assert "tf.TransformBroadcaster" in ROSPY_TO_RCLPY

    def test_tf_listener(self):
        assert "tf.TransformListener" in ROSPY_TO_RCLPY

    def test_actionlib_client(self):
        assert "actionlib.SimpleActionClient" in ROSPY_TO_RCLPY

    def test_actionlib_server(self):
        assert "actionlib.SimpleActionServer" in ROSPY_TO_RCLPY

    def test_get_published_topics(self):
        assert "rospy.get_published_topics" in ROSPY_TO_RCLPY

    def test_get_caller_id(self):
        assert "rospy.get_caller_id" in ROSPY_TO_RCLPY


class TestGetMappingExtended:
    def test_tf_cpp_lookup(self):
        assert get_mapping("tf::TransformBroadcaster", "cpp") == "tf2_ros::TransformBroadcaster"

    def test_tf_python_lookup(self):
        assert get_mapping("tf.TransformBroadcaster", "python") == "tf2_ros.TransformBroadcaster"

    def test_actionlib_cpp(self):
        assert get_mapping("actionlib::SimpleActionClient", "cpp") == "rclcpp_action::Client"

    def test_actionlib_python(self):
        assert get_mapping("actionlib.SimpleActionClient", "python") == "rclpy_action.ActionClient"

    def test_image_transport_cpp(self):
        result = get_mapping("image_transport/image_transport.h", "cpp")
        assert result == "image_transport/image_transport.hpp"
