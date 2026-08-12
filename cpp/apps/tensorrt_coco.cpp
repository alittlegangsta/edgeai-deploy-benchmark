#include "edgeai/backends/tensorrt_detector.hpp"
#include "edgeai/common/config.hpp"
#include "edgeai/common/postprocess.hpp"
#include "edgeai/common/preprocess.hpp"

#include <opencv2/imgcodecs.hpp>

#include <algorithm>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct Args {
    std::filesystem::path engine;
    std::filesystem::path config;
    std::filesystem::path images_dir;
    std::filesystem::path manifest;
    std::filesystem::path output;
    double confidence{0.001};
    double iou{0.6};
    int max_detections{100};
    int limit{0};
};

struct ImageRow {
    int image_id{0};
    std::string file_name;
    int width{0};
    int height{0};
};

const std::vector<int>& coco_category_ids() {
    static const std::vector<int> ids{
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19,
        20, 21, 22, 23, 24, 25, 27, 28, 31, 32, 33, 34, 35, 36, 37, 38,
        39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55,
        56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 70, 72, 73, 74, 75,
        76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 88, 89, 90,
    };
    return ids;
}

Args parse_args(int argc, char* argv[]) {
    if ((argc - 1) % 2 != 0) {
        throw std::runtime_error("arguments must be option/value pairs");
    }
    std::map<std::string, std::string> values;
    for (int index = 1; index < argc; index += 2) {
        const std::string key = argv[index];
        if (key != "--engine" && key != "--config" && key != "--images-dir" &&
            key != "--manifest" && key != "--output" && key != "--confidence" &&
            key != "--iou" && key != "--max-det" && key != "--limit") {
            throw std::runtime_error("unknown argument: " + key);
        }
        if (!values.emplace(key, argv[index + 1]).second) {
            throw std::runtime_error("duplicate argument: " + key);
        }
    }
    for (const char* required : {"--engine", "--config", "--images-dir", "--manifest", "--output"}) {
        if (values.find(required) == values.end()) {
            throw std::runtime_error(std::string("missing required argument: ") + required);
        }
    }
    Args args{values.at("--engine"), values.at("--config"), values.at("--images-dir"),
              values.at("--manifest"), values.at("--output")};
    if (values.count("--confidence")) args.confidence = std::stod(values.at("--confidence"));
    if (values.count("--iou")) args.iou = std::stod(values.at("--iou"));
    if (values.count("--max-det")) args.max_detections = std::stoi(values.at("--max-det"));
    if (values.count("--limit")) args.limit = std::stoi(values.at("--limit"));
    if (args.confidence < 0.0 || args.confidence > 1.0 || args.iou < 0.0 || args.iou > 1.0 ||
        args.max_detections <= 0 || args.limit < 0) {
        throw std::runtime_error("invalid evaluation configuration");
    }
    return args;
}

std::vector<ImageRow> read_manifest(const std::filesystem::path& path, int limit) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("failed to open manifest: " + path.string());
    std::vector<ImageRow> rows;
    std::string line;
    while (std::getline(input, line)) {
        if (line.empty()) continue;
        std::istringstream fields(line);
        std::string id;
        std::string width;
        std::string height;
        ImageRow row;
        if (!std::getline(fields, id, '\t') || !std::getline(fields, row.file_name, '\t') ||
            !std::getline(fields, width, '\t') || !std::getline(fields, height)) {
            throw std::runtime_error("malformed manifest line: " + line);
        }
        row.image_id = std::stoi(id);
        row.width = std::stoi(width);
        row.height = std::stoi(height);
        rows.push_back(row);
        if (limit > 0 && static_cast<int>(rows.size()) >= limit) break;
    }
    if (rows.empty()) throw std::runtime_error("manifest is empty");
    return rows;
}

void write_box(std::ofstream& output, const edgeai::common::Box& box) {
    output << "[" << box.x1 << "," << box.y1 << "," << (box.x2 - box.x1) << ","
           << (box.y2 - box.y1) << "]";
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const Args args = parse_args(argc, argv);
        auto config = edgeai::common::load_config(args.config);
        config.confidence_threshold = args.confidence;
        config.iou_threshold = args.iou;
        config.max_detections = args.max_detections;
        edgeai::common::validate_config(config);
        const auto rows = read_manifest(args.manifest, args.limit);
        if (coco_category_ids().size() != config.class_names.size()) {
            throw std::runtime_error("COCO category mapping does not match model classes");
        }
        edgeai::backends::TensorRtDetector detector(args.engine);
        if (!std::filesystem::exists(args.output.parent_path())) {
            std::filesystem::create_directories(args.output.parent_path());
        }
        std::ofstream output(args.output);
        if (!output) throw std::runtime_error("failed to open prediction output");
        output << std::setprecision(9) << "[";
        bool first_prediction = true;
        std::size_t prediction_count = 0;
        std::size_t zero_detection_images = 0;
        for (std::size_t index = 0; index < rows.size(); ++index) {
            const auto& row = rows[index];
            const auto image = edgeai::common::load_bgr_image(args.images_dir / row.file_name);
            const auto preprocessed = edgeai::common::preprocess_image(image, config);
            const auto raw = detector.infer(preprocessed.tensor);
            const auto postprocessed = edgeai::common::decode_yolov5_output(
                raw.values, raw.shape, config.class_names, preprocessed.metadata, config
            );
            if (postprocessed.detections.empty()) ++zero_detection_images;
            for (const auto& detection : postprocessed.detections) {
                ++prediction_count;
                if (!first_prediction) output << ",";
                first_prediction = false;
                output << "{\"image_id\":" << row.image_id << ",\"category_id\":"
                       << coco_category_ids().at(static_cast<std::size_t>(detection.class_id))
                       << ",\"bbox\":";
                write_box(output, detection.box_xyxy_source);
                output << ",\"score\":" << detection.confidence << "}";
            }
            if ((index + 1) % 250 == 0 || index + 1 == rows.size()) {
                std::cerr << "processed=" << (index + 1) << "/" << rows.size()
                          << " predictions=" << prediction_count << "\n";
            }
        }
        output << "]\n";
        output.close();
        std::cout << "processed_images=" << rows.size() << "\n";
        std::cout << "predictions=" << prediction_count << "\n";
        std::cout << "zero_detection_images=" << zero_detection_images << "\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_tensorrt_coco: " << error.what() << "\n";
        return 1;
    }
}
