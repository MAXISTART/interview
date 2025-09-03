#include "Eigen/Eigen"


class Object
{
public:
	Object( const std::vector<Eigen::Vector4f>& Vertexes, const Eigen::Vector4f& Position, const Eigen::Vector4f& Scale );

	std::vector<Eigen::Vector4f>& GetVertexes() const;
	Eigen::Matrix4f GetWorldMatrix() const;

private:

	std::vector<Eigen::Vector4f> mVertexes;
	Eigen::Vector4f mPosition;
	Eigen::Vector4f mScale;
};