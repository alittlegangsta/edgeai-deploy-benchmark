#include "edgeai/inference_backend.hpp"

#if EDGEAI_UNIFIED_HAVE_NCNN
#include "edgeai/backends/ncnn_detector.hpp"
#endif

#if EDGEAI_UNIFIED_HAVE_ORT
#include "edgeai/backends/ort_detector.hpp"
#endif

#if EDGEAI_UNIFIED_HAVE_TENSORRT
#include "edgeai/backends/tensorrt_detector.hpp"
#endif

#include <stdexcept>

#include <opencv2/core/persistence.hpp>

namespace edgeai::unified {
namespace {

#if EDGEAI_UNIFIED_HAVE_ORT
class OrtAdapter final : public InferenceBackend {
public:
    explicit OrtAdapter(const BackendOptions& options)
        : detector_(options.model, options.manifest, 1, 1) {
        if (options.precision != "fp32") {
            throw std::runtime_error("ORT backend supports only --precision fp32");
        }
        const auto& runtime = detector_.runtime_info();
        if (runtime.inputs.size() != 1U || runtime.outputs.size() != 1U) {
            throw std::runtime_error("ORT unified backend requires one input and one output");
        }
        info_.backend = "ort";
        info_.precision = "fp32";
        info_.runtime = runtime.version + "/" + runtime.execution_provider;
        info_.model_identity = "onnx_sha256=" + detector_.model_sha256();
        info_.input_dtype = runtime.inputs[0].dtype;
        info_.output_dtype = runtime.outputs[0].dtype;
        info_.input_shape = runtime.inputs[0].shape;
        info_.output_shape = runtime.outputs[0].shape;
    }

    const BackendInfo& info() const override { return info_; }

    RawInferenceResult infer(const edgeai::common::InputTensor& tensor) override {
        const auto result = detector_.infer(tensor);
        return {result.values, result.shape};
    }

private:
    edgeai::backends::OrtDetector detector_;
    BackendInfo info_;
};
#endif

#if EDGEAI_UNIFIED_HAVE_NCNN
class NcnnAdapter final : public InferenceBackend {
public:
    explicit NcnnAdapter(const BackendOptions& options) {
        if (options.precision != "fp32" && options.precision != "int8") {
            throw std::runtime_error("ncnn unified backend supports --precision fp32 or int8");
        }
        if (options.precision == "int8") {
            cv::FileStorage manifest(
                options.model.string(), cv::FileStorage::READ | cv::FileStorage::FORMAT_JSON
            );
            if (!manifest.isOpened()) {
                throw std::runtime_error("ncnn --precision int8 manifest could not be opened");
            }
            const cv::FileNode declared_precision = manifest["contract"]["precision"];
            if (!declared_precision.isString() ||
                static_cast<std::string>(declared_precision) != "INT8") {
                throw std::runtime_error(
                    "ncnn --precision int8 requires a matching manifest declaring "
                    "contract.precision=INT8; the supplied FP32 manifest is rejected"
                );
            }
        }
        edgeai::backends::NcnnRuntimeOptions runtime_options;
        runtime_options.threads = options.threads;
        runtime_options.use_packing_layout = options.packing;
        runtime_options.use_int8_inference = options.precision == "int8";
        runtime_options.use_int8_packed = options.precision == "int8";
        runtime_options.use_int8_storage = options.precision == "int8";
        runtime_options.use_int8_arithmetic = options.precision == "int8";
        detector_ = std::make_unique<edgeai::backends::NcnnDetector>(
            options.model, runtime_options, options.model_param, options.model_bin
        );
        const auto& runtime = detector_->runtime_info();
        if (runtime.inputs.size() != 1U || runtime.outputs.size() != 1U) {
            throw std::runtime_error("ncnn unified backend requires one input and one output");
        }
        info_.backend = "ncnn";
        info_.precision = options.precision;
        info_.runtime = runtime.version + "/" + runtime.effective_parallel_backend;
        info_.model_identity = "param_sha256=" + detector_->param_sha256() +
                               ",bin_sha256=" + detector_->bin_sha256();
        info_.input_dtype = runtime.inputs[0].dtype;
        info_.output_dtype = runtime.outputs[0].dtype;
        info_.input_shape = runtime.inputs[0].logical_shape;
        info_.output_shape = runtime.outputs[0].logical_shape;
    }

    const BackendInfo& info() const override { return info_; }

    RawInferenceResult infer(const edgeai::common::InputTensor& tensor) override {
        const auto result = detector_->infer(tensor);
        return {result.values, result.shape};
    }

private:
    std::unique_ptr<edgeai::backends::NcnnDetector> detector_;
    BackendInfo info_;
};
#endif

#if EDGEAI_UNIFIED_HAVE_TENSORRT
class TensorRtAdapter final : public InferenceBackend {
public:
    explicit TensorRtAdapter(const BackendOptions& options)
        : detector_(options.model) {
        if (options.precision != "fp32" && options.precision != "fp16") {
            throw std::runtime_error("TensorRT unified backend supports --precision fp32 or fp16");
        }
        const auto& runtime = detector_.runtime_info();
        info_.backend = "tensorrt";
        info_.precision = options.precision;
        info_.runtime = "TensorRT CUDA/" + runtime.device_name;
        info_.model_identity = "engine=" + options.model.string() +
                               ",bytes=" + std::to_string(std::filesystem::file_size(options.model));
        info_.input_dtype = runtime.input_dtype;
        info_.output_dtype = runtime.output_dtype;
        info_.input_shape = runtime.input_shape;
        info_.output_shape = runtime.output_shape;
    }

    const BackendInfo& info() const override { return info_; }

    RawInferenceResult infer(const edgeai::common::InputTensor& tensor) override {
        const auto result = detector_.infer(tensor);
        return {result.values, result.shape};
    }

private:
    edgeai::backends::TensorRtDetector detector_;
    BackendInfo info_;
};
#endif

}  // namespace

std::unique_ptr<InferenceBackend> make_inference_backend(const BackendOptions& options) {
    if (options.backend == "ort") {
#if EDGEAI_UNIFIED_HAVE_ORT
        return std::make_unique<OrtAdapter>(options);
#else
        throw std::runtime_error("backend 'ort' is unavailable: build with EDGEAI_ENABLE_ORT=ON");
#endif
    }
    if (options.backend == "ncnn") {
#if EDGEAI_UNIFIED_HAVE_NCNN
        return std::make_unique<NcnnAdapter>(options);
#else
        throw std::runtime_error("backend 'ncnn' is unavailable: build with EDGEAI_ENABLE_NCNN=ON");
#endif
    }
    if (options.backend == "tensorrt") {
#if EDGEAI_UNIFIED_HAVE_TENSORRT
        return std::make_unique<TensorRtAdapter>(options);
#else
        throw std::runtime_error(
            "backend 'tensorrt' is unavailable: build with EDGEAI_ENABLE_TENSORRT=ON"
        );
#endif
    }
    throw std::runtime_error("unknown backend '" + options.backend + "'; choose ort, tensorrt or ncnn");
}

}  // namespace edgeai::unified
