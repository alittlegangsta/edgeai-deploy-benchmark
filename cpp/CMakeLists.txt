cmake_minimum_required(VERSION 3.16)

project(edgeai_deploy_benchmark LANGUAGES CXX)

if(NOT CMAKE_CONFIGURATION_TYPES AND NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

set(CMAKE_CXX_EXTENSIONS OFF)

find_package(OpenCV 4 REQUIRED COMPONENTS core imgproc imgcodecs)

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

if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
    target_compile_options(edgeai_opencv_smoke PRIVATE
        -Wall
        -Wextra
        -Wpedantic
    )
endif()
