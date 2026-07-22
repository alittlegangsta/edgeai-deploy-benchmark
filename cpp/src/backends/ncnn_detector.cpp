#include "edgeai/backends/ncnn_detector.hpp"

#include <net.h>
#include <platform.h>

#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <utility>

#include <opencv2/core/persistence.hpp>

namespace edgeai::backends {
namespace {

class Sha256 {
public:
    void update(const std::uint8_t* data, std::size_t size) {
        for (std::size_t index = 0; index < size; ++index) {
            buffer_[buffer_size_++] = data[index];
            if (buffer_size_ == buffer_.size()) {
                transform();
                bit_count_ += 512U;
                buffer_size_ = 0U;
            }
        }
    }

    std::array<std::uint8_t, 32> finish() {
        bit_count_ += static_cast<std::uint64_t>(buffer_size_) * 8U;
        buffer_[buffer_size_++] = 0x80U;
        if (buffer_size_ > 56U) {
            while (buffer_size_ < 64U) {
                buffer_[buffer_size_++] = 0U;
            }
            transform();
            buffer_size_ = 0U;
        }
        while (buffer_size_ < 56U) {
            buffer_[buffer_size_++] = 0U;
        }
        for (int shift = 56; shift >= 0; shift -= 8) {
            buffer_[buffer_size_++] = static_cast<std::uint8_t>(bit_count_ >> shift);
        }
        transform();
        std::array<std::uint8_t, 32> result{};
        for (std::size_t index = 0; index < state_.size(); ++index) {
            result[index * 4U] = static_cast<std::uint8_t>(state_[index] >> 24U);
            result[index * 4U + 1U] = static_cast<std::uint8_t>(state_[index] >> 16U);
            result[index * 4U + 2U] = static_cast<std::uint8_t>(state_[index] >> 8U);
            result[index * 4U + 3U] = static_cast<std::uint8_t>(state_[index]);
        }
        return result;
    }

private:
    static std::uint32_t rotate_right(std::uint32_t value, std::uint32_t count) {
        return (value >> count) | (value << (32U - count));
    }

    void transform() {
        static constexpr std::array<std::uint32_t, 64> constants{{
            0x428a2f98U, 0x71374491U, 0xb5c0fbcfU, 0xe9b5dba5U, 0x3956c25bU,
            0x59f111f1U, 0x923f82a4U, 0xab1c5ed5U, 0xd807aa98U, 0x12835b01U,
            0x243185beU, 0x550c7dc3U, 0x72be5d74U, 0x80deb1feU, 0x9bdc06a7U,
            0xc19bf174U, 0xe49b69c1U, 0xefbe4786U, 0x0fc19dc6U, 0x240ca1ccU,
            0x2de92c6fU, 0x4a7484aaU, 0x5cb0a9dcU, 0x76f988daU, 0x983e5152U,
            0xa831c66dU, 0xb00327c8U, 0xbf597fc7U, 0xc6e00bf3U, 0xd5a79147U,
            0x06ca6351U, 0x14292967U, 0x27b70a85U, 0x2e1b2138U, 0x4d2c6dfcU,
            0x53380d13U, 0x650a7354U, 0x766a0abbU, 0x81c2c92eU, 0x92722c85U,
            0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U, 0xc76c51a3U, 0xd192e819U,
            0xd6990624U, 0xf40e3585U, 0x106aa070U, 0x19a4c116U, 0x1e376c08U,
            0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U, 0x4ed8aa4aU, 0x5b9cca4fU,
            0x682e6ff3U, 0x748f82eeU, 0x78a5636fU, 0x84c87814U, 0x8cc70208U,
            0x90befffaU, 0xa4506cebU, 0xbef9a3f7U, 0xc67178f2U,
        }};
        std::array<std::uint32_t, 64> words{};
        for (std::size_t index = 0; index < 16U; ++index) {
            words[index] = (static_cast<std::uint32_t>(buffer_[index * 4U]) << 24U) |
                           (static_cast<std::uint32_t>(buffer_[index * 4U + 1U]) << 16U) |
                           (static_cast<std::uint32_t>(buffer_[index * 4U + 2U]) << 8U) |
                           static_cast<std::uint32_t>(buffer_[index * 4U + 3U]);
        }
        for (std::size_t index = 16U; index < words.size(); ++index) {
            const std::uint32_t s0 = rotate_right(words[index - 15U], 7U) ^
                                     rotate_right(words[index - 15U], 18U) ^
                                     (words[index - 15U] >> 3U);
            const std::uint32_t s1 = rotate_right(words[index - 2U], 17U) ^
                                     rotate_right(words[index - 2U], 19U) ^
                                     (words[index - 2U] >> 10U);
            words[index] = words[index - 16U] + s0 + words[index - 7U] + s1;
        }
        std::uint32_t a = state_[0];
        std::uint32_t b = state_[1];
        std::uint32_t c = state_[2];
        std::uint32_t d = state_[3];
        std::uint32_t e = state_[4];
        std::uint32_t f = state_[5];
        std::uint32_t g = state_[6];
        std::uint32_t h = state_[7];
        for (std::size_t index = 0; index < words.size(); ++index) {
            const std::uint32_t sum1 = rotate_right(e, 6U) ^ rotate_right(e, 11U) ^
                                       rotate_right(e, 25U);
            const std::uint32_t choice = (e & f) ^ (~e & g);
            const std::uint32_t temporary1 =
                h + sum1 + choice + constants[index] + words[index];
            const std::uint32_t sum0 = rotate_right(a, 2U) ^ rotate_right(a, 13U) ^
                                       rotate_right(a, 22U);
            const std::uint32_t majority = (a & b) ^ (a & c) ^ (b & c);
            const std::uint32_t temporary2 = sum0 + majority;
            h = g;
            g = f;
            f = e;
            e = d + temporary1;
            d = c;
            c = b;
            b = a;
            a = temporary1 + temporary2;
        }
        state_[0] += a;
        state_[1] += b;
        state_[2] += c;
        state_[3] += d;
        state_[4] += e;
        state_[5] += f;
        state_[6] += g;
        state_[7] += h;
    }

    std::array<std::uint32_t, 8> state_{{
        0x6a09e667U, 0xbb67ae85U, 0x3c6ef372U, 0xa54ff53aU,
        0x510e527fU, 0x9b05688cU, 0x1f83d9abU, 0x5be0cd19U,
    }};
    std::array<std::uint8_t, 64> buffer_{};
    std::size_t buffer_size_{0};
    std::uint64_t bit_count_{0};
};

int required_int(const cv::FileNode& parent, const char* key) {
    const cv::FileNode value = parent[key];
    if (!value.isInt()) {
        throw std::runtime_error(std::string("manifest integer is missing: ") + key);
    }
    return static_cast<int>(value);
}

std::string required_string(const cv::FileNode& parent, const char* key) {
    const cv::FileNode value = parent[key];
    if (!value.isString()) {
        throw std::runtime_error(std::string("manifest string is missing: ") + key);
    }
    return static_cast<std::string>(value);
}

std::vector<std::int64_t> required_shape(const cv::FileNode& parent, const char* key) {
    const cv::FileNode value = parent[key];
    if (!value.isSeq()) {
        throw std::runtime_error(std::string("manifest shape is missing: ") + key);
    }
    std::vector<std::int64_t> result;
    for (const auto& dimension : value) {
        if (!dimension.isInt()) {
            throw std::runtime_error("manifest shape contains a non-integer");
        }
        result.push_back(static_cast<int>(dimension));
    }
    return result;
}

struct ManifestContract {
    std::filesystem::path param_path;
    std::filesystem::path bin_path;
    std::string param_sha256;
    std::string bin_sha256;
    std::string runtime_version;
    NcnnTensorDescriptor input;
    NcnnTensorDescriptor output;
};

std::filesystem::path resolve_manifest_artifact(
    const std::filesystem::path& manifest_path,
    const std::filesystem::path& artifact_path
) {
    if (artifact_path.is_absolute()) {
        return artifact_path;
    }
    std::filesystem::path ancestor = std::filesystem::absolute(manifest_path).parent_path();
    while (!ancestor.empty()) {
        const std::filesystem::path candidate = ancestor / artifact_path;
        if (std::filesystem::is_regular_file(candidate)) {
            return candidate.lexically_normal();
        }
        if (ancestor == ancestor.root_path()) {
            break;
        }
        ancestor = ancestor.parent_path();
    }
    return artifact_path;
}

ManifestContract load_manifest(const std::filesystem::path& path) {
    if (std::filesystem::is_symlink(path) || !std::filesystem::is_regular_file(path) ||
        std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("ncnn manifest is missing, empty, or a symlink: " + path.string());
    }
    cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
    if (!storage.isOpened()) {
        throw std::runtime_error("failed to parse ncnn manifest: " + path.string());
    }
    if (required_int(storage.root(), "schema_version") != 1 ||
        required_string(storage.root(), "status") != "PASS") {
        throw std::runtime_error("ncnn manifest schema/status differs");
    }
    const cv::FileNode toolchain = storage["toolchain"];
    if (required_string(toolchain, "tag") != "20240410" ||
        required_string(toolchain, "revision") !=
            "56775de50990ab7f16627efdcf5529b49541206f") {
        throw std::runtime_error("ncnn toolchain identity differs from Task 010");
    }
    const cv::FileNode ncnn = toolchain["ncnn"];
    const std::string runtime_version = required_string(ncnn, "version");
    const cv::FileNode model = storage["ncnn_model"];
    const cv::FileNode param = model["param"];
    const cv::FileNode bin = model["bin"];
    if (required_int(model, "custom_layer_count") != 0) {
        throw std::runtime_error("ncnn manifest contains custom layers");
    }
    const cv::FileNode contract = storage["contract"];
    if (required_string(contract, "classification") !=
            "single decoded YOLOv5 candidate tensor" ||
        required_int(contract, "batch") != 1 ||
        required_string(contract, "precision") != "FP32" ||
        required_string(contract, "device") != "CPU" ||
        required_int(contract, "contains_graph_nms") != 0 ||
        required_int(contract, "class_count") != 80 ||
        required_int(contract, "attributes_per_candidate") != 85) {
        throw std::runtime_error("ncnn manifest high-level contract differs");
    }
    const cv::FileNode inputs = contract["inputs"];
    const cv::FileNode outputs = contract["outputs"];
    if (!inputs.isSeq() || inputs.size() != 1U || !outputs.isSeq() || outputs.size() != 1U) {
        throw std::runtime_error("ncnn manifest must have one input and one output");
    }
    const cv::FileNode input = inputs[0];
    const cv::FileNode output = outputs[0];
    NcnnTensorDescriptor input_descriptor{
        required_string(input, "name"), required_shape(input, "logical_shape"),
        required_string(input, "dtype"), required_int(input, "ncnn_dims"),
        required_int(input, "w"), required_int(input, "h"), 1, required_int(input, "c"), 1, 32,
    };
    NcnnTensorDescriptor output_descriptor{
        required_string(output, "name"), required_shape(output, "logical_shape"),
        required_string(output, "dtype"), required_int(output, "dims"),
        required_int(output, "w"), required_int(output, "h"), required_int(output, "d"),
        required_int(output, "c"), required_int(output, "elempack"),
        required_int(output, "elembits"),
    };
    if (input_descriptor.name != "in0" ||
        input_descriptor.logical_shape != std::vector<std::int64_t>{1, 3, 640, 640} ||
        input_descriptor.dtype != "float32" || input_descriptor.dims != 3 ||
        input_descriptor.w != 640 || input_descriptor.h != 640 || input_descriptor.c != 3 ||
        output_descriptor.name != "out0" ||
        output_descriptor.logical_shape != std::vector<std::int64_t>{1, 25200, 85} ||
        output_descriptor.dtype != "float32" || output_descriptor.dims != 2 ||
        output_descriptor.w != 85 || output_descriptor.h != 25200 ||
        output_descriptor.elempack != 1 || output_descriptor.elembits != 32) {
        throw std::runtime_error("ncnn tensor/blob contract differs from Task 010");
    }
    return {
        resolve_manifest_artifact(path, required_string(param, "path")),
        resolve_manifest_artifact(path, required_string(bin, "path")),
        required_string(param, "sha256"), required_string(bin, "sha256"),
        runtime_version, std::move(input_descriptor), std::move(output_descriptor),
    };
}

std::size_t element_count(const std::vector<std::int64_t>& shape) {
    std::size_t result = 1U;
    for (const std::int64_t dimension : shape) {
        if (dimension <= 0 || result > std::numeric_limits<std::size_t>::max() /
                                          static_cast<std::size_t>(dimension)) {
            throw std::runtime_error("invalid tensor shape");
        }
        result *= static_cast<std::size_t>(dimension);
    }
    return result;
}

}  // namespace

std::string ncnn_sha256_file(const std::filesystem::path& path) {
    if (std::filesystem::is_symlink(path) || !std::filesystem::is_regular_file(path) ||
        std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("SHA256 input is missing, empty, or a symlink: " + path.string());
    }
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("failed to open SHA256 input: " + path.string());
    }
    Sha256 hash;
    std::array<char, 1024 * 1024> buffer{};
    while (input) {
        input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        const std::streamsize count = input.gcount();
        if (count > 0) {
            hash.update(
                reinterpret_cast<const std::uint8_t*>(buffer.data()),
                static_cast<std::size_t>(count)
            );
        }
    }
    if (!input.eof()) {
        throw std::runtime_error("failed while reading SHA256 input: " + path.string());
    }
    const auto digest = hash.finish();
    std::ostringstream output;
    output << std::hex << std::setfill('0');
    for (const std::uint8_t byte : digest) {
        output << std::setw(2) << static_cast<unsigned int>(byte);
    }
    return output.str();
}

struct NcnnDetector::Impl {
    explicit Impl(const std::filesystem::path& manifest_path, int threads) {
        if (threads != 1) {
            throw std::runtime_error("Task 011 requires exactly one ncnn thread");
        }
        const ManifestContract manifest = load_manifest(manifest_path);
        param = manifest.param_path;
        bin = manifest.bin_path;
        param_sha = ncnn_sha256_file(param);
        bin_sha = ncnn_sha256_file(bin);
        if (param_sha != manifest.param_sha256 || bin_sha != manifest.bin_sha256) {
            throw std::runtime_error("ncnn param/bin SHA256 differs from Task 010 manifest");
        }
        info.version = NCNN_VERSION_STRING;
        if (info.version != manifest.runtime_version || info.version != "1.0.20240410") {
            throw std::runtime_error("ncnn runtime version differs from Task 010 manifest");
        }
        info.threads = threads;
        info.inputs = {manifest.input};
        info.outputs = {manifest.output};
        network.opt.num_threads = threads;
        network.opt.use_vulkan_compute = false;
        network.opt.use_fp16_packed = false;
        network.opt.use_fp16_storage = false;
        network.opt.use_fp16_arithmetic = false;
        network.opt.use_bf16_storage = false;
        network.opt.use_int8_inference = false;
        network.opt.use_int8_packed = false;
        network.opt.use_int8_storage = false;
        network.opt.use_int8_arithmetic = false;
        const int param_status = network.load_param(param.string().c_str());
        const int bin_status = param_status == 0 ? network.load_model(bin.string().c_str()) : -1;
        if (param_status != 0 || bin_status != 0) {
            throw std::runtime_error(
                "ncnn model load failed: param=" + std::to_string(param_status) +
                " bin=" + std::to_string(bin_status)
            );
        }
        const auto input_names = network.input_names();
        const auto output_names = network.output_names();
        if (input_names.size() != 1U || output_names.size() != 1U ||
            std::string(input_names[0]) != info.inputs[0].name ||
            std::string(output_names[0]) != info.outputs[0].name) {
            throw std::runtime_error("ncnn runtime blob names differ from Task 010 manifest");
        }
    }

    NcnnRawInferenceResult infer(const edgeai::common::InputTensor& tensor) {
        const auto& input_contract = info.inputs.at(0);
        if (std::vector<std::int64_t>(tensor.shape.begin(), tensor.shape.end()) !=
                input_contract.logical_shape ||
            tensor.values.size() != element_count(input_contract.logical_shape)) {
            throw std::runtime_error("common tensor differs from ncnn input contract");
        }
        for (const float value : tensor.values) {
            if (!std::isfinite(value)) {
                throw std::runtime_error("ncnn input contains a non-finite value");
            }
        }
        ncnn::Mat input(
            input_contract.w,
            input_contract.h,
            input_contract.c,
            const_cast<float*>(tensor.values.data()),
            sizeof(float),
            1
        );
        ncnn::Extractor extractor = network.create_extractor();
        const int input_status = extractor.input(input_contract.name.c_str(), input);
        if (input_status != 0) {
            throw std::runtime_error("ncnn input binding failed: " + std::to_string(input_status));
        }
        ncnn::Mat output;
        const auto& output_contract = info.outputs.at(0);
        const int output_status = extractor.extract(output_contract.name.c_str(), output);
        if (output_status != 0) {
            throw std::runtime_error("ncnn output extraction failed: " + std::to_string(output_status));
        }
        if (output.dims != output_contract.dims || output.w != output_contract.w ||
            output.h != output_contract.h || output.d != output_contract.d ||
            output.c != output_contract.c || output.elempack != output_contract.elempack ||
            output.elembits() != output_contract.elembits) {
            throw std::runtime_error("ncnn inference output layout differs from Task 010 manifest");
        }
        const std::size_t count = output.total() * static_cast<std::size_t>(output.elempack);
        if (count != element_count(output_contract.logical_shape)) {
            throw std::runtime_error("ncnn output scalar count differs from logical shape");
        }
        const float* values = static_cast<const float*>(output.data);
        std::vector<float> copied(values, values + count);
        for (const float value : copied) {
            if (!std::isfinite(value)) {
                throw std::runtime_error("ncnn output contains a non-finite value");
            }
        }
        return {std::move(copied), output_contract.logical_shape};
    }

    ncnn::Net network;
    NcnnRuntimeInfo info;
    std::filesystem::path param;
    std::filesystem::path bin;
    std::string param_sha;
    std::string bin_sha;
};

NcnnDetector::NcnnDetector(const std::filesystem::path& manifest_path, int threads)
    : impl_(std::make_unique<Impl>(manifest_path, threads)) {}

NcnnDetector::~NcnnDetector() = default;
NcnnDetector::NcnnDetector(NcnnDetector&&) noexcept = default;
NcnnDetector& NcnnDetector::operator=(NcnnDetector&&) noexcept = default;

const NcnnRuntimeInfo& NcnnDetector::runtime_info() const { return impl_->info; }
const std::filesystem::path& NcnnDetector::param_path() const { return impl_->param; }
const std::filesystem::path& NcnnDetector::bin_path() const { return impl_->bin; }
const std::string& NcnnDetector::param_sha256() const { return impl_->param_sha; }
const std::string& NcnnDetector::bin_sha256() const { return impl_->bin_sha; }
NcnnRawInferenceResult NcnnDetector::infer(const edgeai::common::InputTensor& tensor) {
    return impl_->infer(tensor);
}

}  // namespace edgeai::backends
