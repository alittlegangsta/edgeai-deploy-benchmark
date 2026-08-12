#include <cuda_runtime.h>

#include <cstdio>

int main() {
    int device_count = 0;
    const cudaError_t count_status = cudaGetDeviceCount(&device_count);
    if (count_status != cudaSuccess || device_count < 1) {
        std::fprintf(stderr, "cudaGetDeviceCount failed: %s (count=%d)\n",
                     cudaGetErrorString(count_status), device_count);
        return 1;
    }

    cudaDeviceProp properties{};
    const cudaError_t property_status = cudaGetDeviceProperties(&properties, 0);
    if (property_status != cudaSuccess) {
        std::fprintf(stderr, "cudaGetDeviceProperties failed: %s\n",
                     cudaGetErrorString(property_status));
        return 2;
    }

    void* device_memory = nullptr;
    const cudaError_t allocation_status = cudaMalloc(&device_memory, 4096);
    if (allocation_status != cudaSuccess) {
        std::fprintf(stderr, "cudaMalloc failed: %s\n",
                     cudaGetErrorString(allocation_status));
        return 3;
    }
    const cudaError_t memset_status = cudaMemset(device_memory, 0, 4096);
    const cudaError_t sync_status = cudaDeviceSynchronize();
    const cudaError_t free_status = cudaFree(device_memory);
    if (memset_status != cudaSuccess || sync_status != cudaSuccess ||
        free_status != cudaSuccess) {
        std::fprintf(stderr, "CUDA memory probe failed: memset=%s sync=%s free=%s\n",
                     cudaGetErrorString(memset_status),
                     cudaGetErrorString(sync_status),
                     cudaGetErrorString(free_status));
        return 4;
    }

    std::printf("device_count=%d\n", device_count);
    std::printf("device_name=%s\n", properties.name);
    std::printf("compute_capability=%d.%d\n", properties.major, properties.minor);
    std::printf("global_memory_bytes=%zu\n",
                static_cast<std::size_t>(properties.totalGlobalMem));
    return 0;
}
