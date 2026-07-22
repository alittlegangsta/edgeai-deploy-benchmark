#include <net.h>
#include <platform.h>

#include <cmath>
#include <cstddef>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct Arguments {
    std::filesystem::path param;
    std::filesystem::path bin;
    std::filesystem::path output;
};

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

Arguments parse_arguments(const int argc, char* argv[]) {
    if (argc != 7) {
        throw std::runtime_error(
            "usage: edgeai_ncnn_model_smoke --param MODEL.param --bin MODEL.bin "
            "--output EVIDENCE.json");
    }

    Arguments arguments;
    for (int index = 1; index < argc; index += 2) {
        const std::string option = argv[index];
        const std::filesystem::path value = argv[index + 1];
        if (option == "--param") {
            arguments.param = value;
        } else if (option == "--bin") {
            arguments.bin = value;
        } else if (option == "--output") {
            arguments.output = value;
        } else {
            throw std::runtime_error("unknown argument: " + option);
        }
    }
    if (arguments.param.empty() || arguments.bin.empty() || arguments.output.empty()) {
        throw std::runtime_error("--param, --bin, and --output are all required");
    }
    return arguments;
}

void require_model_file(const std::filesystem::path& path, const std::string& label) {
    if (std::filesystem::is_symlink(path) || !std::filesystem::is_regular_file(path)) {
        throw std::runtime_error(label + " is not a regular non-symlink file: " + path.string());
    }
    if (std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error(label + " is empty: " + path.string());
    }
}

std::vector<std::string> names_to_strings(const std::vector<const char*>& names) {
    std::vector<std::string> result;
    result.reserve(names.size());
    for (const char* name : names) {
        if (name == nullptr || *name == '\0') {
            throw std::runtime_error("ncnn reported an empty blob name");
        }
        result.emplace_back(name);
    }
    return result;
}

void write_names(std::ostream& stream, const std::vector<std::string>& names) {
    stream << '[';
    for (std::size_t index = 0; index < names.size(); ++index) {
        if (index != 0U) {
            stream << ", ";
        }
        stream << '"' << json_escape(names[index]) << '"';
    }
    stream << ']';
}

std::size_t scalar_count(const ncnn::Mat& value) {
    return value.total() * static_cast<std::size_t>(value.elempack);
}

void require_finite_fp32(const ncnn::Mat& value, const std::string& name) {
    if (value.empty()) {
        throw std::runtime_error("ncnn output is empty: " + name);
    }
    if (value.elembits() != 32) {
        throw std::runtime_error("ncnn output is not 32-bit: " + name);
    }
    const float* values = static_cast<const float*>(value.data);
    for (std::size_t index = 0; index < scalar_count(value); ++index) {
        if (!std::isfinite(values[index])) {
            throw std::runtime_error("ncnn output contains a non-finite value: " + name);
        }
    }
}

void write_output_metadata(
    std::ostream& stream,
    const std::string& name,
    const ncnn::Mat& value) {
    stream << "      {\n"
           << "        \"name\": \"" << json_escape(name) << "\",\n"
           << "        \"dims\": " << value.dims << ",\n"
           << "        \"w\": " << value.w << ",\n"
           << "        \"h\": " << value.h << ",\n"
           << "        \"d\": " << value.d << ",\n"
           << "        \"c\": " << value.c << ",\n"
           << "        \"elempack\": " << value.elempack << ",\n"
           << "        \"elembits\": " << value.elembits() << ",\n"
           << "        \"dtype\": \"float32\",\n"
           << "        \"scalar_count\": " << scalar_count(value) << ",\n"
           << "        \"all_finite\": true\n"
           << "      }";
}

int run(const Arguments& arguments) {
    require_model_file(arguments.param, "ncnn param");
    require_model_file(arguments.bin, "ncnn bin");

    ncnn::Net network;
    network.opt.num_threads = 1;
    network.opt.use_vulkan_compute = false;
    network.opt.use_fp16_packed = false;
    network.opt.use_fp16_storage = false;
    network.opt.use_fp16_arithmetic = false;
    network.opt.use_bf16_storage = false;
    network.opt.use_int8_inference = false;
    network.opt.use_int8_packed = false;
    network.opt.use_int8_storage = false;
    network.opt.use_int8_arithmetic = false;

    const int param_status = network.load_param(arguments.param.string().c_str());
    if (param_status != 0) {
        throw std::runtime_error("ncnn load_param failed with status " + std::to_string(param_status));
    }
    const int model_status = network.load_model(arguments.bin.string().c_str());
    if (model_status != 0) {
        throw std::runtime_error("ncnn load_model failed with status " + std::to_string(model_status));
    }

    const std::vector<std::string> input_names = names_to_strings(network.input_names());
    const std::vector<std::string> output_names = names_to_strings(network.output_names());
    if (input_names.size() != 1U || output_names.empty()) {
        throw std::runtime_error(
            "expected one input and at least one output, observed inputs="
            + std::to_string(input_names.size()) + " outputs="
            + std::to_string(output_names.size()));
    }

    ncnn::Mat input(640, 640, 3);
    if (input.empty() || input.elembits() != 32 || input.elempack != 1) {
        throw std::runtime_error("failed to allocate the FP32 3x640x640 contract probe");
    }
    input.fill(0.0F);
    ncnn::Extractor extractor = network.create_extractor();
    const int input_status = extractor.input(input_names[0].c_str(), input);
    if (input_status != 0) {
        throw std::runtime_error("ncnn extractor input failed with status " + std::to_string(input_status));
    }

    std::vector<ncnn::Mat> outputs;
    outputs.reserve(output_names.size());
    for (const std::string& output_name : output_names) {
        ncnn::Mat output;
        const int extract_status = extractor.extract(output_name.c_str(), output);
        if (extract_status != 0) {
            throw std::runtime_error(
                "ncnn extractor output failed for " + output_name + " with status "
                + std::to_string(extract_status));
        }
        require_finite_fp32(output, output_name);
        outputs.push_back(output);
    }

    const std::filesystem::path parent = arguments.output.parent_path();
    if (!parent.empty()) {
        std::filesystem::create_directories(parent);
    }
    std::ofstream evidence(arguments.output);
    if (!evidence) {
        throw std::runtime_error("failed to open evidence path: " + arguments.output.string());
    }
    evidence << "{\n"
             << "  \"schema_version\": 1,\n"
             << "  \"application\": \"edgeai_ncnn_model_smoke\",\n"
             << "  \"ncnn_version\": \"" << NCNN_VERSION_STRING << "\",\n"
             << "  \"param_path\": \"" << json_escape(arguments.param.string()) << "\",\n"
             << "  \"bin_path\": \"" << json_escape(arguments.bin.string()) << "\",\n"
             << "  \"load_param_status\": " << param_status << ",\n"
             << "  \"load_model_status\": " << model_status << ",\n"
             << "  \"input_names\": ";
    write_names(evidence, input_names);
    evidence << ",\n  \"output_names\": ";
    write_names(evidence, output_names);
    evidence << ",\n"
             << "  \"probe\": {\n"
             << "    \"purpose\": \"zero-input shape/type/load contract probe; not a correctness result\",\n"
             << "    \"input_shape_ncnn_chw\": [3, 640, 640],\n"
             << "    \"input_dtype\": \"float32\",\n"
             << "    \"outputs\": [\n";
    for (std::size_t index = 0; index < outputs.size(); ++index) {
        if (index != 0U) {
            evidence << ",\n";
        }
        write_output_metadata(evidence, output_names[index], outputs[index]);
    }
    evidence << "\n    ]\n"
             << "  },\n"
             << "  \"options\": {\n"
             << "    \"num_threads\": 1,\n"
             << "    \"vulkan_compute\": false,\n"
             << "    \"fp16_packed\": false,\n"
             << "    \"fp16_storage\": false,\n"
             << "    \"fp16_arithmetic\": false,\n"
             << "    \"bf16_storage\": false,\n"
             << "    \"int8_inference\": false,\n"
             << "    \"int8_packed\": false,\n"
             << "    \"int8_storage\": false,\n"
             << "    \"int8_arithmetic\": false\n"
             << "  },\n"
             << "  \"status\": \"PASS\"\n"
             << "}\n";
    evidence.close();
    if (!evidence) {
        throw std::runtime_error("failed while writing evidence: " + arguments.output.string());
    }

    std::cout << "Application: edgeai_ncnn_model_smoke\n"
              << "ncnn version: " << NCNN_VERSION_STRING << '\n'
              << "Input blob: " << input_names[0] << '\n'
              << "Output blobs: " << output_names.size() << '\n';
    for (std::size_t index = 0; index < outputs.size(); ++index) {
        std::cout << "Output " << output_names[index] << ": dims=" << outputs[index].dims
                  << " w=" << outputs[index].w << " h=" << outputs[index].h
                  << " d=" << outputs[index].d << " c=" << outputs[index].c
                  << " elembits=" << outputs[index].elembits() << '\n';
    }
    std::cout << "Model load and contract probe: PASS\n";
    return 0;
}

} // namespace

int main(int argc, char* argv[]) {
    try {
        return run(parse_arguments(argc, argv));
    } catch (const std::exception& error) {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }
}
