# TARGET

这个项目的目标是通过模拟现代 gpu 的渲染管线流程，去绘制一个会动的3D模型，这个会动并不是说骨骼这种更加上层的东西，而只是有一个主体的游戏 while 循环。
通过这个项目来理清楚整个 gpu 渲染管线每个 stage 中涉及到的算法原理是什么

1) 应用阶段（CPU 侧，非 GPU stage）
- 场景管理、剔除、批处理、命令录制（例如 Vulkan Command Buffer）。
- 生成顶点/实例数据、绑定资源（纹理、缓冲、常量/推常量）。

2) 输入装配器（Input Assembler, IA）
- 从顶点/索引缓冲读取顶点流，按拓扑组织成点/线/三角形/patch。
- 不做计算，仅装配与步进。

3) 顶点着色器（Vertex Shader, VS）
- 对每个顶点执行：坐标变换（模型→世界→视图→裁剪空间）、法线变换、顶点属性输出。
- 必需阶段（在现代 API 中）。

4) 细分控制着色器 / 曲面细分（Tessellation Control Shader, TCS 或 Hull Shader）
- 可选。设置细分因子，控制 patch 的细分密度（适配视距、曲率等）。

5) 细分评估着色器（Tessellation Evaluation Shader, TES 或 Domain Shader）
- 可选。根据细分坐标评估曲面位置与属性，输出到裁剪空间。

6) 几何着色器（Geometry Shader, GS）
- 可选。以图元为粒度，可以放大/裁剪/生成额外图元（如法线可视化、阴影体生成）。
- 现代实时渲染中较少用，性能一般不佳。

7) 视口与裁剪（Clipping & Viewport Transform）
- 齐次裁剪空间裁剪（视锥、用户裁剪平面）。
- 透视除法，NDC 映射到屏幕空间；应用视口与剪裁矩形。

8) 光栅化（Rasterization）
- 将三角形离散化为片段（像素候选），插值顶点输出到片段属性。
- 早期深度/模板测试（Early-Z/Stencil）与背面剔除可能在此或更早进行。

9) 片段/像素着色器（Fragment/Pixel Shader, FS/PS）
- 对每个片段着色：采样纹理、BRDF 光照、阴影、法线/粗糙度等材质处理。
- 可写多个颜色附件（MRT），可输出自定义数据（如延迟渲染的 G-buffer）。

10) 片段测试与输出合并（Per-sample Ops & Output Merger）
- 深度测试、模板测试、Alpha-to-coverage、混合（Blending）、逻辑操作、抖动、sRGB 转换。
- 通过测试的片段写入颜色/深度/模板附件（Render Targets / Framebuffer）。

11) 显示合成（Presentation/Composition）
- 交换链呈现到屏幕；操作系统可能有合成器（桌面合成）进行最终合成。

简单记忆（经典栅格管线必选/常见顺序）
IA → VS → [Tess(TCS/TES)] → [GS] → Clipping/Viewport → Rasterizer → FS → 深度/模板/混合 → 输出/呈现

具体 API 对应：
- Direct3D 11/12：IA → VS → [HS/TCS] → [DS/TES] → [GS] → RS → PS → OM
- OpenGL：VAO/IA → VS → [TCS] → [TES] → [GS] → Rasterizer → FS → FBO
- Vulkan：输入装配 → 顶点 → [细分控制/评估] → [几何] → 光栅化 → 片段 → 颜色混合/深度模板 → 呈现队列


# STEPS

## STEP - 1

找到合适的库来build最近本的项目，这个库，实现的功能就是，传入 2D 坐标点，以及这个坐标的颜色，绘制一个 2D 画面即可

## STEP - 2

实现 2D 平面的一些图形绘制，直线，三角形，因为这是最底层的绘制方法（暂时不用考虑四边形），其中应该涉及 三角形 重心坐标推导

## STEP - 3

2D旋转矩阵，3D旋转矩阵推导，MVP 矩阵推导，三维空间三角形的绘制


## STEP - 4

模型的读取以及绘制

##  STEP - 5

模拟 vertex shader, pixel shader

## STEP - 6

Clip stage 的实现
