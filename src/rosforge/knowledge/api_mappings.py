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
    "ros::shutdown": "rclcpp::shutdown",
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
    "ros::waitForShutdown": "rclcpp::spin(node)",
    # Logging macros
    "ROS_INFO(...)": "RCLCPP_INFO(node->get_logger(), ...)",
    "ROS_INFO": "RCLCPP_INFO",
    "ROS_INFO_STREAM": "RCLCPP_INFO_STREAM",
    "ROS_WARN(...)": "RCLCPP_WARN(node->get_logger(), ...)",
    "ROS_WARN": "RCLCPP_WARN",
    "ROS_WARN_STREAM": "RCLCPP_WARN_STREAM",
    "ROS_ERROR(...)": "RCLCPP_ERROR(node->get_logger(), ...)",
    "ROS_ERROR": "RCLCPP_ERROR",
    "ROS_ERROR_STREAM": "RCLCPP_ERROR_STREAM",
    "ROS_DEBUG(...)": "RCLCPP_DEBUG(node->get_logger(), ...)",
    "ROS_DEBUG": "RCLCPP_DEBUG",
    "ROS_DEBUG_STREAM": "RCLCPP_DEBUG_STREAM",
    "ROS_FATAL": "RCLCPP_FATAL",
    "ROS_FATAL_STREAM": "RCLCPP_FATAL_STREAM",
    "ROS_INFO_ONCE": "RCLCPP_INFO_ONCE",
    "ROS_WARN_ONCE": "RCLCPP_WARN_ONCE",
    "ROS_ERROR_ONCE": "RCLCPP_ERROR_ONCE",
    "ROS_INFO_THROTTLE": "RCLCPP_INFO_THROTTLE",
    "ROS_WARN_THROTTLE": "RCLCPP_WARN_THROTTLE",
    # Time
    "ros::Time::now()": "node->now()",
    "ros::Time::now": "node->now",
    "ros::Time": "rclcpp::Time",
    "ros::Duration": "rclcpp::Duration",
    "ros::WallTime": "rclcpp::Clock",
    "ros::WallDuration": "rclcpp::Duration",
    "ros::WallTimer": "rclcpp::WallTimer",
    "ros::Timer": "rclcpp::TimerBase::SharedPtr",
    "nh.createTimer": "node->create_wall_timer",
    # Services
    "ros::ServiceServer": "rclcpp::Service<T>::SharedPtr",
    "ros::ServiceClient": "rclcpp::Client<T>::SharedPtr",
    "nh.advertiseService": "node->create_service<T>",
    "nh.serviceClient<T>": "node->create_client<T>",
    "nh.serviceClient": "node->create_client",
    "ros::service::call": "client->async_send_request",
    "ros::service::waitForService": "client->wait_for_service",
    # Parameters
    "ros::param::get": "node->get_parameter",
    "ros::param::set": "node->set_parameter",
    "ros::param::has": "node->has_parameter",
    "nh.getParam": "node->get_parameter",
    "nh.setParam": "node->set_parameter",
    "nh.hasParam": "node->has_parameter",
    "nh.deleteParam": "node->undeclare_parameter",
    "nh.param<T>": "node->declare_parameter<T>",
    "nh.param": "node->declare_parameter",
    "nh.getParamCached": "node->get_parameter",
    # TF / TF2
    "tf/tf.h": "tf2_ros/transform_broadcaster.h",
    "tf/transform_broadcaster.h": "tf2_ros/transform_broadcaster.h",
    "tf/transform_listener.h": "tf2_ros/transform_listener.h",
    "tf::TransformBroadcaster": "tf2_ros::TransformBroadcaster",
    "tf::TransformListener": "tf2_ros::TransformListener",
    "tf::StampedTransform": "geometry_msgs::msg::TransformStamped",
    "tf::Transform": "geometry_msgs::msg::Transform",
    "tf::Quaternion": "tf2::Quaternion",
    "tf::Vector3": "tf2::Vector3",
    "tf2_ros::TransformBroadcaster": "tf2_ros::TransformBroadcaster",
    "tf2_ros::TransformListener": "tf2_ros::TransformListener",
    "tf2_ros::Buffer": "tf2_ros::Buffer",
    "transformBroadcaster.sendTransform": "tf_broadcaster->sendTransform",
    "transformListener.lookupTransform": "tf_buffer->lookupTransform",
    "transformListener.waitForTransform": "tf_buffer->canTransform",
    # Actionlib
    "actionlib/simple_action_client.h": "rclcpp_action/rclcpp_action.hpp",
    "actionlib/simple_action_server.h": "rclcpp_action/rclcpp_action.hpp",
    "actionlib::SimpleActionClient": "rclcpp_action::Client",
    "actionlib::SimpleActionServer": "rclcpp_action::Server",
    "actionlib::SimpleClientGoalState": "rclcpp_action::ResultCode",
    "action_client.sendGoal": "action_client->async_send_goal",
    "action_client.waitForResult": "action_client->async_get_result",
    "action_client.getResult": "goal_handle->get_result",
    # Dynamic reconfigure (removed in ROS2 — use parameter events)
    "dynamic_reconfigure::Server": "rclcpp::node_interfaces::NodeParametersInterface",
    # Pluginlib
    "pluginlib/class_loader.h": "pluginlib/class_loader.hpp",
    "pluginlib::ClassLoader": "pluginlib::ClassLoader",
    # Image transport
    "image_transport/image_transport.h": "image_transport/image_transport.hpp",
    "image_transport::ImageTransport": "image_transport::ImageTransport",
    "image_transport::Publisher": "image_transport::Publisher",
    "image_transport::Subscriber": "image_transport::Subscriber",
    # Diagnostic updater
    "diagnostic_updater/diagnostic_updater.h": "diagnostic_updater/diagnostic_updater.hpp",
    "diagnostic_updater::Updater": "diagnostic_updater::Updater",
    "diagnostic_updater::DiagnosticStatusWrapper": "diagnostic_updater::DiagnosticStatusWrapper",
    # Node options
    "ros::console::set_logger_level": "rcutils_logging_set_logger_level",
    # Callbacks / executors
    "ros::AsyncSpinner": "rclcpp::executors::MultiThreadedExecutor",
    "ros::MultiThreadedSpinner": "rclcpp::executors::MultiThreadedExecutor",
    "ros::CallbackQueue": "rclcpp::CallbackGroup",
    # Messages
    "ros::message_traits::MD5Sum": "rosidl_generator_traits::TypeName",
    "boost::shared_ptr": "std::shared_ptr",
    "boost::make_shared": "std::make_shared",
}

# rospy → rclpy mappings
# Key: ROS1 pattern/token, Value: ROS2 equivalent
ROSPY_TO_RCLPY: dict[str, str] = {
    # Initialization / shutdown
    "rospy.init_node": "rclpy.init",
    "rospy.signal_shutdown": "rclpy.shutdown",
    "rospy.is_shutdown": "not rclpy.ok()",
    "rospy.ok": "rclpy.ok",
    "rospy.on_shutdown": "# Use rclpy context shutdown callbacks",
    # Node creation
    "rospy.get_name()": "node.get_name()",
    "rospy.get_namespace": "node.get_namespace",
    "rospy.get_node_uri": "node.get_node_names_and_namespaces",
    # Publishers / subscribers
    "rospy.Publisher": "node.create_publisher",
    "rospy.Subscriber": "node.create_subscription",
    # Services
    "rospy.Service": "node.create_service",
    "rospy.ServiceProxy": "node.create_client",
    "rospy.wait_for_service": "client.wait_for_service",
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
    "rospy.logfatal": "node.get_logger().fatal",
    "rospy.loginfo_once": "node.get_logger().info",
    "rospy.logwarn_once": "node.get_logger().warn",
    "rospy.logerr_once": "node.get_logger().error",
    "rospy.loginfo_throttle": "node.get_logger().info",
    "rospy.logwarn_throttle": "node.get_logger().warn",
    "rospy.logerr_throttle": "node.get_logger().error",
    # Time
    "rospy.Time.now()": "node.get_clock().now()",
    "rospy.Time.now": "node.get_clock().now",
    "rospy.Time": "rclpy.time.Time",
    "rospy.Duration": "rclpy.duration.Duration",
    "rospy.get_time": "node.get_clock().now().nanoseconds / 1e9",
    "rospy.get_rostime": "node.get_clock().now()",
    # Parameters
    "rospy.get_param": "node.get_parameter",
    "rospy.set_param": "node.set_parameters",
    "rospy.has_param": "node.has_parameter",
    "rospy.delete_param": "node.undeclare_parameter",
    "rospy.search_param": "node.get_parameter",
    # TF
    "tf.TransformBroadcaster": "tf2_ros.TransformBroadcaster",
    "tf.TransformListener": "tf2_ros.TransformListener",
    "tf.Buffer": "tf2_ros.Buffer",
    # Actionlib
    "actionlib.SimpleActionClient": "rclpy_action.ActionClient",
    "actionlib.SimpleActionServer": "rclpy_action.ActionServer",
    # Messages
    "rospy.AnyMsg": "# Use specific message types in ROS2",
    # Topics
    "rospy.get_published_topics": "node.get_topic_names_and_types",
    "rospy.resolve_name": "node.resolve_topic_name",
    # Miscellaneous
    "rospy.myargv": "# Use argparse or rclpy argument parsing",
    "rospy.get_caller_id": "node.get_name",
    "rospy.get_master": "# No master in ROS2; use discovery",
    "rospy.remap_name": "node.resolve_topic_name",
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
