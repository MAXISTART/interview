#include "Rasterizer.h"

// Implementation of DDA
void Rasterizer::DrawLine2D_DDA(const Eigen::Vector2f& Start, const Eigen::Vector2f& End, const Eigen::Vector3f& Color)
{
	// https://zhuanlan.zhihu.com/p/20213658

	float dx = End.x() - Start.x();
	float dy = End.y() - Start.y();

	// Steps can ensure which dimension has the small increment
	float Steps = std::max(std::abs(dx), std::abs(dy));
	if (Steps == 0)
	{
		SetPixel(Eigen::Vector3f(Start.x(), Start.y(), 1.0), Color);
		return;
	}

	float x = Start.x();
	float y = Start.y();
	float x_inc = dx / Steps;
	float y_inc = dy / Steps;

	for (int i = 0; i < Steps; i++)
	{
		SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
		x += x_inc;
		y += y_inc;
	}
}

// Implementation of Bresenham float
void Rasterizer::DrawLine2D_BRH_Float(const Eigen::Vector2f& Start, const Eigen::Vector2f& End, const Eigen::Vector3f& Color)
{
	// https://zhuanlan.zhihu.com/p/535670908
	// the key of this algorithm is to decide when y(or x) should increase by 1
	// and unlike DDA, there's no y(or x) calculation here

	float x = std::min(Start.x(), End.x());
	float x1 = std::max(Start.x(), End.x());
	float y = (x == Start.x()) ? Start.y() : End.y();
	float y1 = (x1 == Start.x()) ? Start.y() : End.y();

	SetPixel(Eigen::Vector3f(x, y, 1.0), Color);

	float delta = 0;
	float middle = 0.5;
	float k = (y1 - y) / (x1 - x);
	float inverse_k = 1 / k;

	if (k < 1)
	{
		while (x < x1)
		{
			x++;
			delta += k;
			if (delta > middle)
			{
				middle += 1;
				y++;
			}
			SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
		}
	}
	else
	{
		while (y < y1)
		{
			y++;
			delta += inverse_k;
			if (delta > middle)
			{
				middle += 1;
				x++;
			}
			SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
		}
	}
}

// Implementation of Bresenham int
void Rasterizer::DrawLine2D_BRH_Int(const Eigen::Vector2f& Start, const Eigen::Vector2f& End,
	const Eigen::Vector3f& Color)
{
	// https://zhuanlan.zhihu.com/p/535670908
	// the difference between float version and int version is only the scale value, which can turn float to int

	int x = std::min(Start.x(), End.x());
	int x1 = std::max(Start.x(), End.x());
	int y = std::min(Start.y(), End.y());
	int y1 = std::max(Start.y(), End.y());

	SetPixel(Eigen::Vector3f(x, y, 1.0), Color);

	int dx = x1 - x;
	int dy = y1 - y;
	int delta = 0;
	int middle = 1;

	if (dy < dx)
	{
		int scale = 2 * (x1 - x);
		int k = 2 * (y1 - y);

		while (x < x1)
		{
			x++;
			delta += k;
			if (delta > middle)
			{
				middle += scale;
				y++;
			}
			SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
		}
	}
	else
	{
		int scale = 2 * (y1 - y);
		int k = 2 * (x1 - x);

		while (y < y1)
		{
			y++;
			delta += k;
			if (delta > middle)
			{
				middle += scale;
				x++;
			}
			SetPixel(Eigen::Vector3f(x, y, 1.0), Color);
		}

	}
}