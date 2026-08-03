#include "edgeai/common/camera_pipeline.hpp"

namespace edgeai::common {

bool LatestFrameSlot::publish(CameraFrame frame) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (closed_) {
        return false;
    }
    const bool overwritten = latest_.has_value();
    if (overwritten) {
        ++overwritten_count_;
    }
    latest_ = std::move(frame);
    ++published_count_;
    condition_.notify_one();
    return overwritten;
}

bool LatestFrameSlot::wait_pop(CameraFrame& frame) {
    std::unique_lock<std::mutex> lock(mutex_);
    condition_.wait(lock, [this] { return latest_.has_value() || closed_; });
    if (!latest_.has_value()) {
        return false;
    }
    frame = std::move(*latest_);
    latest_.reset();
    return true;
}

void LatestFrameSlot::close() {
    std::lock_guard<std::mutex> lock(mutex_);
    closed_ = true;
    condition_.notify_all();
}

bool LatestFrameSlot::closed() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return closed_;
}

bool LatestFrameSlot::has_pending() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return latest_.has_value();
}

std::size_t LatestFrameSlot::published_count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return published_count_;
}

std::size_t LatestFrameSlot::overwritten_count() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return overwritten_count_;
}

}  // namespace edgeai::common
