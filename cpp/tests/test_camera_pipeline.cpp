#include "edgeai/common/camera_pipeline.hpp"

#include <cassert>
#include <chrono>
#include <thread>

#include <opencv2/core/mat.hpp>

int main() {
    edgeai::common::LatestFrameSlot slot;
    cv::Mat first(2, 2, CV_8UC3, cv::Scalar(1, 2, 3));
    cv::Mat second(2, 2, CV_8UC3, cv::Scalar(4, 5, 6));
    assert(!slot.publish({first.clone(), 1U, 1.0}));
    assert(slot.publish({second.clone(), 2U, 2.0}));
    assert(slot.published_count() == 2U);
    assert(slot.overwritten_count() == 1U);
    edgeai::common::CameraFrame received;
    assert(slot.wait_pop(received));
    assert(received.sequence == 2U);
    assert(received.bgr.at<cv::Vec3b>(0, 0)[0] == 4U);
    slot.close();
    assert(!slot.wait_pop(received));
    return 0;
}
