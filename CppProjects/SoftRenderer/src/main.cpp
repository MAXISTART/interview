#include <opencv2/opencv.hpp>
#include "rasterizer.h"

int main(int argc, char** argv) {

	int Key = 0;
	int FrameRate = 120;
	int TimePerFrame = 1.0f / 120 * 1000; // mill-second
	float WindowScale = 0.75;

	// Init
	Rasterizer& Rst = Rasterizer();
	Rst.ResizeBuffer(1920 * WindowScale, 1080 * WindowScale);
	Rst.ClearBuffer(Eigen::Vector3f(0.0, 1.0, 0.0));

	// Draw lines
	Rst.DrawLine2D(Eigen::Vector2f(25, 25), Eigen::Vector2f(1320, 25), Eigen::Vector3f(1.0, 0.0, 0.0));

	// Draw triangles
	Rst.DrawTriangle2D(Eigen::Vector2f(300, 300), Eigen::Vector2f(400, 500), Eigen::Vector2f(500, 200), Eigen::Vector3f(0.0, 0.0, 1.0));
	// Rst.DrawTriangle2D(Eigen::Vector2f(200, 200), Eigen::Vector2f(800, 300), Eigen::Vector2f(400, 700), Eigen::Vector3f(1.0, 1.0, 0.0));
	Rst.DrawTriangle2D(Eigen::Vector2f(400, 700), Eigen::Vector2f(800, 300), Eigen::Vector2f(200, 200), Eigen::Vector3f(1.0, 1.0, 0.0));


	while( Key != 27 )
	{
		// Render
		cv::Mat RGB_RenderTarget( Rst.GetHeight(), Rst.GetWidth(), CV_32FC3, Rst.GetBuffer().data() );
		cv::Mat BGR_RenderTarget;
		cv::cvtColor(RGB_RenderTarget, BGR_RenderTarget, cv::COLOR_RGB2BGR);
		cv::imshow("Game", BGR_RenderTarget);
		Key = cv::waitKey(TimePerFrame);
	}

	return 0;
}