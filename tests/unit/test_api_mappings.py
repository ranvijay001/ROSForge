"""Unit tests for rosforge.knowledge.api_mappings."""

from __future__ import annotations

import pytest

from rosforge.knowledge.api_mappings import (
    ROSCPP_TO_RCLCPP,
    ROSPY_TO_RCLPY,
    get_mapping,
)


class TestRoscppToRclcpp:
    def test_header_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros/ros.h"] == "rclcpp/rclcpp.hpp"

    def test_init_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros::init"] == "rclcpp::init"

    def test_publisher_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros::Publisher"] == "rclcpp::Publisher<T>::SharedPtr"

    def test_subscriber_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros::Subscriber"] == "rclcpp::Subscription<T>::SharedPtr"

    def test_spin_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros::spin"] == "rclcpp::spin"

    def test_spin_once_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros::spinOnce"] == "rclcpp::spin_some"

    def test_ok_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros::ok"] == "rclcpp::ok"

    def test_logging_info(self):
        assert ROSCPP_TO_RCLCPP["ROS_INFO"] == "RCLCPP_INFO"

    def test_logging_warn(self):
        assert ROSCPP_TO_RCLCPP["ROS_WARN"] == "RCLCPP_WARN"

    def test_logging_error(self):
        assert ROSCPP_TO_RCLCPP["ROS_ERROR"] == "RCLCPP_ERROR"

    def test_logging_debug(self):
        assert ROSCPP_TO_RCLCPP["ROS_DEBUG"] == "RCLCPP_DEBUG"

    def test_rate_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros::Rate"] == "rclcpp::Rate"

    def test_duration_mapping(self):
        assert ROSCPP_TO_RCLCPP["ros::Duration"] == "rclcpp::Duration"

    def test_service_server(self):
        assert ROSCPP_TO_RCLCPP["ros::ServiceServer"] == "rclcpp::Service<T>::SharedPtr"

    def test_service_client(self):
        assert ROSCPP_TO_RCLCPP["ros::ServiceClient"] == "rclcpp::Client<T>::SharedPtr"

    def test_param_get(self):
        assert ROSCPP_TO_RCLCPP["nh.getParam"] == "node->get_parameter"

    def test_at_least_25_entries(self):
        assert len(ROSCPP_TO_RCLCPP) >= 25


class TestRospyToRclpy:
    def test_init_node(self):
        assert ROSPY_TO_RCLPY["rospy.init_node"] == "rclpy.init"

    def test_publisher(self):
        assert ROSPY_TO_RCLPY["rospy.Publisher"] == "node.create_publisher"

    def test_subscriber(self):
        assert ROSPY_TO_RCLPY["rospy.Subscriber"] == "node.create_subscription"

    def test_spin(self):
        assert ROSPY_TO_RCLPY["rospy.spin"] == "rclpy.spin"

    def test_loginfo(self):
        assert ROSPY_TO_RCLPY["rospy.loginfo"] == "node.get_logger().info"

    def test_logwarn(self):
        assert ROSPY_TO_RCLPY["rospy.logwarn"] == "node.get_logger().warn"

    def test_logerr(self):
        assert ROSPY_TO_RCLPY["rospy.logerr"] == "node.get_logger().error"

    def test_service(self):
        assert ROSPY_TO_RCLPY["rospy.Service"] == "node.create_service"

    def test_service_proxy(self):
        assert ROSPY_TO_RCLPY["rospy.ServiceProxy"] == "node.create_client"

    def test_duration(self):
        assert ROSPY_TO_RCLPY["rospy.Duration"] == "rclpy.duration.Duration"

    def test_get_param(self):
        assert ROSPY_TO_RCLPY["rospy.get_param"] == "node.get_parameter"

    def test_at_least_20_entries(self):
        assert len(ROSPY_TO_RCLPY) >= 20


class TestGetMapping:
    def test_cpp_lookup(self):
        assert get_mapping("ros/ros.h", "cpp") == "rclcpp/rclcpp.hpp"

    def test_python_lookup(self):
        assert get_mapping("rospy.init_node", "python") == "rclpy.init"

    def test_default_language_is_cpp(self):
        assert get_mapping("ros::ok") == "rclcpp::ok"

    def test_missing_key_returns_none(self):
        assert get_mapping("nonexistent_api") is None

    def test_unknown_language_returns_none(self):
        assert get_mapping("ros::ok", "java") is None

    def test_python_key_not_found_in_cpp(self):
        assert get_mapping("rospy.init_node", "cpp") is None
