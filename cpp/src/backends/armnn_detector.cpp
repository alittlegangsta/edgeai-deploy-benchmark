#include "edgeai/backends/armnn_detector.hpp"

#include <armnn/ArmNN.hpp>
#include <armnnALUtils/cma_mem_init.hpp>
#include <armnnOnnxParser/IOnnxParser.hpp>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <utility>

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
            0xa2bfe8a1U, 0xa81a664bU, 0xc24b8b70U,
            0xc76c51a3U, 0xd192e819U, 0xd6990624U, 0xf40e3585U, 0x106aa070U,
            0x19a4c116U, 0x1e376c08U, 0x2748774cU, 0x34b0bcb5U, 0x391c0cb3U,
            0x4ed8aa4aU, 0x5b9cca4fU, 0x682e6ff3U, 0x748f82eeU, 0x78a5636fU,
            0x84c87814U, 0x8cc70208U, 0x90befffaU, 0xa4506cebU, 0xbef9a3f7U,
            0xc67178f2U,
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

std::vector<std::int64_t> shape_of(const armnn::TensorShape& shape) {
    std::vector<std::int64_t> result;
    result.reserve(shape.GetNumDimensions());
    for (unsigned int index = 0; index < shape.GetNumDimensions(); ++index) {
        result.push_back(static_cast<std::int64_t>(shape[index]));
    }
    return result;
}

const char* dtype_name(armnn::DataType type) {
    switch (type) {
        case armnn::DataType::Float16: return "float16";
        case armnn::DataType::Float32: return "float32";
        case armnn::DataType::QAsymmU8: return "uint8";
        case armnn::DataType::Signed32: return "int32";
        case armnn::DataType::Boolean: return "bool";
        case armnn::DataType::QSymmS16: return "qint16";
        case armnn::DataType::QSymmS8: return "qint8";
        case armnn::DataType::QAsymmS8: return "qint8_asymm";
        case armnn::DataType::BFloat16: return "bfloat16";
        case armnn::DataType::Signed64: return "int64";
    }
    return "unknown";
}

ArmnnTensorDescriptor descriptor(
    const std::string& name,
    const armnn::TensorInfo& info
) {
    return {
        name,
        shape_of(info.GetShape()),
        dtype_name(info.GetDataType()),
        info.GetNumBytes(),
        info.GetQuantizationScale(),
        info.GetQuantizationOffset(),
    };
}

std::string join_messages(const std::vector<std::string>& messages) {
    std::ostringstream result;
    for (std::size_t index = 0; index < messages.size(); ++index) {
        if (index != 0U) {
            result << " | ";
        }
        result << messages[index];
    }
    return result.str();
}

class CmaScope {
public:
    CmaScope() {
        if (cma_mem_init() != 0) {
            throw std::runtime_error("cma_mem_init failed; /dev/cma_mem is unavailable");
        }
    }
    ~CmaScope() { cma_mem_deinit(); }
    CmaScope(const CmaScope&) = delete;
    CmaScope& operator=(const CmaScope&) = delete;
};

class CmaBuffer {
public:
    explicit CmaBuffer(std::size_t bytes) {
        if (bytes == 0U || bytes > std::numeric_limits<std::uint32_t>::max()) {
            throw std::runtime_error("invalid CMA tensor size");
        }
        buffer_ = cma_buffer_t(static_cast<std::uint32_t>(bytes));
        if (cma_mem_alloc(&buffer_) != 0 || buffer_.virt_addr == nullptr || buffer_.phys_addr == 0U) {
            throw std::runtime_error("cma_mem_alloc failed for tensor buffer");
        }
    }
    ~CmaBuffer() {
        if (buffer_.virt_addr != nullptr) {
            cma_mem_free(&buffer_);
        }
    }
    CmaBuffer(const CmaBuffer&) = delete;
    CmaBuffer& operator=(const CmaBuffer&) = delete;
    void* data() const { return buffer_.virt_addr; }
    cma_buffer_t& raw() { return buffer_; }

private:
    cma_buffer_t buffer_{};
};

bool contains_backend(const armnn::BackendIdSet& backends, const char* wanted) {
    return backends.find(armnn::BackendId(wanted)) != backends.end();
}

}  // namespace

std::string armnn_sha256_file(const edgeai::filesystem::path& path) {
    if (edgeai::filesystem::is_symlink(path) ||
        !edgeai::filesystem::is_regular_file(path) ||
        edgeai::filesystem::file_size(path) == 0U) {
        throw std::runtime_error("SHA256 input is missing, empty, or a symlink: " + path.string());
    }
    std::ifstream input(path.string(), std::ios::binary);
    if (!input) {
        throw std::runtime_error("failed to open SHA256 input: " + path.string());
    }
    Sha256 hash;
    std::array<char, 1024 * 1024> buffer{};
    while (input) {
        input.read(buffer.data(), static_cast<std::streamsize>(buffer.size()));
        const std::streamsize count = input.gcount();
        if (count > 0) {
            hash.update(reinterpret_cast<const std::uint8_t*>(buffer.data()),
                        static_cast<std::size_t>(count));
        }
    }
    if (!input.eof()) {
        throw std::runtime_error("failed while reading SHA256 input");
    }
    const auto digest = hash.finish();
    std::ostringstream result;
    result << std::hex << std::setfill('0');
    for (const std::uint8_t byte : digest) {
        result << std::setw(2) << static_cast<unsigned int>(byte);
    }
    return result.str();
}

struct ArmnnDetector::Impl {
    explicit Impl(const edgeai::filesystem::path& model)
        : model_path(model), model_sha256(armnn_sha256_file(model)), cma_scope() {
        armnn::ConfigureLogging(true, false, armnn::LogSeverity::Info);
        parser = armnnOnnxParser::IOnnxParser::Create();
        if (!parser) {
            throw std::runtime_error("ArmNN OnnxParser creation returned null");
        }
        std::cerr << "armnn_stage=parser_created\n";
        network = parser->CreateNetworkFromBinaryFile(model.string().c_str());
        if (!network) {
            throw std::runtime_error("ArmNN OnnxParser returned a null network");
        }
        std::cerr << "armnn_stage=network_parsed\n";

        const auto input_names = parser->GetInputTensorNames();
        const auto output_names = parser->GetOutputTensorNames();
        if (input_names.size() != 1U || output_names.empty()) {
            throw std::runtime_error("ArmNN model must expose exactly one input and at least one output");
        }
        input_name = input_names.front();
        const auto input_binding = parser->GetNetworkInputBindingInfo(input_name);
        input_binding_id = input_binding.first;
        input_info = input_binding.second;
        input_info.SetConstant(true);

        runtime_info.version = armnn::GetVersion();
        runtime_info.input = descriptor(input_name, input_info);
        for (const auto& name : output_names) {
            const auto binding = parser->GetNetworkOutputBindingInfo(name);
            output_binding_ids.push_back(binding.first);
            output_names_.push_back(name);
            output_infos.push_back(binding.second);
            runtime_info.outputs.push_back(descriptor(name, binding.second));
        }
        output_name = output_names_.front();
        output_info = output_infos.front();
        runtime_info.output = runtime_info.outputs.front();

        armnn::IRuntime::CreationOptions runtime_options;
        runtime = armnn::IRuntime::Create(runtime_options);
        if (!runtime) {
            throw std::runtime_error("ArmNN runtime creation returned null");
        }
        const auto& supported = runtime->GetDeviceSpec().GetSupportedBackends();
        runtime_info.requested_backend_registered = contains_backend(supported, "Alnpu");
        for (const auto& backend : supported) {
            runtime_info.supported_backends.push_back(backend.Get());
        }
        if (!runtime_info.requested_backend_registered) {
            throw std::runtime_error(
                "Alnpu backend is not registered; supported backends=" +
                join_messages(runtime_info.supported_backends)
            );
        }

        const std::vector<armnn::BackendId> backends{armnn::BackendId("Alnpu")};
        armnn::OptimizerOptionsOpaque optimizer_options;
        optimizer_options.SetImportEnabled(true);
        optimizer_options.SetExportEnabled(true);
        std::vector<std::string> messages;
        std::cerr << "armnn_stage=optimize_begin backend=Alnpu\n";
        try {
            optimized_network = armnn::Optimize(
                *network,
                backends,
                runtime->GetDeviceSpec(),
                optimizer_options,
                armnn::Optional<std::vector<std::string>&>(messages)
            );
        } catch (const std::exception& error) {
            runtime_info.optimizer_messages = messages;
            throw std::runtime_error(
                std::string("Alnpu optimization failed: ") + error.what() +
                (messages.empty() ? std::string{} : "; messages=" + join_messages(messages))
            );
        }
        runtime_info.optimizer_messages = messages;
        std::cerr << "armnn_stage=optimize_complete\n";
        if (!optimized_network) {
            throw std::runtime_error(
                "Alnpu optimization returned null" +
                (messages.empty() ? std::string{} : "; messages=" + join_messages(messages))
            );
        }

        const armnn::INetworkProperties properties(
            false, armnn::MemorySource::Malloc, armnn::MemorySource::Malloc);
        std::string load_error;
        std::cerr << "armnn_stage=load_begin\n";
        const armnn::Status load_status = runtime->LoadNetwork(
            network_id, std::move(optimized_network), load_error, properties);
        runtime_info.load_status = load_status == armnn::Status::Success ? "Success" : "Failure";
        runtime_info.load_error = load_error;
        std::cerr << "armnn_stage=load_complete status=" << runtime_info.load_status << "\n";
        if (load_status != armnn::Status::Success) {
            throw std::runtime_error(
                "Alnpu LoadNetwork failed" +
                (load_error.empty() ? std::string{} : ": " + load_error)
            );
        }

        input_buffer = std::make_unique<CmaBuffer>(input_info.GetNumBytes());
        for (const auto& info : output_infos) {
            output_buffers.push_back(std::make_unique<CmaBuffer>(info.GetNumBytes()));
        }
        std::cerr << "armnn_stage=cma_buffers_ready input_bytes=" << input_info.GetNumBytes()
                  << " output_count=" << output_buffers.size() << "\n";
    }

    edgeai::filesystem::path model_path;
    std::string model_sha256;
    CmaScope cma_scope;
    armnnOnnxParser::IOnnxParserPtr parser{
        nullptr, &armnnOnnxParser::IOnnxParser::Destroy};
    armnn::INetworkPtr network{nullptr, &armnn::INetwork::Destroy};
    armnn::IOptimizedNetworkPtr optimized_network{
        nullptr, &armnn::IOptimizedNetwork::Destroy};
    armnn::IRuntimePtr runtime{nullptr, &armnn::IRuntime::Destroy};
    armnn::NetworkId network_id{-1};
    armnn::LayerBindingId input_binding_id{-1};
    std::vector<armnn::LayerBindingId> output_binding_ids;
    std::string input_name;
    std::string output_name;
    std::vector<std::string> output_names_;
    armnn::TensorInfo input_info;
    armnn::TensorInfo output_info;
    std::vector<armnn::TensorInfo> output_infos;
    std::unique_ptr<CmaBuffer> input_buffer;
    std::vector<std::unique_ptr<CmaBuffer>> output_buffers;
    ArmnnRuntimeInfo runtime_info;
};

ArmnnDetector::ArmnnDetector(const edgeai::filesystem::path& model_path)
    : impl_(std::make_unique<Impl>(model_path)) {}

ArmnnDetector::~ArmnnDetector() = default;
ArmnnDetector::ArmnnDetector(ArmnnDetector&&) noexcept = default;
ArmnnDetector& ArmnnDetector::operator=(ArmnnDetector&&) noexcept = default;

const ArmnnRuntimeInfo& ArmnnDetector::runtime_info() const {
    return impl_->runtime_info;
}

const edgeai::filesystem::path& ArmnnDetector::model_path() const {
    return impl_->model_path;
}

const std::string& ArmnnDetector::model_sha256() const {
    return impl_->model_sha256;
}

ArmnnRawInferenceResult ArmnnDetector::infer(const edgeai::common::InputTensor& tensor) {
    const std::vector<std::int64_t> input_shape{
        tensor.shape[0], tensor.shape[1], tensor.shape[2], tensor.shape[3]
    };
    if (input_shape != impl_->runtime_info.input.shape) {
        throw std::runtime_error("ArmNN input tensor shape differs from parser contract");
    }
    if (tensor.values.size() != static_cast<std::size_t>(impl_->input_info.GetNumElements())) {
        throw std::runtime_error("ArmNN input tensor element count differs from parser contract");
    }
    const auto supported_type = [](armnn::DataType type) {
        return type == armnn::DataType::Float32 || type == armnn::DataType::QAsymmU8 ||
               type == armnn::DataType::QAsymmS8 || type == armnn::DataType::QSymmS8;
    };
    if (!supported_type(impl_->input_info.GetDataType()) ||
        std::any_of(impl_->output_infos.begin(), impl_->output_infos.end(),
                    [&supported_type](const armnn::TensorInfo& info) {
                        return !supported_type(info.GetDataType());
                    })) {
        throw std::runtime_error("unsupported ArmNN tensor dtype for project runner: input=" +
                                 std::string(dtype_name(impl_->input_info.GetDataType())) +
                                 " output=" + dtype_name(impl_->output_info.GetDataType()));
    }
    const auto input_type = impl_->input_info.GetDataType();
    const float input_scale = impl_->input_info.GetQuantizationScale();
    const auto input_offset = impl_->input_info.GetQuantizationOffset();
    if (input_type == armnn::DataType::Float32) {
        std::memcpy(impl_->input_buffer->data(), tensor.values.data(),
                    tensor.values.size() * sizeof(float));
    } else {
        if (!(std::isfinite(input_scale) && input_scale > 0.0F)) {
            throw std::runtime_error("quantized ArmNN input has invalid scale");
        }
        if (input_type == armnn::DataType::QAsymmU8) {
            auto* destination = static_cast<std::uint8_t*>(impl_->input_buffer->data());
            for (std::size_t index = 0; index < tensor.values.size(); ++index) {
                const auto quantized = static_cast<long long>(std::llround(
                    static_cast<double>(tensor.values[index]) / input_scale + input_offset));
                destination[index] = static_cast<std::uint8_t>(std::clamp(quantized, 0LL, 255LL));
            }
        } else {
            auto* destination = static_cast<std::int8_t*>(impl_->input_buffer->data());
            for (std::size_t index = 0; index < tensor.values.size(); ++index) {
                const auto quantized = static_cast<long long>(std::llround(
                    static_cast<double>(tensor.values[index]) / input_scale + input_offset));
                destination[index] = static_cast<std::int8_t>(std::clamp(quantized, -128LL, 127LL));
            }
        }
    }
    if (cma_mem_sync_for_device(
            impl_->input_buffer->raw().phys_addr,
            impl_->input_info.GetNumBytes()) != 0) {
        throw std::runtime_error("cma_mem_sync_for_device failed for ArmNN input");
    }
    const armnn::InputTensors inputs{{
        impl_->input_binding_id,
        armnn::ConstTensor(impl_->input_info, impl_->input_buffer->data())
    }};
    armnn::OutputTensors outputs;
    outputs.reserve(impl_->output_infos.size());
    for (std::size_t index = 0; index < impl_->output_infos.size(); ++index) {
        outputs.push_back({
            impl_->output_binding_ids[index],
            armnn::Tensor(impl_->output_infos[index], impl_->output_buffers[index]->data())
        });
    }
    std::cerr << "armnn_stage=enqueue_begin\n";
    const armnn::Status status = impl_->runtime->EnqueueWorkload(
        impl_->network_id, inputs, outputs);
    std::cerr << "armnn_stage=enqueue_complete status="
              << (status == armnn::Status::Success ? "Success" : "Failure") << "\n";
    if (status != armnn::Status::Success) {
        throw std::runtime_error("ArmNN EnqueueWorkload failed on forced Alnpu backend");
    }
    for (std::size_t index = 0; index < impl_->output_infos.size(); ++index) {
        if (cma_mem_sync_for_cpu(
                impl_->output_buffers[index]->raw().phys_addr,
                impl_->output_infos[index].GetNumBytes()) != 0) {
            throw std::runtime_error("cma_mem_sync_for_cpu failed for ArmNN output");
        }
    }
    ArmnnRawInferenceResult result;
    result.tensors.reserve(impl_->output_infos.size());
    for (std::size_t index = 0; index < impl_->output_infos.size(); ++index) {
        ArmnnRawTensor tensor;
        tensor.name = impl_->output_names_[index];
        tensor.shape = impl_->runtime_info.outputs[index].shape;
        const auto& info = impl_->output_infos[index];
        tensor.values.resize(info.GetNumElements());
        if (info.GetDataType() == armnn::DataType::Float32) {
            std::memcpy(tensor.values.data(), impl_->output_buffers[index]->data(),
                        tensor.values.size() * sizeof(float));
        } else {
            const float scale = info.GetQuantizationScale();
            const auto offset = info.GetQuantizationOffset();
            if (!(std::isfinite(scale) && scale > 0.0F)) {
                throw std::runtime_error("quantized ArmNN output has invalid scale");
            }
            if (info.GetDataType() == armnn::DataType::QAsymmU8) {
                const auto* source = static_cast<const std::uint8_t*>(
                    impl_->output_buffers[index]->data());
                for (std::size_t element = 0; element < tensor.values.size(); ++element) {
                    tensor.values[element] = (static_cast<float>(source[element]) - offset) * scale;
                }
            } else {
                const auto* source = static_cast<const std::int8_t*>(
                    impl_->output_buffers[index]->data());
                for (std::size_t element = 0; element < tensor.values.size(); ++element) {
                    tensor.values[element] = (static_cast<float>(source[element]) - offset) * scale;
                }
            }
        }
        result.tensors.push_back(std::move(tensor));
    }
    if (result.tensors.size() == 1U) {
        result.shape = result.tensors.front().shape;
        result.values = result.tensors.front().values;
    }
    return result;
}

}  // namespace edgeai::backends
