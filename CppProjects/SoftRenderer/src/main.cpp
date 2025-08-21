#include <opencv2/opencv.hpp>

int main(int argc, char** argv) {

	int Key = 0;
	int FrameRate = 120;
	int TimePerFrame = 1.0f / 120 * 1000; // mill-second
	std::string ImagePath = R"(H:\workArea\UnrealProjects\interview\CppProjects\SoftRenderer\data\1.png)";

	while( Key != 27 )
	{
		cv::Mat Image = cv::imread( ImagePath, cv::IMREAD_COLOR );
		cv::Mat GrayImage;
		cv::cvtColor(Image, GrayImage, cv::COLOR_BGR2GRAY);
		cv::imshow("Image",GrayImage);
		Key = cv::waitKey(TimePerFrame);
	}

	return 0;
}