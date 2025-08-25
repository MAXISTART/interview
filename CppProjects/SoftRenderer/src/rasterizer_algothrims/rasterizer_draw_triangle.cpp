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
	// https://zhuanlan.zhihu.com/p/140926917

	// Get the bounding box of the triangle
	float Min_x = std::min( {P0.x(), P1.x(), P2.x()} );
	float Max_x = std::max({ P0.x(), P1.x(), P2.x() });
	float Min_y = std::min({ P0.y(), P1.y(), P2.y() });
	float Max_y = std::max({ P0.y(), P1.y(), P2.y() });

	auto CrossProduct = [](const Eigen::Vector2f& A, const Eigen::Vector2f& B, const Eigen::Vector2f& C)->float
	{
		// AB X AC
		return (B.x() - A.x()) * (C.y() - A.y()) - (C.x() - A.x()) * (B.y() - A.y());
	};

	// Make points counterclockwise
	std::vector<Eigen::Vector2f> Pts = { P0, P1, P2 };

	if(CrossProduct(Pts[0], Pts[1], Pts[2]) < 0)
	{
		std::swap(Pts[1], Pts[2]);
	}

	for(int x = Min_x; x <= Max_x; x++)
	{
		for(int y = Min_y; y <= Max_y; y++)
		{
			float Edge_1 = CrossProduct(Pts[0], Pts[1], Eigen::Vector2f(x, y));
			float Edge_2 = CrossProduct(Pts[1], Pts[2], Eigen::Vector2f(x, y));
			float Edge_3 = CrossProduct(Pts[2], Pts[0], Eigen::Vector2f(x, y));

			if(Edge_1 >= 0 && Edge_2 >= 0 && Edge_3 >= 0)
			{
				SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
			}
		}
	}
}

void Rasterizer::DrawTriangle2D_EdgeOpt(const Eigen::Vector2f& P0, const Eigen::Vector2f& P1, const Eigen::Vector2f& P2,
	const Eigen::Vector3f& Color)
{
	// https://zhuanlan.zhihu.com/p/140926917

	// Get the bounding box of the triangle
	float Min_x = std::min({ P0.x(), P1.x(), P2.x() });
	float Max_x = std::max({ P0.x(), P1.x(), P2.x() });
	float Min_y = std::min({ P0.y(), P1.y(), P2.y() });
	float Max_y = std::max({ P0.y(), P1.y(), P2.y() });

	auto CrossProduct = [](const Eigen::Vector2f& A, const Eigen::Vector2f& B, const Eigen::Vector2f& C)->float
		{
			// AB X AC
			return (B.x() - A.x()) * (C.y() - A.y()) - (C.x() - A.x()) * (B.y() - A.y());
		};

	// Make points counterclockwise
	std::vector<Eigen::Vector2f> Pts = { P0, P1, P2 };

	if (CrossProduct(Pts[0], Pts[1], Pts[2]) < 0)
	{
		std::swap(Pts[1], Pts[2]);
	}

	float F1 = Pts[0].x() * Pts[1].y() - Pts[0].y() * Pts[1].x();
	float F2 = Pts[1].x() * Pts[2].y() - Pts[1].y() * Pts[2].x();
	float F3 = Pts[2].x() * Pts[0].y() - Pts[2].y() * Pts[0].x();

	float I1 = Pts[0].y() - Pts[1].y();
	float I2 = Pts[1].y() - Pts[2].y();
	float I3 = Pts[2].y() - Pts[0].y();

	float J1 = Pts[1].x() - Pts[0].x();
	float J2 = Pts[2].x() - Pts[1].x();
	float J3 = Pts[0].x() - Pts[2].x();

	for (int x = Min_x; x <= Max_x; x++)
	{
		for (int y = Min_y; y <= Max_y; y++)
		{
			float Edge_1 = I1 * x + J1 * y + F1;
			float Edge_2 = I2 * x + J2 * y + F2;
			float Edge_3 = I3 * x + J3 * y + F3;

			if (Edge_1 >= 0 && Edge_2 >= 0 && Edge_3 >= 0)
			{
				SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
			}
		}
	}
}