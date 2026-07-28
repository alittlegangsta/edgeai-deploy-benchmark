#include <cpu.h>
#include <mat.h>
#include <net.h>
#include <platform.h>

#include <cmath>
#include <iostream>

int main() {
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

    ncnn::Mat values(4);
    if (values.empty() || values.elembits() != 32 || values.elempack != 1) {
        std::cerr << "mat_allocation=FAIL\n";
        return 1;
    }

    float* data = static_cast<float*>(values.data);
    data[0] = 1.0F;
    data[1] = 2.0F;
    data[2] = 3.0F;
    data[3] = 4.0F;

    float sum = 0.0F;
    for (int index = 0; index < 4; ++index) {
        sum += data[index];
    }

    const int cpu_count = ncnn::get_cpu_count();
    std::cout << "program=edgeai_anlogic_ncnn_smoke\n";
    std::cout << "ncnn_version=" << NCNN_VERSION_STRING << '\n';
    std::cout << "reported_cpu_count=" << cpu_count << '\n';
    std::cout << "configured_threads=" << network.opt.num_threads << '\n';
    std::cout << "vulkan_enabled=" << network.opt.use_vulkan_compute << '\n';
    std::cout << "fp16_storage_enabled=" << network.opt.use_fp16_storage << '\n';
    std::cout << "fp16_arithmetic_enabled=" << network.opt.use_fp16_arithmetic << '\n';
    std::cout << "bf16_storage_enabled=" << network.opt.use_bf16_storage << '\n';
    std::cout << "int8_inference_enabled=" << network.opt.use_int8_inference << '\n';
    std::cout << "mat_sum=" << sum << '\n';

    if (cpu_count < 1 || network.opt.num_threads != 1 || std::fabs(sum - 10.0F) > 1e-6F) {
        std::cerr << "runtime_contract=FAIL\n";
        return 2;
    }

    if (network.opt.use_vulkan_compute || network.opt.use_fp16_storage
        || network.opt.use_fp16_arithmetic || network.opt.use_bf16_storage
        || network.opt.use_int8_inference) {
        std::cerr << "precision_contract=FAIL\n";
        return 3;
    }

    std::cout << "runtime_contract=PASS\n";
    return 0;
}
