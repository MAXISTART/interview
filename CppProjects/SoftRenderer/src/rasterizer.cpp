#include "Rasterizer.h"

std::vector<Eigen::Vector3f>& Rasterizer::GetBuffer()
{
	return mBuffer;
}

void Rasterizer::ResizeBuffer( int Width, int Height )
{
	mBuffer.resize( Width * Height );
	mWidth = Width;
	mHeight = Height;
}

void Rasterizer::ClearBuffer( const Eigen::Vector3f& Color )
{
	std::fill( mBuffer.begin(), mBuffer.end(), Color );
}

void Rasterizer::DrawLine2D(const Eigen::Vector2f& Start, const Eigen::Vector2f& End, const Eigen::Vector3f& Color)
{
	DrawLine2D_BRH_Int(Start, End, Color);
}

void Rasterizer::DrawTriangle2D(const Eigen::Vector2f& P0, const Eigen::Vector2f& P1, const Eigen::Vector2f& P2,
	const Eigen::Vector3f& Color)
{
	DrawTriangle2D_Scan(P0, P1, P2, Color);
}

void Rasterizer::SetPixel( const Eigen::Vector3f& Point, const Eigen::Vector3f& Color )
{
	if( Point.x() < 0 || Point.x() >= mWidth || Point.y() < 0 || Point.y() >= mHeight ) return;
	int Index = (int)Point.x() + (int)Point.y() * mWidth;
	mBuffer[Index] = Color;
}

