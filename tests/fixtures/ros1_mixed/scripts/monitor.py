#!/usr/bin/env python
"""ROS1 monitor node using rospy."""

import rospy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String


def scan_callback(msg):
    rospy.loginfo("Scan ranges: %d", len(msg.ranges))


def main():
    rospy.init_node("monitor", anonymous=True)
    rate = rospy.Rate(1)

    pub = rospy.Publisher("monitor/status", String, queue_size=10)
    rospy.Subscriber("scan", LaserScan, scan_callback)

    while not rospy.is_shutdown():
        msg = String()
        msg.data = "monitoring"
        pub.publish(msg)
        rate.sleep()


if __name__ == "__main__":
    main()
