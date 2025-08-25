#pragma once

#include "Eigen/Eigen"


class Rasterizer
{
public:

	std::vector<Eigen::Vector3f>& GetBuffer();

	void ResizeBuffer( int Width, int Height );
	void ClearBuffer( const Eigen::Vector3f& Color );

	void DrawLine2D( const Eigen::Vector2f& Start, const Eigen::Vector2f& End, const Eigen::Vector3f& Color );
	void DrawTriangle2D( const Eigen::Vector2f& P0, const Eigen::Vector2f& P1, const Eigen::Vector2f& P2, const Eigen::Vector3f& Color );

	void SetPixel( const Eigen::Vector3f& Point, const Eigen::Vector3f& Color );

	inline int GetWidth() const { return mWidth; }
	inline int GetHeight() const { return mHeight; }

protected:
	// draw lines
	void DrawLine2D_DDA(const Eigen::Vector2f& Start, const Eigen::Vector2f& End, const Eigen::Vector3f& Color);
	void DrawLine2D_BRH_Float(const Eigen::Vector2f& Start, const Eigen::Vector2f& End, const Eigen::Vector3f& Color);
	void DrawLine2D_BRH_Int(const Eigen::Vector2f& Start, const Eigen::Vector2f& End, const Eigen::Vector3f& Color);
	// draw triangles
	void DrawTriangle2D_Scan(const Eigen::Vector2f& P0, const Eigen::Vector2f& P1, const Eigen::Vector2f& P2, const Eigen::Vector3f& Color);
	void DrawTriangle2D_Edge(const Eigen::Vector2f& P0, const Eigen::Vector2f& P1, const Eigen::Vector2f& P2, const Eigen::Vector3f& Color);
	void DrawTriangle2D_EdgeOpt(const Eigen::Vector2f& P0, const Eigen::Vector2f& P1, const Eigen::Vector2f& P2, const Eigen::Vector3f& Color);

private:

	std::vector<Eigen::Vector3f> mBuffer;

	int mWidth;
	int mHeight;
};

