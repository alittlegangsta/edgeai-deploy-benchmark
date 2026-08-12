#include "edgeai/backends/tensorrt_detector.hpp"

#include <NvInferRuntime.h>
#include <cuda_runtime_api.h>

#include <fstream>
#include <cmath>
#include <cstdio>
#include <limits>
#include <stdexcept>
#include <utility>

namespace edgeai::backends {
namespace {

class Logger final : public nvinfer1::ILogger {
public:
    void log(Severity severity, const char* message) noexcept override {
        if (severity <= Severity::kWARNING) {
            std::fprintf(stderr, "[TensorRT] %s\n", message);
        }
    }
};

void check_cuda(cudaError_t status, const char* operation) {
    if (status != cudaSuccess) {
        throw std::runtime_error(std::string(operation) + " failed: " +
                                 cudaGetErrorString(status));
    }
}

std::vector<std::uint8_t> read_file(const std::filesystem::path& path) {
    std::ifstream input(path, std::ios::binary | std::ios::ate);
    if (!input) {
        throw std::runtime_error("failed to open TensorRT engine: " + path.string());
    }
    const std::streamsize size = input.tellg();
    if (size <= 0) {
        throw std::runtime_error("TensorRT engine is empty: " + path.string());
    }
    input.seekg(0, std::ios::beg);
    std::vector<std::uint8_t> bytes(static_cast<std::size_t>(size));
    if (!input.read(reinterpret_cast<char*>(bytes.data()), size)) {
        throw std::runtime_error("failed to read TensorRT engine: " + path.string());
    }
    return bytes;
}

std::vector<std::int64_t> dims_to_vector(const nvinfer1::Dims& dims) {
    if (dims.nbDims <= 0) {
        throw std::runtime_error("TensorRT tensor has no dimensions");
    }
    std::vector<std::int64_t> result;
    result.reserve(static_cast<std::size_t>(dims.nbDims));
    for (int index = 0; index < dims.nbDims; ++index) {
        if (dims.d[index] <= 0) {
            throw std::runtime_error("dynamic or invalid TensorRT tensor shape is unsupported");
        }
        result.push_back(dims.d[index]);
    }
    return result;
}

std::size_t volume(const std::vector<std::int64_t>& shape) {
    std::size_t result = 1U;
    for (const std::int64_t dimension : shape) {
        if (dimension <= 0 ||
            static_cast<std::uint64_t>(dimension) >
                std::numeric_limits<std::size_t>::max() / result) {
            throw std::runtime_error("TensorRT tensor volume overflows host size");
        }
        result *= static_cast<std::size_t>(dimension);
    }
    return result;
}

const char* dtype_name(nvinfer1::DataType dtype) {
    switch (dtype) {
        case nvinfer1::DataType::kFLOAT:
            return "FLOAT";
        case nvinfer1::DataType::kHALF:
            return "HALF";
        case nvinfer1::DataType::kINT8:
            return "INT8";
        case nvinfer1::DataType::kINT32:
            return "INT32";
        case nvinfer1::DataType::kBOOL:
            return "BOOL";
        default:
            return "UNKNOWN";
    }
}

}  // namespace

struct TensorRtDetector::Impl {
    explicit Impl(const std::filesystem::path& path) : engine_path(path) {
        if (!std::filesystem::is_regular_file(path) || std::filesystem::file_size(path) == 0U) {
            throw std::runtime_error("TensorRT engine is missing or empty: " + path.string());
        }
        check_cuda(cudaGetDevice(&device), "cudaGetDevice");
        cudaDeviceProp properties{};
        check_cuda(cudaGetDeviceProperties(&properties, device), "cudaGetDeviceProperties");
        info.device_name = properties.name;
        info.compute_capability_major = properties.major;
        info.compute_capability_minor = properties.minor;
        info.device_memory_bytes = properties.totalGlobalMem;

        const std::vector<std::uint8_t> bytes = read_file(path);
        runtime.reset(nvinfer1::createInferRuntime(logger));
        if (!runtime) {
            throw std::runtime_error("TensorRT createInferRuntime returned null");
        }
        engine.reset(runtime->deserializeCudaEngine(bytes.data(), bytes.size()));
        if (!engine) {
            throw std::runtime_error("TensorRT engine deserialization failed");
        }
        context.reset(engine->createExecutionContext());
        if (!context) {
            throw std::runtime_error("TensorRT createExecutionContext returned null");
        }

        for (int index = 0; index < engine->getNbIOTensors(); ++index) {
            const char* name = engine->getIOTensorName(index);
            if (name == nullptr) {
                throw std::runtime_error("TensorRT returned a null I/O tensor name");
            }
            if (engine->getTensorIOMode(name) == nvinfer1::TensorIOMode::kINPUT) {
                if (!info.input_name.empty()) {
                    throw std::runtime_error("multiple TensorRT inputs are unsupported");
                }
                info.input_name = name;
                info.input_shape = dims_to_vector(engine->getTensorShape(name));
                info.input_dtype = dtype_name(engine->getTensorDataType(name));
            } else {
                if (!info.output_name.empty()) {
                    throw std::runtime_error("multiple TensorRT outputs are unsupported");
                }
                info.output_name = name;
                info.output_shape = dims_to_vector(engine->getTensorShape(name));
                info.output_dtype = dtype_name(engine->getTensorDataType(name));
            }
        }
        if (info.input_name.empty() || info.output_name.empty()) {
            throw std::runtime_error("TensorRT engine must expose one input and one output");
        }
        if (info.input_dtype != "FLOAT" || info.output_dtype != "FLOAT") {
            throw std::runtime_error("TensorRT runner requires FP32 input and output tensors");
        }
        if (info.input_shape != std::vector<std::int64_t>{1, 3, 640, 640} ||
            info.output_shape != std::vector<std::int64_t>{1, 25200, 85}) {
            throw std::runtime_error("TensorRT engine I/O shape differs from frozen YOLOv5n contract");
        }

        input_bytes = volume(info.input_shape) * sizeof(float);
        output_bytes = volume(info.output_shape) * sizeof(float);
        check_cuda(cudaStreamCreate(&stream), "cudaStreamCreate");
        check_cuda(cudaEventCreate(&h2d_start), "cudaEventCreate(h2d_start)");
        check_cuda(cudaEventCreate(&h2d_end), "cudaEventCreate(h2d_end)");
        check_cuda(cudaEventCreate(&inference_start), "cudaEventCreate(inference_start)");
        check_cuda(cudaEventCreate(&inference_end), "cudaEventCreate(inference_end)");
        check_cuda(cudaEventCreate(&d2h_start), "cudaEventCreate(d2h_start)");
        check_cuda(cudaEventCreate(&d2h_end), "cudaEventCreate(d2h_end)");
        check_cuda(cudaMalloc(&device_input, input_bytes), "cudaMalloc(input)");
        check_cuda(cudaMalloc(&device_output, output_bytes), "cudaMalloc(output)");
        if (!context->setTensorAddress(info.input_name.c_str(), device_input) ||
            !context->setTensorAddress(info.output_name.c_str(), device_output)) {
            throw std::runtime_error("TensorRT setTensorAddress failed");
        }
        info.engine_path = path.string();
        info.precision_mode = "FP32_IO; engine internal precision recorded by build command";
    }

    ~Impl() {
        if (device_input != nullptr) {
            cudaFree(device_input);
        }
        if (device_output != nullptr) {
            cudaFree(device_output);
        }
        if (h2d_start != nullptr) {
            cudaEventDestroy(h2d_start);
        }
        if (h2d_end != nullptr) {
            cudaEventDestroy(h2d_end);
        }
        if (inference_start != nullptr) {
            cudaEventDestroy(inference_start);
        }
        if (inference_end != nullptr) {
            cudaEventDestroy(inference_end);
        }
        if (d2h_start != nullptr) {
            cudaEventDestroy(d2h_start);
        }
        if (d2h_end != nullptr) {
            cudaEventDestroy(d2h_end);
        }
        if (stream != nullptr) {
            cudaStreamDestroy(stream);
        }
    }

    std::filesystem::path engine_path;
    Logger logger;
    std::unique_ptr<nvinfer1::IRuntime> runtime;
    std::unique_ptr<nvinfer1::ICudaEngine> engine;
    std::unique_ptr<nvinfer1::IExecutionContext> context;
    TensorRtRuntimeInfo info;
    int device{0};
    cudaStream_t stream{nullptr};
    cudaEvent_t h2d_start{nullptr};
    cudaEvent_t h2d_end{nullptr};
    cudaEvent_t inference_start{nullptr};
    cudaEvent_t inference_end{nullptr};
    cudaEvent_t d2h_start{nullptr};
    cudaEvent_t d2h_end{nullptr};
    void* device_input{nullptr};
    void* device_output{nullptr};
    std::size_t input_bytes{0};
    std::size_t output_bytes{0};
};

TensorRtDetector::TensorRtDetector(const std::filesystem::path& engine_path)
    : impl_(std::make_unique<Impl>(engine_path)) {}

TensorRtDetector::~TensorRtDetector() = default;
TensorRtDetector::TensorRtDetector(TensorRtDetector&&) noexcept = default;
TensorRtDetector& TensorRtDetector::operator=(TensorRtDetector&&) noexcept = default;

const TensorRtRuntimeInfo& TensorRtDetector::runtime_info() const {
    return impl_->info;
}

TensorRtRawResult TensorRtDetector::infer(const edgeai::common::InputTensor& tensor) {
    if (!impl_) {
        throw std::runtime_error("TensorRT detector is not initialized");
    }
    if (tensor.shape != std::array<std::int64_t, 4>{{1, 3, 640, 640}} ||
        tensor.values.size() != impl_->input_bytes / sizeof(float)) {
        throw std::runtime_error("TensorRT input differs from frozen YOLOv5n contract");
    }

    check_cuda(cudaEventRecord(impl_->h2d_start, impl_->stream), "cudaEventRecord(h2d_start)");
    check_cuda(cudaMemcpyAsync(
                   impl_->device_input,
                   tensor.values.data(),
                   impl_->input_bytes,
                   cudaMemcpyHostToDevice,
                   impl_->stream
               ),
               "cudaMemcpyAsync(H2D)");
    check_cuda(cudaEventRecord(impl_->h2d_end, impl_->stream), "cudaEventRecord(h2d_end)");
    check_cuda(cudaEventRecord(impl_->inference_start, impl_->stream),
               "cudaEventRecord(inference_start)");
    if (!impl_->context->enqueueV3(impl_->stream)) {
        throw std::runtime_error("TensorRT enqueueV3 failed");
    }
    check_cuda(cudaEventRecord(impl_->inference_end, impl_->stream),
               "cudaEventRecord(inference_end)");
    TensorRtRawResult result;
    result.values.resize(impl_->output_bytes / sizeof(float));
    check_cuda(cudaEventRecord(impl_->d2h_start, impl_->stream), "cudaEventRecord(d2h_start)");
    check_cuda(cudaMemcpyAsync(
                   result.values.data(),
                   impl_->device_output,
                   impl_->output_bytes,
                   cudaMemcpyDeviceToHost,
                   impl_->stream
               ),
               "cudaMemcpyAsync(D2H)");
    check_cuda(cudaEventRecord(impl_->d2h_end, impl_->stream), "cudaEventRecord(d2h_end)");
    check_cuda(cudaEventSynchronize(impl_->d2h_end), "cudaEventSynchronize");
    float milliseconds = 0.0F;
    check_cuda(cudaEventElapsedTime(&milliseconds, impl_->h2d_start, impl_->h2d_end),
               "cudaEventElapsedTime(H2D)");
    result.gpu_timings.host_to_device = milliseconds;
    check_cuda(cudaEventElapsedTime(&milliseconds, impl_->inference_start, impl_->inference_end),
               "cudaEventElapsedTime(inference)");
    result.gpu_timings.inference = milliseconds;
    check_cuda(cudaEventElapsedTime(&milliseconds, impl_->d2h_start, impl_->d2h_end),
               "cudaEventElapsedTime(D2H)");
    result.gpu_timings.device_to_host = milliseconds;
    result.shape = impl_->info.output_shape;
    for (const float value : result.values) {
        if (!std::isfinite(value)) {
            throw std::runtime_error("TensorRT output contains a non-finite value");
        }
    }
    return result;
}

}  // namespace edgeai::backends
