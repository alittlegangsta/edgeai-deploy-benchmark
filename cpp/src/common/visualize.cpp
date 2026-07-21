#include "edgeai/common/visualize.hpp"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <sstream>
#include <stdexcept>

#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

namespace edgeai::common {

cv::Scalar class_color(int class_id) {
    if (class_id < 0) {
        throw std::runtime_error("class_id must not be negative");
    }
    return {
        static_cast<double>((37 * class_id + 67) % 192 + 32),
        static_cast<double>((17 * class_id + 149) % 192 + 32),
        static_cast<double>((29 * class_id + 101) % 192 + 32),
    };
}

cv::Mat draw_detections(const cv::Mat& image, const std::vector<Detection>& detections) {
    if (image.empty() || image.dims != 2 || image.type() != CV_8UC3) {
        throw std::runtime_error("visualization expects a nonempty CV_8UC3 BGR image");
    }
    cv::Mat output = image.clone();
    for (const auto& detection : detections) {
        if (detection.class_id < 0 || detection.class_name.empty() ||
            !std::isfinite(detection.confidence) || detection.confidence < 0.0F ||
            detection.confidence > 1.0F) {
            throw std::runtime_error("detection metadata is invalid for visualization");
        }
        const int left = std::clamp(
            static_cast<int>(std::lround(detection.box_xyxy_source.x1)), 0, output.cols - 1
        );
        const int top = std::clamp(
            static_cast<int>(std::lround(detection.box_xyxy_source.y1)), 0, output.rows - 1
        );
        const int right = std::clamp(
            static_cast<int>(std::lround(detection.box_xyxy_source.x2)), 0, output.cols - 1
        );
        const int bottom = std::clamp(
            static_cast<int>(std::lround(detection.box_xyxy_source.y2)), 0, output.rows - 1
        );
        if (right <= left || bottom <= top) {
            throw std::runtime_error("detection box is invalid after raster clipping");
        }

        const cv::Scalar color = class_color(detection.class_id);
        std::ostringstream label_stream;
        label_stream << detection.class_name << ' ' << std::fixed << std::setprecision(3)
                     << detection.confidence;
        const std::string label = label_stream.str();
        cv::rectangle(output, {left, top}, {right, bottom}, color, 2, cv::LINE_8);
        int baseline = 0;
        const cv::Size text_size =
            cv::getTextSize(label, cv::FONT_HERSHEY_SIMPLEX, 0.6, 1, &baseline);
        const int label_top = std::max(0, top - text_size.height - baseline - 4);
        const int label_right = std::min(output.cols - 1, left + text_size.width + 4);
        cv::rectangle(output, {left, label_top}, {label_right, top}, color, cv::FILLED, cv::LINE_8);
        cv::putText(
            output,
            label,
            {left + 2, std::max(text_size.height + 1, top - baseline - 2)},
            cv::FONT_HERSHEY_SIMPLEX,
            0.6,
            {255, 255, 255},
            1,
            cv::LINE_AA
        );
    }
    return output;
}

void save_image(const std::filesystem::path& path, const cv::Mat& image) {
    if (image.empty()) {
        throw std::runtime_error("cannot save an empty image");
    }
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path());
    }
    if (!cv::imwrite(path.string(), image)) {
        throw std::runtime_error("OpenCV failed to write image: " + path.string());
    }
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("output image is missing or empty: " + path.string());
    }
}

}  // namespace edgeai::common
