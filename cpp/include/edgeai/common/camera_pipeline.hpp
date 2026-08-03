#pragma once

#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <optional>

#include <opencv2/core/mat.hpp>

namespace edgeai::common {

struct CameraFrame {
    cv::Mat bgr;
    std::uint64_t sequence{0U};
    double capture_monotonic_ms{0.0};
};

// A single-slot, latest-frame-wins hand-off between camera capture and
// inference. publish() owns the supplied Mat after the call and reports
// whether an older unprocessed frame was overwritten.
class LatestFrameSlot {
public:
    LatestFrameSlot() = default;
    LatestFrameSlot(const LatestFrameSlot&) = delete;
    LatestFrameSlot& operator=(const LatestFrameSlot&) = delete;

    bool publish(CameraFrame frame);
    bool wait_pop(CameraFrame& frame);
    void close();
    bool closed() const;
    bool has_pending() const;
    std::size_t published_count() const;
    std::size_t overwritten_count() const;

private:
    mutable std::mutex mutex_;
    std::condition_variable condition_;
    std::optional<CameraFrame> latest_;
    bool closed_{false};
    std::size_t published_count_{0U};
    std::size_t overwritten_count_{0U};
};

}  // namespace edgeai::common
