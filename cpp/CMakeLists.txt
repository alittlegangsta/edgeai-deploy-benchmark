cmake_minimum_required(VERSION 3.16)

project(edgeai_deploy_benchmark LANGUAGES CXX)

if(NOT CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(CMAKE_CXX_EXTENSIONS OFF)

find_package(OpenCV 4 REQUIRED COMPONENTS core imgproc imgcodecs)

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
    src/common/config.cpp
    src/common/preprocess.cpp
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
