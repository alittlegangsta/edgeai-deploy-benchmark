cmake_minimum_required(VERSION 3.16)

project(edgeai_deploy_benchmark LANGUAGES CXX)

if(POLICY CMP0144)
    cmake_policy(SET CMP0144 NEW)
endif()

if(NOT CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(CMAKE_CXX_EXTENSIONS OFF)

find_package(OpenCV 4 REQUIRED COMPONENTS core imgproc imgcodecs videoio)

set(ONNXRUNTIME_ROOT "" CACHE PATH "Absolute root of ONNX Runtime 1.18.1 C/C++ SDK")
if(NOT IS_ABSOLUTE "${ONNXRUNTIME_ROOT}")
    message(FATAL_ERROR "ONNXRUNTIME_ROOT must be an explicit absolute SDK path")
endif()
get_filename_component(ONNXRUNTIME_ROOT "${ONNXRUNTIME_ROOT}" REALPATH)
set(ONNXRUNTIME_INCLUDE_DIR "${ONNXRUNTIME_ROOT}/include")
set(ONNXRUNTIME_LIBRARY "${ONNXRUNTIME_ROOT}/lib/libonnxruntime.so")
set(ONNXRUNTIME_VERSION_FILE "${ONNXRUNTIME_ROOT}/VERSION_NUMBER")
foreach(required_path
        "${ONNXRUNTIME_INCLUDE_DIR}/onnxruntime_c_api.h"
        "${ONNXRUNTIME_INCLUDE_DIR}/onnxruntime_cxx_api.h"
        "${ONNXRUNTIME_INCLUDE_DIR}/cpu_provider_factory.h"
        "${ONNXRUNTIME_LIBRARY}"
        "${ONNXRUNTIME_VERSION_FILE}")
    if(NOT EXISTS "${required_path}")
        message(FATAL_ERROR "Required ONNX Runtime SDK artifact is missing: ${required_path}")
    endif()
endforeach()
file(READ "${ONNXRUNTIME_VERSION_FILE}" ONNXRUNTIME_VERSION)
string(STRIP "${ONNXRUNTIME_VERSION}" ONNXRUNTIME_VERSION)
if(NOT ONNXRUNTIME_VERSION STREQUAL "1.18.1")
    message(FATAL_ERROR
        "ONNX Runtime SDK version must be 1.18.1, observed: ${ONNXRUNTIME_VERSION}"
    )
endif()
message(STATUS "ONNX Runtime root: ${ONNXRUNTIME_ROOT}")
message(STATUS "ONNX Runtime include: ${ONNXRUNTIME_INCLUDE_DIR}")
message(STATUS "ONNX Runtime library: ${ONNXRUNTIME_LIBRARY}")
message(STATUS "ONNX Runtime version: ${ONNXRUNTIME_VERSION}")

set(NCNN_ROOT "" CACHE PATH "Absolute root of the pinned ncnn 20240410 install")
if(NOT IS_ABSOLUTE "${NCNN_ROOT}")
    message(FATAL_ERROR "NCNN_ROOT must be an explicit absolute SDK path")
endif()
get_filename_component(NCNN_ROOT "${NCNN_ROOT}" REALPATH)
set(ncnn_DIR "${NCNN_ROOT}/lib/cmake/ncnn")
if(NOT EXISTS "${ncnn_DIR}/ncnnConfig.cmake")
    message(FATAL_ERROR "Required ncnn CMake config is missing: ${ncnn_DIR}/ncnnConfig.cmake")
endif()
find_package(ncnn CONFIG REQUIRED NO_DEFAULT_PATH PATHS "${ncnn_DIR}")
message(STATUS "ncnn root: ${NCNN_ROOT}")

function(edgeai_enable_warnings target_name)
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        target_compile_options(${target_name} PRIVATE
            -Wall
            -Wextra
            -Wpedantic
        )
    endif()
endfunction()

add_library(edgeai_common STATIC
    src/common/benchmark.cpp
    src/common/config.cpp
    src/common/postprocess.cpp
    src/common/preprocess.cpp
    src/common/video_pipeline.cpp
    src/common/visualize.cpp
)

target_compile_features(edgeai_common PUBLIC cxx_std_17)
set_target_properties(edgeai_common PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
target_include_directories(edgeai_common PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
target_include_directories(edgeai_common SYSTEM PUBLIC
    ${OpenCV_INCLUDE_DIRS}
)
target_link_libraries(edgeai_common PUBLIC
    ${OpenCV_LIBS}
)
edgeai_enable_warnings(edgeai_common)

add_executable(edgeai_opencv_smoke
    apps/opencv_smoke.cpp
)

target_compile_features(edgeai_opencv_smoke PRIVATE cxx_std_17)
set_target_properties(edgeai_opencv_smoke PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)

target_include_directories(edgeai_opencv_smoke SYSTEM PRIVATE
    ${OpenCV_INCLUDE_DIRS}
)
target_link_libraries(edgeai_opencv_smoke PRIVATE
    ${OpenCV_LIBS}
)

edgeai_enable_warnings(edgeai_opencv_smoke)

add_executable(edgeai_preprocess_probe
    apps/preprocess_probe.cpp
)
target_compile_features(edgeai_preprocess_probe PRIVATE cxx_std_17)
set_target_properties(edgeai_preprocess_probe PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
target_link_libraries(edgeai_preprocess_probe PRIVATE edgeai_common)
edgeai_enable_warnings(edgeai_preprocess_probe)

add_library(edgeai_ort_backend STATIC
    src/backends/ort_detector.cpp
)
target_compile_features(edgeai_ort_backend PUBLIC cxx_std_17)
set_target_properties(edgeai_ort_backend PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
target_include_directories(edgeai_ort_backend PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
)
target_include_directories(edgeai_ort_backend SYSTEM PRIVATE
    ${ONNXRUNTIME_INCLUDE_DIR}
)
target_link_libraries(edgeai_ort_backend PUBLIC
    edgeai_common
    ${ONNXRUNTIME_LIBRARY}
)
edgeai_enable_warnings(edgeai_ort_backend)

add_executable(edgeai_ort_image
    apps/ort_image.cpp
)
target_compile_features(edgeai_ort_image PRIVATE cxx_std_17)
set_target_properties(edgeai_ort_image PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
    BUILD_RPATH "${ONNXRUNTIME_ROOT}/lib"
)
target_link_libraries(edgeai_ort_image PRIVATE edgeai_ort_backend)
edgeai_enable_warnings(edgeai_ort_image)

add_executable(edgeai_common_tests
    tests/test_common.cpp
)
target_compile_features(edgeai_common_tests PRIVATE cxx_std_17)
set_target_properties(edgeai_common_tests PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
target_compile_definitions(edgeai_common_tests PRIVATE
    EDGEAI_REPOSITORY_ROOT="${CMAKE_CURRENT_SOURCE_DIR}/.."
)
target_link_libraries(edgeai_common_tests PRIVATE edgeai_common)
edgeai_enable_warnings(edgeai_common_tests)

enable_testing()
add_test(NAME edgeai_common_tests COMMAND edgeai_common_tests)

add_executable(edgeai_postprocess_tests
    tests/test_postprocess.cpp
)
target_compile_features(edgeai_postprocess_tests PRIVATE cxx_std_17)
set_target_properties(edgeai_postprocess_tests PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
target_link_libraries(edgeai_postprocess_tests PRIVATE edgeai_common)
edgeai_enable_warnings(edgeai_postprocess_tests)
add_test(NAME edgeai_postprocess_tests COMMAND edgeai_postprocess_tests)
add_test(NAME edgeai_ort_image_invalid_args COMMAND edgeai_ort_image)
set_tests_properties(edgeai_ort_image_invalid_args PROPERTIES WILL_FAIL TRUE)

add_executable(edgeai_ort_video
    apps/ort_video.cpp
)
target_compile_features(edgeai_ort_video PRIVATE cxx_std_17)
set_target_properties(edgeai_ort_video PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
    BUILD_RPATH "${ONNXRUNTIME_ROOT}/lib"
)
target_link_libraries(edgeai_ort_video PRIVATE edgeai_ort_backend)
edgeai_enable_warnings(edgeai_ort_video)
add_test(NAME edgeai_ort_video_invalid_args COMMAND edgeai_ort_video)
set_tests_properties(edgeai_ort_video_invalid_args PROPERTIES WILL_FAIL TRUE)

add_executable(edgeai_video_pipeline_tests
    tests/test_video_pipeline.cpp
)
target_compile_features(edgeai_video_pipeline_tests PRIVATE cxx_std_17)
set_target_properties(edgeai_video_pipeline_tests PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
target_link_libraries(edgeai_video_pipeline_tests PRIVATE edgeai_common)
edgeai_enable_warnings(edgeai_video_pipeline_tests)
add_test(NAME edgeai_video_pipeline_tests COMMAND edgeai_video_pipeline_tests)

add_executable(edgeai_benchmark_ort
    apps/benchmark_ort.cpp
)
target_compile_features(edgeai_benchmark_ort PRIVATE cxx_std_17)
set_target_properties(edgeai_benchmark_ort PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
    BUILD_RPATH "${ONNXRUNTIME_ROOT}/lib"
)
target_compile_definitions(edgeai_benchmark_ort PRIVATE
    EDGEAI_BUILD_TYPE="${CMAKE_BUILD_TYPE}"
)
target_link_libraries(edgeai_benchmark_ort PRIVATE edgeai_ort_backend)
edgeai_enable_warnings(edgeai_benchmark_ort)

add_executable(edgeai_ncnn_model_smoke
    apps/ncnn_model_smoke.cpp
)
target_compile_features(edgeai_ncnn_model_smoke PRIVATE cxx_std_17)
set_target_properties(edgeai_ncnn_model_smoke PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
target_link_libraries(edgeai_ncnn_model_smoke PRIVATE ncnn)
edgeai_enable_warnings(edgeai_ncnn_model_smoke)
add_test(NAME edgeai_ncnn_model_smoke_invalid_args COMMAND edgeai_ncnn_model_smoke)
set_tests_properties(edgeai_ncnn_model_smoke_invalid_args PROPERTIES WILL_FAIL TRUE)
add_test(NAME edgeai_benchmark_ort_invalid_args COMMAND edgeai_benchmark_ort)
set_tests_properties(edgeai_benchmark_ort_invalid_args PROPERTIES WILL_FAIL TRUE)

add_executable(edgeai_benchmark_tests
    tests/test_benchmark.cpp
)
target_compile_features(edgeai_benchmark_tests PRIVATE cxx_std_17)
set_target_properties(edgeai_benchmark_tests PROPERTIES
    CXX_STANDARD 17
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
)
target_link_libraries(edgeai_benchmark_tests PRIVATE edgeai_common)
edgeai_enable_warnings(edgeai_benchmark_tests)
add_test(NAME edgeai_benchmark_tests COMMAND edgeai_benchmark_tests)
