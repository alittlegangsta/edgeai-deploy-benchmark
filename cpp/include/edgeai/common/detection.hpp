#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace edgeai::common {

struct Size2D {
    int width{0};
    int height{0};
};

struct Padding {
    int left{0};
    int top{0};
    int right{0};
    int bottom{0};
};

struct Box {
    float x1{0.0F};
    float y1{0.0F};
    float x2{0.0F};
    float y2{0.0F};
};

struct LetterboxMetadata {
    Size2D original_size;
    Size2D target_size;
    Size2D resized_size;
    double scale{0.0};
    Padding padding;
    std::array<int, 3> pad_color_bgr{{114, 114, 114}};
    std::string interpolation{"cv2.INTER_LINEAR"};
    std::vector<std::string> transforms;
};

struct InputTensor {
    std::array<std::int64_t, 4> shape{{0, 0, 0, 0}};
    std::vector<float> values;
};

struct Detection {
    std::size_t rank{0};
    std::size_t candidate_index{0};
    int class_id{-1};
    std::string class_name;
    float objectness{0.0F};
    float class_score{0.0F};
    float confidence{0.0F};
    Box box_xywh_input;
    Box box_xyxy_input;
    Box box_xyxy_source;
};

struct StageTimingsMs {
    double input_read{0.0};
    double preprocess{0.0};
    double inference{0.0};
    double postprocess{0.0};
    double visualization{0.0};
    double output_write{0.0};
};

}  // namespace edgeai::common
