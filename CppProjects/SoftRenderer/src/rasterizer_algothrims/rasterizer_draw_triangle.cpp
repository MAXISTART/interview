#include "Rasterizer.h"

void Rasterizer::DrawTriangle2D_Scan(const Eigen::Vector2f& P0, const Eigen::Vector2f& P1, const Eigen::Vector2f& P2,
	const Eigen::Vector3f& Color)
{
	// https://zhuanlan.zhihu.com/p/140926917

	std::vector<Eigen::Vector2f> Points = { P0, P1, P2 };
	std::sort(Points.begin(), Points.end(), [](const Eigen::Vector2f& A, const Eigen::Vector2f& B)->bool
		{
			return A.y() < B.y();
		}
	);

	for(int y = Points[0].y(); y <= Points[1].y(); y++)
	{
		int x0 = (y - Points[0].y()) / (Points[1].y() - Points[0].y()) * (Points[1].x() - Points[0].x()) + Points[0].x();
		int x1 = (y - Points[0].y()) / (Points[2].y() - Points[0].y()) * (Points[2].x() - Points[0].x()) + Points[0].x();
		for( int x = x0; x < x1; x++ )
		{
			SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
		}
	}

	for (int y = Points[1].y(); y <= Points[2].y(); y++)
	{
		int x0 = (y - Points[1].y()) / (Points[2].y() - Points[1].y()) * (Points[2].x() - Points[1].x()) + Points[1].x();
		int x1 = (y - Points[0].y()) / (Points[2].y() - Points[0].y()) * (Points[2].x() - Points[0].x()) + Points[0].x();
		for (int x = x0; x < x1; x++)
		{
			SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
		}
	}
}

void Rasterizer::DrawTriangle2D_Edge(const Eigen::Vector2f& P0, const Eigen::Vector2f& P1, const Eigen::Vector2f& P2,
	const Eigen::Vector3f& Color)
{

}
