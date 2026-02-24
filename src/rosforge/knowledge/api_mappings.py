"""ROS1 → ROS2 API mapping tables.

Provides static lookup tables for roscpp→rclcpp and rospy→rclpy API
translations, used by both the PromptBuilder and rule-based transformers.
"""

from __future__ import annotations

# roscpp → rclcpp mappings
# Key: ROS1 pattern/token, Value: ROS2 equivalent
ROSCPP_TO_RCLCPP: dict[str, str] = {
    # Headers
    "ros/ros.h": "rclcpp/rclcpp.hpp",
    # Initialization
    'ros::init(argc, argv, "node_name")': "rclcpp::init(argc, argv)",
    "ros::init": "rclcpp::init",
    # Node handle
    "ros::NodeHandle nh": 'auto node = std::make_shared<rclcpp::Node>("node_name")',
    "ros::NodeHandle": "rclcpp::Node",
    # Publishers / subscribers
    "ros::Publisher": "rclcpp::Publisher<T>::SharedPtr",
    "ros::Subscriber": "rclcpp::Subscription<T>::SharedPtr",
    "nh.advertise<T>(topic, queue_size)": "node->create_publisher<T>(topic, queue_size)",
    "nh.advertise": "node->create_publisher",
    "nh.subscribe(topic, queue_size, callback)": "node->create_subscription<T>(topic, queue_size, callback)",
    "nh.subscribe": "node->create_subscription",
    # Rate / spinning
    "ros::Rate": "rclcpp::Rate",
    "ros::spin()": "rclcpp::spin(node)",
    "ros::spin": "rclcpp::spin",
    "ros::spinOnce()": "rclcpp::spin_some(node)",
    "ros::spinOnce": "rclcpp::spin_some",
    "ros::ok()": "rclcpp::ok()",
    "ros::ok": "rclcpp::ok",
    # Logging macros
    "ROS_INFO(...)": "RCLCPP_INFO(node->get_logger(), ...)",
    "ROS_INFO": "RCLCPP_INFO",
    "ROS_WARN(...)": "RCLCPP_WARN(node->get_logger(), ...)",
    "ROS_WARN": "RCLCPP_WARN",
    "ROS_ERROR(...)": "RCLCPP_ERROR(node->get_logger(), ...)",
    "ROS_ERROR": "RCLCPP_ERROR",
    "ROS_DEBUG(...)": "RCLCPP_DEBUG(node->get_logger(), ...)",
    "ROS_DEBUG": "RCLCPP_DEBUG",
    # Time
    "ros::Time::now()": "node->now()",
    "ros::Time::now": "node->now",
    "ros::Duration": "rclcpp::Duration",
    # Services
    "ros::ServiceServer": "rclcpp::Service<T>::SharedPtr",
    "ros::ServiceClient": "rclcpp::Client<T>::SharedPtr",
    "nh.advertiseService": "node->create_service<T>",
    "nh.serviceClient<T>": "node->create_client<T>",
    "nh.serviceClient": "node->create_client",
    # Parameters
    "ros::param::get": "node->get_parameter",
    "nh.getParam": "node->get_parameter",
    "nh.param<T>": "node->declare_parameter<T>",
    "nh.param": "node->declare_parameter",
}

# rospy → rclpy mappings
# Key: ROS1 pattern/token, Value: ROS2 equivalent
ROSPY_TO_RCLPY: dict[str, str] = {
    # Initialization / shutdown
    "rospy.init_node": "rclpy.init",
    "rospy.signal_shutdown": "rclpy.shutdown",
    "rospy.is_shutdown": "not rclpy.ok()",
    "rospy.ok": "rclpy.ok",
    # Node creation
    "rospy.get_name()": "node.get_name()",
    # Publishers / subscribers
    "rospy.Publisher": "node.create_publisher",
    "rospy.Subscriber": "node.create_subscription",
    # Services
    "rospy.Service": "node.create_service",
    "rospy.ServiceProxy": "node.create_client",
    # Rate / spinning
    "rospy.Rate": "node.create_rate",
    "rospy.spin()": "rclpy.spin(node)",
    "rospy.spin": "rclpy.spin",
    "rospy.sleep": "node.get_clock().sleep_for",
    # Logging
    "rospy.loginfo": "node.get_logger().info",
    "rospy.logwarn": "node.get_logger().warn",
    "rospy.logerr": "node.get_logger().error",
    "rospy.logdebug": "node.get_logger().debug",
    # Time
    "rospy.Time.now()": "node.get_clock().now()",
    "rospy.Time.now": "node.get_clock().now",
    "rospy.Duration": "rclpy.duration.Duration",
    # Parameters
    "rospy.get_param": "node.get_parameter",
    "rospy.set_param": "node.set_parameters",
    "rospy.has_param": "node.has_parameter",
}


def get_mapping(api_name: str, language: str = "cpp") -> str | None:
    """Look up the ROS2 equivalent of a ROS1 API name.

    Args:
        api_name: The ROS1 API name or pattern to translate.
        language: Either ``"cpp"`` (roscpp→rclcpp) or ``"python"``
                  (rospy→rclpy).

    Returns:
        The ROS2 equivalent string, or ``None`` if no mapping is found.
    """
    if language == "cpp":
        return ROSCPP_TO_RCLCPP.get(api_name)
    if language == "python":
        return ROSPY_TO_RCLPY.get(api_name)
    return None
