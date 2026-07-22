#include "edgeai/backends/ort_detector.hpp"

#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <limits>
#include <sstream>
#include <stdexcept>
#include <utility>

#include <cpu_provider_factory.h>
#include <onnxruntime_cxx_api.h>
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
        std::array<std::uint8_t, 32> digest{};
        for (std::size_t index = 0; index < state_.size(); ++index) {
            digest[index * 4U] = static_cast<std::uint8_t>(state_[index] >> 24U);
            digest[index * 4U + 1U] = static_cast<std::uint8_t>(state_[index] >> 16U);
            digest[index * 4U + 2U] = static_cast<std::uint8_t>(state_[index] >> 8U);
            digest[index * 4U + 3U] = static_cast<std::uint8_t>(state_[index]);
        }
        return digest;
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
        0x6a09e667U,
        0xbb67ae85U,
        0x3c6ef372U,
        0xa54ff53aU,
        0x510e527fU,
        0x9b05688cU,
        0x1f83d9abU,
        0x5be0cd19U,
    }};
    std::array<std::uint8_t, 64> buffer_{};
    std::size_t buffer_size_{0};
    std::uint64_t bit_count_{0};
};

struct ManifestContract {
    std::string model_sha256;
    int class_count{0};
    std::vector<TensorDescriptor> inputs;
    std::vector<TensorDescriptor> outputs;
};

std::vector<std::int64_t> read_shape(const cv::FileNode& node) {
    if (!node.isSeq()) {
        throw std::runtime_error("manifest tensor shape must be an array");
    }
    std::vector<std::int64_t> shape;
    shape.reserve(node.size());
    for (const auto& dimension : node) {
        if (!dimension.isInt()) {
            throw std::runtime_error("manifest tensor shape must contain integers");
        }
        shape.push_back(static_cast<int>(dimension));
    }
    return shape;
}

TensorDescriptor read_descriptor(const cv::FileNode& node) {
    const cv::FileNode name = node["name"];
    const cv::FileNode dtype = node["dtype"];
    const cv::FileNode shape = node["shape"];
    if (!name.isString() || !dtype.isString() || shape.empty()) {
        throw std::runtime_error("manifest tensor descriptor is incomplete");
    }
    return {static_cast<std::string>(name), read_shape(shape), static_cast<std::string>(dtype)};
}

std::vector<TensorDescriptor> read_descriptors(const cv::FileNode& node) {
    if (!node.isSeq()) {
        throw std::runtime_error("manifest inputs/outputs must be arrays");
    }
    std::vector<TensorDescriptor> descriptors;
    descriptors.reserve(node.size());
    for (const auto& descriptor : node) {
        descriptors.push_back(read_descriptor(descriptor));
    }
    return descriptors;
}

ManifestContract load_manifest(const std::filesystem::path& path) {
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("manifest is missing or empty: " + path.string());
    }
    cv::FileStorage storage(path.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON);
    if (!storage.isOpened()) {
        throw std::runtime_error("failed to parse manifest JSON: " + path.string());
    }
    const cv::FileNode onnx = storage["onnx"];
    const cv::FileNode contract = onnx["contract"];
    const cv::FileNode sha256 = onnx["sha256"];
    const cv::FileNode class_count = contract["class_count"];
    const cv::FileNode contains_graph_nms = contract["contains_graph_nms"];
    if (!sha256.isString() || !class_count.isInt() || !contains_graph_nms.isInt()) {
        throw std::runtime_error("manifest ONNX contract is incomplete");
    }
    if (static_cast<int>(contains_graph_nms) != 0) {
        throw std::runtime_error("manifest unexpectedly declares graph NMS");
    }
    return {
        static_cast<std::string>(sha256),
        static_cast<int>(class_count),
        read_descriptors(contract["inputs"]),
        read_descriptors(contract["outputs"]),
    };
}

std::string ort_dtype(ONNXTensorElementDataType type) {
    if (type == ONNX_TENSOR_ELEMENT_DATA_TYPE_FLOAT) {
        return "FLOAT";
    }
    throw std::runtime_error("runtime tensor dtype is not FLOAT");
}

void validate_descriptors(
    const std::vector<TensorDescriptor>& actual,
    const std::vector<TensorDescriptor>& expected,
    const char* kind
) {
    if (actual.size() != expected.size()) {
        throw std::runtime_error(std::string("runtime ") + kind + " count differs from manifest");
    }
    for (std::size_t index = 0; index < actual.size(); ++index) {
        if (actual[index].name != expected[index].name || actual[index].shape != expected[index].shape ||
            actual[index].dtype != expected[index].dtype) {
            throw std::runtime_error(
                std::string("runtime ") + kind + " descriptor differs from manifest at index " +
                std::to_string(index)
            );
        }
    }
}

std::size_t element_count(const std::vector<std::int64_t>& shape) {
    std::size_t count = 1U;
    for (const std::int64_t dimension : shape) {
        if (dimension <= 0) {
            throw std::runtime_error("runtime tensor shape must be fully static and positive");
        }
        const auto converted = static_cast<std::size_t>(dimension);
        if (count > std::numeric_limits<std::size_t>::max() / converted) {
            throw std::runtime_error("runtime tensor element count overflows size_t");
        }
        count *= converted;
    }
    return count;
}

}  // namespace

std::string sha256_file(const std::filesystem::path& path) {
    if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("SHA256 input is missing or empty: " + path.string());
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

struct OrtDetector::Impl {
    Impl(
        const std::filesystem::path& model_path,
        const std::filesystem::path& manifest_path,
        int intra_op_threads,
        int inter_op_threads
    )
        : env(ORT_LOGGING_LEVEL_WARNING, "edgeai_cpp_ort"), session(nullptr) {
        if (intra_op_threads <= 0 || inter_op_threads <= 0) {
            throw std::runtime_error("ORT thread counts must be positive");
        }
        const ManifestContract manifest = load_manifest(manifest_path);
        model_sha = sha256_file(model_path);
        if (model_sha != manifest.model_sha256) {
            throw std::runtime_error(
                "model SHA256 differs from manifest: expected " + manifest.model_sha256 +
                ", observed " + model_sha
            );
        }
        if (manifest.class_count != 80) {
            throw std::runtime_error("manifest class count differs from frozen value 80");
        }
        info.version = OrtGetApiBase()->GetVersionString();
        if (info.version != "1.18.1") {
            throw std::runtime_error("ONNX Runtime version differs from required 1.18.1: " + info.version);
        }
        info.execution_provider = "CPUExecutionProvider";
        info.intra_op_threads = intra_op_threads;
        info.inter_op_threads = inter_op_threads;
        session_options.SetIntraOpNumThreads(intra_op_threads);
        session_options.SetInterOpNumThreads(inter_op_threads);
        session_options.SetExecutionMode(ExecutionMode::ORT_SEQUENTIAL);
        session_options.SetGraphOptimizationLevel(GraphOptimizationLevel::ORT_ENABLE_ALL);
        Ort::ThrowOnError(OrtSessionOptionsAppendExecutionProvider_CPU(session_options, 1));
        session = Ort::Session(env, model_path.c_str(), session_options);

        Ort::AllocatorWithDefaultOptions allocator;
        const std::size_t input_count = session.GetInputCount();
        const std::size_t output_count = session.GetOutputCount();
        info.inputs.reserve(input_count);
        info.outputs.reserve(output_count);
        for (std::size_t index = 0; index < input_count; ++index) {
            const auto name = session.GetInputNameAllocated(index, allocator);
            const auto type_info = session.GetInputTypeInfo(index);
            const auto tensor_info = type_info.GetTensorTypeAndShapeInfo();
            const auto shape = tensor_info.GetShape();
            info.inputs.push_back({name.get(), shape, ort_dtype(tensor_info.GetElementType())});
        }
        for (std::size_t index = 0; index < output_count; ++index) {
            const auto name = session.GetOutputNameAllocated(index, allocator);
            const auto type_info = session.GetOutputTypeInfo(index);
            const auto tensor_info = type_info.GetTensorTypeAndShapeInfo();
            const auto shape = tensor_info.GetShape();
            info.outputs.push_back({name.get(), shape, ort_dtype(tensor_info.GetElementType())});
        }
        validate_descriptors(info.inputs, manifest.inputs, "input");
        validate_descriptors(info.outputs, manifest.outputs, "output");
    }

    RawInferenceResult infer(const edgeai::common::InputTensor& tensor) {
        const std::vector<std::int64_t> input_shape(tensor.shape.begin(), tensor.shape.end());
        if (input_shape != info.inputs.at(0).shape || tensor.values.size() != element_count(input_shape)) {
            throw std::runtime_error("common preprocessing tensor differs from runtime input contract");
        }
        Ort::MemoryInfo memory_info =
            Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
        Ort::Value input = Ort::Value::CreateTensor<float>(
            memory_info,
            const_cast<float*>(tensor.values.data()),
            tensor.values.size(),
            input_shape.data(),
            input_shape.size()
        );
        const char* input_name = info.inputs.at(0).name.c_str();
        const char* output_name = info.outputs.at(0).name.c_str();
        Ort::RunOptions run_options{nullptr};
        auto outputs = session.Run(
            run_options,
            &input_name,
            &input,
            1U,
            &output_name,
            1U
        );
        if (outputs.size() != 1U || !outputs[0].IsTensor()) {
            throw std::runtime_error("ORT did not return exactly one tensor output");
        }
        const auto tensor_info = outputs[0].GetTensorTypeAndShapeInfo();
        const std::vector<std::int64_t> output_shape = tensor_info.GetShape();
        if (output_shape != info.outputs.at(0).shape ||
            ort_dtype(tensor_info.GetElementType()) != info.outputs.at(0).dtype) {
            throw std::runtime_error("ORT output descriptor changed during inference");
        }
        const std::size_t count = tensor_info.GetElementCount();
        if (count != element_count(output_shape)) {
            throw std::runtime_error("ORT output element count differs from output shape");
        }
        const float* output_data = outputs[0].GetTensorData<float>();
        std::vector<float> values(output_data, output_data + count);
        for (const float value : values) {
            if (!std::isfinite(value)) {
                throw std::runtime_error("ORT output contains a non-finite value");
            }
        }
        return {std::move(values), output_shape};
    }

    Ort::Env env;
    Ort::SessionOptions session_options;
    Ort::Session session;
    OrtRuntimeInfo info;
    std::string model_sha;
};

OrtDetector::OrtDetector(
    const std::filesystem::path& model_path,
    const std::filesystem::path& manifest_path,
    int intra_op_threads,
    int inter_op_threads
)
    : impl_(std::make_unique<Impl>(
          model_path,
          manifest_path,
          intra_op_threads,
          inter_op_threads
      )) {}

OrtDetector::~OrtDetector() = default;
OrtDetector::OrtDetector(OrtDetector&&) noexcept = default;
OrtDetector& OrtDetector::operator=(OrtDetector&&) noexcept = default;

const OrtRuntimeInfo& OrtDetector::runtime_info() const {
    return impl_->info;
}

const std::string& OrtDetector::model_sha256() const {
    return impl_->model_sha;
}

RawInferenceResult OrtDetector::infer(const edgeai::common::InputTensor& tensor) {
    return impl_->infer(tensor);
}

}  // namespace edgeai::backends
