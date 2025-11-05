#include "camera.h"

void Camera::Update(float DeltaTime)
{
	UpdateRenderData();
}

void Camera::UpdateRenderData()
{
	GetViewMatrix();
}

float Camera::GetFov()
{
}

Eigen::Matrix4f Camera::GetViewMatrix() const
{
}

Eigen::Matrix4f Camera::GetProjectionMatrix() const
{
}

std::vector<Eigen::Vector3f> Camera::GetRenderTarget() const
{
}
