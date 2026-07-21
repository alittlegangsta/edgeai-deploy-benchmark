#include "edgeai/common/config.hpp"

#include <cmath>
#include <sstream>
#include <stdexcept>
#include <unordered_set>
#include <utility>

#include <opencv2/core/persistence.hpp>

namespace edgeai::common {
namespace {

cv::FileNode require_node(const cv::FileStorage& storage, const char* name) {
    const cv::FileNode node = storage[name];
    if (node.empty()) {
        throw std::runtime_error(std::string("missing configuration field: ") + name);
    }
    return node;
}

int read_int(const cv::FileNode& node, const char* name) {
    if (!node.isInt()) {
        throw std::runtime_error(std::string("configuration field must be an integer: ") + name);
    }
    return static_cast<int>(node);
}

double read_number(const cv::FileNode& node, const char* name) {
    if (!node.isInt() && !node.isReal()) {
        throw std::runtime_error(std::string("configuration field must be numeric: ") + name);
    }
    return static_cast<double>(node);
}

bool read_bool(const cv::FileNode& node, const char* name) {
    if (!node.isInt()) {
        throw std::runtime_error(std::string("configuration field must be boolean: ") + name);
    }
    const int value = static_cast<int>(node);
    if (value != 0 && value != 1) {
        throw std::runtime_error(std::string("configuration boolean must be 0 or 1: ") + name);
    }
    return value == 1;
}

std::vector<std::string> read_class_names(const cv::FileNode& node) {
    std::vector<std::string> names;
    if (!node.isSeq()) {
        throw std::runtime_error("class_names must be a JSON array");
    }
    names.reserve(node.size());
    for (const auto& entry : node) {
        if (!entry.isString()) {
            throw std::runtime_error("every class name must be a string");
        }
        names.push_back(static_cast<std::string>(entry));
    }
    return names;
}

}  // namespace

const std::vector<std::string>& frozen_coco80_class_names() {
    static const std::vector<std::string> names{
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
        "truck", "boat", "traffic light", "fire hydrant", "stop sign",
        "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
        "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
        "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
        "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
        "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
        "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
        "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
        "mouse", "remote", "keyboard", "cell phone", "microwave", "oven",
        "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
        "teddy bear", "hair drier", "toothbrush",
    };
    return names;
}

void validate_config(const InferenceConfig& config) {
    if (config.schema_version != 1) {
        throw std::runtime_error("configuration schema_version must be 1");
    }
    if (config.input_size.width <= 0 || config.input_size.height <= 0) {
        throw std::runtime_error("input dimensions must be positive");
    }
    if (!std::isfinite(config.confidence_threshold) ||
        config.confidence_threshold < 0.0 || config.confidence_threshold > 1.0) {
        throw std::runtime_error("confidence_threshold must be finite and in [0, 1]");
    }
    if (!std::isfinite(config.iou_threshold) || config.iou_threshold < 0.0 ||
        config.iou_threshold > 1.0) {
        throw std::runtime_error("iou_threshold must be finite and in [0, 1]");
    }
    if (!config.class_aware_nms) {
        throw std::runtime_error("class_aware_nms must remain enabled");
    }
    if (config.max_detections <= 0) {
        throw std::runtime_error("max_detections must be positive");
    }
    if (config.class_names.empty()) {
        throw std::runtime_error("class_names must not be empty");
    }
    std::unordered_set<std::string> unique_names;
    for (const auto& name : config.class_names) {
        if (name.empty()) {
            throw std::runtime_error("class_names must not contain empty strings");
        }
        if (!unique_names.insert(name).second) {
            throw std::runtime_error("class_names must be unique");
        }
    }
    for (const int channel : config.letterbox.pad_color_bgr) {
        if (channel < 0 || channel > 255) {
            throw std::runtime_error("letterbox pad_color_bgr values must be in [0, 255]");
        }
    }
    if (config.letterbox.interpolation != "cv2.INTER_LINEAR") {
        throw std::runtime_error("only cv2.INTER_LINEAR interpolation is supported");
    }
}

InferenceConfig load_config(const std::filesystem::path& path) {
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("configuration file is missing or empty: " + path.string());
    }
    cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
    if (!storage.isOpened()) {
        throw std::runtime_error("failed to parse configuration JSON: " + path.string());
    }

    InferenceConfig config;
    config.schema_version = read_int(require_node(storage, "schema_version"), "schema_version");
    config.confidence_threshold =
        read_number(require_node(storage, "confidence_threshold"), "confidence_threshold");
    config.iou_threshold = read_number(require_node(storage, "iou_threshold"), "iou_threshold");
    config.class_aware_nms =
        read_bool(require_node(storage, "class_aware_nms"), "class_aware_nms");
    config.max_detections =
        read_int(require_node(storage, "max_detections"), "max_detections");

    const cv::FileNode input_size = require_node(storage, "input_size");
    if (!input_size.isSeq() || input_size.size() != 2U) {
        throw std::runtime_error("input_size must contain [height, width]");
    }
    auto input_size_entry = input_size.begin();
    config.input_size.height = read_int(*input_size_entry, "input_size[0]");
    ++input_size_entry;
    config.input_size.width = read_int(*input_size_entry, "input_size[1]");

    const cv::FileNode class_names = storage["class_names"];
    config.class_names = class_names.empty() ? frozen_coco80_class_names()
                                             : read_class_names(class_names);

    const cv::FileNode letterbox = storage["letterbox"];
    if (!letterbox.empty()) {
        if (!letterbox.isMap()) {
            throw std::runtime_error("letterbox must be a JSON object");
        }
        const cv::FileNode pad_color = letterbox["pad_color_bgr"];
        if (!pad_color.empty()) {
            if (!pad_color.isSeq() || pad_color.size() != 3U) {
                throw std::runtime_error("letterbox.pad_color_bgr must contain three integers");
            }
            std::size_t index = 0;
            for (const auto& channel : pad_color) {
                config.letterbox.pad_color_bgr[index] =
                    read_int(channel, "letterbox.pad_color_bgr");
                ++index;
            }
        }
        const cv::FileNode interpolation = letterbox["interpolation"];
        if (!interpolation.empty()) {
            if (!interpolation.isString()) {
                throw std::runtime_error("letterbox.interpolation must be a string");
            }
            config.letterbox.interpolation = static_cast<std::string>(interpolation);
        }
    }

    validate_config(config);
    return config;
}

}  // namespace edgeai::common
