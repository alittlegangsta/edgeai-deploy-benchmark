#include <opencv2/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/imgproc.hpp>

#include <iostream>

int main() {
    cv::Mat image(240, 320, CV_8UC3, cv::Scalar(16, 16, 16));

    cv::rectangle(image, cv::Rect(20, 20, 280, 180), cv::Scalar(0, 200, 0), 2);
    cv::circle(image, cv::Point(160, 110), 48, cv::Scalar(200, 0, 0), 3);
    cv::putText(
        image,
        "Anlogic DR1M90",
        cv::Point(20, 225),
        cv::FONT_HERSHEY_SIMPLEX,
        0.5,
        cv::Scalar(240, 240, 240),
        1,
        cv::LINE_AA);

    if (!cv::imwrite("opencv_smoke.png", image)) {
        std::cerr << "imwrite_failed\n";
        return 2;
    }

    std::cout << "opencv_version=" << CV_VERSION << '\n';
    std::cout << "width=" << image.cols << '\n';
    std::cout << "height=" << image.rows << '\n';
    std::cout << "channels=" << image.channels() << '\n';
    return 0;
}
