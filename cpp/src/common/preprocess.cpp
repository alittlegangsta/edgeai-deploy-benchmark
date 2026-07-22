#include "edgeai/common/preprocess.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <utility>

#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

namespace edgeai::common {
namespace {

void validate_bgr_image(const cv::Mat& image) {
    if (image.empty()) {
        throw std::runtime_error("preprocessing input image is empty");
    }
    if (image.dims != 2 || image.type() != CV_8UC3) {
        throw std::runtime_error("preprocessing expects a two-dimensional CV_8UC3 BGR image");
    }
}

int round_half_to_even(double value) {
    const double lower = std::floor(value);
    const double fraction = value - lower;
    if (fraction < 0.5) {
        return static_cast<int>(lower);
    }
    if (fraction > 0.5) {
        return static_cast<int>(lower + 1.0);
    }
    const auto lower_integer = static_cast<long long>(lower);
    return static_cast<int>((lower_integer % 2LL == 0LL) ? lower_integer : lower_integer + 1LL);
}

bool finite_box(const Box& box) {
    return std::isfinite(box.x1) && std::isfinite(box.y1) && std::isfinite(box.x2) &&
           std::isfinite(box.y2);
}

}  // namespace

cv::Mat load_bgr_image(const std::filesystem::path& path) {
    if (std::filesystem::is_symlink(path)) {
        throw std::runtime_error("input image must not be a symbolic link: " + path.string());
    }
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("input image is missing or empty: " + path.string());
    }
    cv::Mat image = cv::imread(path.string(), cv::IMREAD_COLOR);
    if (image.empty()) {
        throw std::runtime_error("OpenCV failed to decode input image: " + path.string());
    }
    validate_bgr_image(image);
    return image;
}

PreprocessResult preprocess_image(const cv::Mat& image, const InferenceConfig& config) {
    validate_config(config);
    validate_bgr_image(image);

    const double scale = std::min(
        static_cast<double>(config.input_size.height) / static_cast<double>(image.rows),
        static_cast<double>(config.input_size.width) / static_cast<double>(image.cols)
    );
    const int resized_width = round_half_to_even(static_cast<double>(image.cols) * scale);
    const int resized_height = round_half_to_even(static_cast<double>(image.rows) * scale);
    if (resized_width <= 0 || resized_height <= 0 || resized_width > config.input_size.width ||
        resized_height > config.input_size.height) {
        throw std::runtime_error("letterbox resize produced invalid dimensions");
    }

    cv::Mat resized;
    if (resized_width == image.cols && resized_height == image.rows) {
        resized = image.clone();
    } else {
        cv::resize(image, resized, cv::Size(resized_width, resized_height), 0.0, 0.0, cv::INTER_LINEAR);
    }

    const int horizontal_padding = config.input_size.width - resized_width;
    const int vertical_padding = config.input_size.height - resized_height;
    const int left = horizontal_padding / 2;
    const int right = horizontal_padding - left;
    const int top = vertical_padding / 2;
    const int bottom = vertical_padding - top;

    cv::Mat letterboxed;
    cv::copyMakeBorder(
        resized,
        letterboxed,
        top,
        bottom,
        left,
        right,
        cv::BORDER_CONSTANT,
        cv::Scalar(
            config.letterbox.pad_color_bgr[0],
            config.letterbox.pad_color_bgr[1],
            config.letterbox.pad_color_bgr[2]
        )
    );
    if (letterboxed.cols != config.input_size.width ||
        letterboxed.rows != config.input_size.height) {
        throw std::runtime_error("letterbox output dimensions do not match the configuration");
    }

    const std::size_t plane_size =
        static_cast<std::size_t>(letterboxed.rows) * static_cast<std::size_t>(letterboxed.cols);
    InputTensor tensor;
    tensor.shape = {{1, 3, letterboxed.rows, letterboxed.cols}};
    tensor.values.resize(3U * plane_size);
    for (int y = 0; y < letterboxed.rows; ++y) {
        const auto* row = letterboxed.ptr<cv::Vec3b>(y);
        for (int x = 0; x < letterboxed.cols; ++x) {
            const std::size_t offset = static_cast<std::size_t>(y) *
                                           static_cast<std::size_t>(letterboxed.cols) +
                                       static_cast<std::size_t>(x);
            tensor.values[offset] = static_cast<float>(row[x][2]) / 255.0F;
            tensor.values[plane_size + offset] = static_cast<float>(row[x][1]) / 255.0F;
            tensor.values[2U * plane_size + offset] = static_cast<float>(row[x][0]) / 255.0F;
        }
    }
    for (const float value : tensor.values) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("preprocessing tensor contains a non-finite value");
        }
    }

    LetterboxMetadata metadata;
    metadata.original_size = {image.cols, image.rows};
    metadata.target_size = config.input_size;
    metadata.resized_size = {resized_width, resized_height};
    metadata.scale = scale;
    metadata.padding = {left, top, right, bottom};
    metadata.pad_color_bgr = config.letterbox.pad_color_bgr;
    metadata.interpolation = config.letterbox.interpolation;
    metadata.transforms = {
        "BGR_TO_RGB",
        "HWC_TO_CHW",
        "uint8_TO_float32",
        "divide_by_255",
        "add_batch_dimension",
    };
    return {letterboxed, std::move(tensor), std::move(metadata)};
}

std::optional<Box> restore_and_clip_box(
    const Box& input_box,
    const LetterboxMetadata& metadata
) {
    if (!finite_box(input_box)) {
        throw std::runtime_error("input box contains a non-finite value");
    }
    if (!std::isfinite(metadata.scale) || metadata.scale <= 0.0) {
        throw std::runtime_error("letterbox scale must be finite and positive");
    }
    if (metadata.original_size.width <= 0 || metadata.original_size.height <= 0) {
        throw std::runtime_error("letterbox original dimensions must be positive");
    }
    Box restored{
        static_cast<float>((static_cast<double>(input_box.x1) - metadata.padding.left) /
                           metadata.scale),
        static_cast<float>((static_cast<double>(input_box.y1) - metadata.padding.top) /
                           metadata.scale),
        static_cast<float>((static_cast<double>(input_box.x2) - metadata.padding.left) /
                           metadata.scale),
        static_cast<float>((static_cast<double>(input_box.y2) - metadata.padding.top) /
                           metadata.scale),
    };
    restored.x1 = std::clamp(restored.x1, 0.0F, static_cast<float>(metadata.original_size.width));
    restored.x2 = std::clamp(restored.x2, 0.0F, static_cast<float>(metadata.original_size.width));
    restored.y1 = std::clamp(restored.y1, 0.0F, static_cast<float>(metadata.original_size.height));
    restored.y2 = std::clamp(restored.y2, 0.0F, static_cast<float>(metadata.original_size.height));
    if (restored.x2 <= restored.x1 || restored.y2 <= restored.y1) {
        return std::nullopt;
    }
    return restored;
}

}  // namespace edgeai::common
