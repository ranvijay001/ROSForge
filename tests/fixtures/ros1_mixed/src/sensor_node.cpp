#include "ros/ros.h"
#include "std_msgs/String.h"
#include "sensor_msgs/LaserScan.h"

class SensorNode {
public:
    SensorNode() {
        pub_ = nh_.advertise<std_msgs::String>("status", 10);
        scan_sub_ = nh_.subscribe("scan", 10, &SensorNode::scanCallback, this);
        timer_ = nh_.createTimer(ros::Duration(1.0), &SensorNode::timerCallback, this);
    }

    void scanCallback(const sensor_msgs::LaserScan::ConstPtr& msg) {
        ROS_INFO("Got scan with %zu ranges", msg->ranges.size());
    }

    void timerCallback(const ros::TimerEvent& event) {
        std_msgs::String out;
        out.data = "alive";
        pub_.publish(out);
    }

private:
    ros::NodeHandle nh_;
    ros::Publisher pub_;
    ros::Subscriber scan_sub_;
    ros::Timer timer_;
};

int main(int argc, char** argv) {
    ros::init(argc, argv, "sensor_node");
    SensorNode node;
    ros::spin();
    return 0;
}
