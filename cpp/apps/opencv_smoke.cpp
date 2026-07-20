#include <exception>
#include <filesystem>
#include <iostream>
#include <string>

#include <opencv2/core.hpp>
#include <opencv2/core/version.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

int main(int argc, char* argv[]) {
    constexpr int image_width = 640;
    constexpr int image_height = 360;
    const std::filesystem::path default_output_path =
        "results/images/opencv_smoke.png";

    std::cout << "Application: edgeai_opencv_smoke\n"
              << "__cplusplus: " << __cplusplus << '\n'
              << "OpenCV version: " << CV_VERSION << '\n';

    if (argc > 2) {
        std::cerr << "Usage: " << argv[0] << " [output_path]\n";
        return 2;
    }

    try {
        const std::filesystem::path output_path =
            argc == 2 ? std::filesystem::path(argv[1]) : default_output_path;
        const std::filesystem::path parent_path = output_path.parent_path();

        if (!parent_path.empty()) {
            std::filesystem::create_directories(parent_path);
        }

        cv::Mat image(image_height, image_width, CV_8UC3,
                      cv::Scalar(34, 40, 49));
        cv::rectangle(image, cv::Point(70, 70), cv::Point(570, 290),
                      cv::Scalar(90, 190, 240), 4);
        cv::putText(image, "OpenCV C++17 smoke test", cv::Point(105, 190),
                    cv::FONT_HERSHEY_SIMPLEX, 0.85,
                    cv::Scalar(235, 235, 235), 2, cv::LINE_AA);

        if (!cv::imwrite(output_path.string(), image)) {
            std::cerr << "Error: failed to write image to " << output_path
                      << '\n';
            return 1;
        }

        const cv::Mat decoded_image =
            cv::imread(output_path.string(), cv::IMREAD_COLOR);
        if (decoded_image.empty()) {
            std::cerr << "Error: failed to read image from " << output_path
                      << '\n';
            return 1;
        }

        if (decoded_image.cols != image_width ||
            decoded_image.rows != image_height) {
            std::cerr << "Error: unexpected image dimensions "
                      << decoded_image.cols << 'x' << decoded_image.rows
                      << "; expected " << image_width << 'x' << image_height
                      << '\n';
            return 1;
        }

        std::cout << "Output path: " << output_path << '\n'
                  << "Verified dimensions: " << decoded_image.cols << 'x'
                  << decoded_image.rows << '\n';
        return 0;
    } catch (const std::exception& exception) {
        std::cerr << "Error: " << exception.what() << '\n';
        return 1;
    }
}
