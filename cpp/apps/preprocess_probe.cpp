#include "edgeai/common/config.hpp"
#include "edgeai/common/preprocess.hpp"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

namespace {

std::string json_escape(const std::string& value) {
    std::string escaped;
    escaped.reserve(value.size());
    for (const char character : value) {
        switch (character) {
            case '\\':
                escaped += "\\\\";
                break;
            case '"':
                escaped += "\\\"";
                break;
            case '\n':
                escaped += "\\n";
                break;
            case '\r':
                escaped += "\\r";
                break;
            case '\t':
                escaped += "\\t";
                break;
            default:
                escaped += character;
                break;
        }
    }
    return escaped;
}

std::map<std::string, std::filesystem::path> parse_args(int argc, char* argv[]) {
    if (argc != 9) {
        throw std::runtime_error(
            "usage: edgeai_preprocess_probe --config PATH --image PATH "
            "--metadata PATH --tensor PATH"
        );
    }
    std::map<std::string, std::filesystem::path> values;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        if (option != "--config" && option != "--image" && option != "--metadata" &&
            option != "--tensor") {
            throw std::runtime_error("unknown argument: " + option);
        }
        if (!values.emplace(option, argv[index + 1]).second) {
            throw std::runtime_error("duplicate argument: " + option);
        }
    }
    if (values.size() != 4U) {
        throw std::runtime_error("all four named arguments are required");
    }
    return values;
}

void write_tensor(const std::filesystem::path& path, const edgeai::common::InputTensor& tensor) {
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path());
    }
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) {
        throw std::runtime_error("failed to open tensor output: " + path.string());
    }
    const auto byte_count = static_cast<std::streamsize>(tensor.values.size() * sizeof(float));
    output.write(reinterpret_cast<const char*>(tensor.values.data()), byte_count);
    output.close();
    if (!output || !std::filesystem::is_regular_file(path) ||
        std::filesystem::file_size(path) != static_cast<std::uintmax_t>(byte_count)) {
        throw std::runtime_error("failed to write complete tensor output: " + path.string());
    }
}

void write_metadata(
    const std::filesystem::path& path,
    const std::filesystem::path& config_path,
    const std::filesystem::path& image_path,
    const edgeai::common::InferenceConfig& config,
    const edgeai::common::PreprocessResult& result
) {
    if (!path.parent_path().empty()) {
        std::filesystem::create_directories(path.parent_path());
    }
    std::ofstream output(path, std::ios::trunc);
    if (!output) {
        throw std::runtime_error("failed to open metadata output: " + path.string());
    }
    const auto& metadata = result.metadata;
    const bool all_finite = std::all_of(
        result.tensor.values.begin(),
        result.tensor.values.end(),
        [](float value) { return std::isfinite(value); }
    );
    output << std::setprecision(17);
    output << "{\n"
           << "  \"application\": \"edgeai_preprocess_probe\",\n"
           << "  \"schema_version\": 1,\n"
           << "  \"config_path\": \"" << json_escape(config_path.string()) << "\",\n"
           << "  \"image_path\": \"" << json_escape(image_path.string()) << "\",\n"
           << "  \"class_name_count\": " << config.class_names.size() << ",\n"
           << "  \"input_tensor\": {\n"
           << "    \"dtype\": \"float32\",\n"
           << "    \"shape\": [" << result.tensor.shape[0] << ", " << result.tensor.shape[1]
           << ", " << result.tensor.shape[2] << ", " << result.tensor.shape[3] << "],\n"
           << "    \"element_count\": " << result.tensor.values.size() << ",\n"
           << "    \"all_finite\": " << (all_finite ? "true" : "false") << "\n"
           << "  },\n"
           << "  \"preprocess\": {\n"
           << "    \"original_size\": {\"width\": " << metadata.original_size.width
           << ", \"height\": " << metadata.original_size.height << "},\n"
           << "    \"target_size\": {\"width\": " << metadata.target_size.width
           << ", \"height\": " << metadata.target_size.height << "},\n"
           << "    \"scale\": " << metadata.scale << ",\n"
           << "    \"resized_size\": {\"width\": " << metadata.resized_size.width
           << ", \"height\": " << metadata.resized_size.height << "},\n"
           << "    \"padding\": {\"left\": " << metadata.padding.left
           << ", \"top\": " << metadata.padding.top << ", \"right\": "
           << metadata.padding.right << ", \"bottom\": " << metadata.padding.bottom << "},\n"
           << "    \"pad_color_bgr\": [" << metadata.pad_color_bgr[0] << ", "
           << metadata.pad_color_bgr[1] << ", " << metadata.pad_color_bgr[2] << "],\n"
           << "    \"interpolation\": \"" << json_escape(metadata.interpolation) << "\",\n"
           << "    \"transforms\": [";
    for (std::size_t index = 0; index < metadata.transforms.size(); ++index) {
        if (index != 0U) {
            output << ", ";
        }
        output << '"' << json_escape(metadata.transforms[index]) << '"';
    }
    output << "]\n  }\n}\n";
    output.close();
    if (!output || !std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("failed to write metadata output: " + path.string());
    }
}

}  // namespace

int main(int argc, char* argv[]) {
    try {
        const auto arguments = parse_args(argc, argv);
        const auto config = edgeai::common::load_config(arguments.at("--config"));
        const cv::Mat image = edgeai::common::load_bgr_image(arguments.at("--image"));
        const auto result = edgeai::common::preprocess_image(image, config);
        write_tensor(arguments.at("--tensor"), result.tensor);
        write_metadata(
            arguments.at("--metadata"),
            arguments.at("--config"),
            arguments.at("--image"),
            config,
            result
        );
        std::cout << "Application: edgeai_preprocess_probe\n"
                  << "Tensor shape: [" << result.tensor.shape[0] << ", "
                  << result.tensor.shape[1] << ", " << result.tensor.shape[2] << ", "
                  << result.tensor.shape[3] << "]\n"
                  << "Letterbox scale: " << result.metadata.scale << "\n"
                  << "Letterbox padding: left=" << result.metadata.padding.left
                  << " top=" << result.metadata.padding.top
                  << " right=" << result.metadata.padding.right
                  << " bottom=" << result.metadata.padding.bottom << '\n'
                  << "Metadata: " << arguments.at("--metadata") << '\n'
                  << "Tensor: " << arguments.at("--tensor") << '\n';
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "edgeai_preprocess_probe error: " << error.what() << '\n';
        return 1;
    }
}
