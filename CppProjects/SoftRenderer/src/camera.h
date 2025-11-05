// getView
// getRenderTarget

#include "Eigen/Eigen"

class Camera
{
public:
	void Update(float DeltaTime);
	void UpdateRenderData();
	float GetFov();

	Eigen::Matrix4f GetViewMatrix() const;
	Eigen::Matrix4f GetProjectionMatrix() const;

	std::vector<Eigen::Vector3f> GetRenderTarget() const;

private:
	Eigen::Vector4f mPosition;

	Eigen::Vector4f mNearPlane;
	Eigen::Vector4f mFarPlane;
	Eigen::Vector4f mAspectRatio;
	Eigen::Vector4f mViewWidth;

	std::vector<Eigen::Vector3f> mRenderTarget;
};