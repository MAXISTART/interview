# P4V Project Manager

自动监控Perforce仓库变更并触发项目构建的工具。

## 特性

- 自动监控多个P4V项目的更新
- 支持并行构建多个项目（通过subprocess）
- 配置验证：启动时检查所有配置的有效性
- 实时监控构建进程状态
- 详细的日志记录
- 支持测试模式

## 配置说明

### 全局配置

- `max_parallel_builds`: 最大并行构建数
- `build_timeout`: 构建超时时间（秒）
- `default_check_interval`: 默认检查间隔（秒）
- `test_mode`: 是否启用测试模式
- `log_level`: 日志级别（DEBUG/INFO/WARNING/ERROR）

### 项目配置

每个项目需要配置：
- `depot_path`: P4V仓库路径
- `local_path`: 本地工作目录
- `scripts_path`: 构建脚本所在目录
- `build_scripts`: 构建脚本列表（按顺序执行）
- `check_interval`: 检查更新间隔（秒）

## 使用方法

1. 安装Python 3.8+
2. 配置config.json
3. 运行：`python p4v_project_manager.py`

## 测试模式

将`test_mode`设置为`true`可以在不连接P4V的情况下测试构建流程。