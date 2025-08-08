import os
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('p4v_project_manager.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('P4VProjectManager')


class BuildStatus(Enum):
    """构建状态枚举"""
    IDLE = "idle"  # 空闲，等待任务
    RUNNING = "running"  # 正在执行构建
    COMPLETED = "completed"  # 构建完成
    FAILED = "failed"  # 构建失败
    TIMEOUT = "timeout"  # 构建超时


@dataclass
class ProjectWindow:
    """项目窗口信息"""
    project_name: str
    process: subprocess.Popen
    command_file: Path  # 命令文件，用于传递新的构建命令
    status_file: Path  # 状态文件，用于读取构建状态
    main_batch_file: Path  # 主批处理文件（持续运行的）
    status: BuildStatus = BuildStatus.IDLE
    last_build_time: float = 0
    current_script: str = ""


class P4VProjectManager:
    """P4V项目管理器"""

    def __init__(self, config_path: str = 'config.json'):
        """
        初始化P4V项目管理器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.projects = {}
        self.test_mode = False
        self.default_check_interval = 300
        self.build_timeout = 10800  # 默认3小时超时

        # 每个项目的CMD窗口
        self.project_windows: Dict[str, ProjectWindow] = {}

        # 记录项目的最后同步版本
        self.last_sync_versions: Dict[str, str] = {}

        # 测试模式下的构建计数
        self.test_build_count: Dict[str, int] = {}

        # 加载并验证配置
        self.load_and_validate_config()

        # 初始化所有项目的CMD窗口
        self.initialize_project_windows()

    def load_and_validate_config(self):
        """加载并验证配置文件"""
        logger.info("=" * 60)
        logger.info("P4V Project Manager 启动")
        logger.info("=" * 60)

        # 加载配置文件
        logger.info(f"加载配置文件: {self.config_path}")
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            logger.error(f"配置文件不存在: {self.config_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise
        except Exception as e:
            logger.error(f"无法加载配置文件: {e}")
            raise

        # 提取配置项
        self.projects = self.config.get('projects', {})
        self.test_mode = self.config.get('test_mode', False)
        self.default_check_interval = self.config.get('default_check_interval', 300)
        self.build_timeout = self.config.get('build_timeout', 10800)

        # 设置日志级别
        log_level = self.config.get('log_level', 'INFO')
        logger.setLevel(getattr(logging, log_level))

        logger.info(f"配置加载成功")
        logger.info(f"- 项目数量: {len(self.projects)}")
        logger.info(f"- 测试模式: {self.test_mode}")
        logger.info(f"- 默认检查间隔: {self.default_check_interval}秒")
        logger.info(f"- 构建超时时间: {self.build_timeout}秒")

        # 验证配置
        self.validate_configuration()

    def validate_configuration(self):
        """验证所有配置的有效性"""
        logger.info("-" * 60)
        logger.info("开始验证配置...")

        errors = []
        warnings = []

        # 验证P4连接（非测试模式）
        if not self.test_mode:
            logger.info("检查Perforce连接...")
            if not self.check_p4_connection():
                errors.append("无法连接到Perforce服务器")

        # 验证每个项目的配置
        for project_name, project_config in self.projects.items():
            logger.info(f"验证项目: {project_name}")

            # 检查必需字段
            required_fields = ['scripts_path', 'build_scripts']
            if not self.test_mode:
                required_fields.append('depot_path')

            for field in required_fields:
                if field not in project_config:
                    errors.append(f"项目 {project_name} 缺少必需字段: {field}")

            # 检查脚本路径
            scripts_path = project_config.get('scripts_path', '')
            if scripts_path:
                scripts_path_obj = Path(scripts_path)
                if not scripts_path_obj.exists():
                    errors.append(f"项目 {project_name} 的脚本路径不存在: {scripts_path}")
                else:
                    # 检查每个脚本文件
                    build_scripts = project_config.get('build_scripts', [])
                    for script in build_scripts:
                        script_file = scripts_path_obj / script
                        if not script_file.exists():
                            errors.append(f"项目 {project_name} 的脚本文件不存在: {script_file}")
                        else:
                            logger.info(f"  ✓ 脚本文件存在: {script}")

            # 检查Depot路径格式（非测试模式）
            if not self.test_mode:
                depot_path = project_config.get('depot_path', '')
                if depot_path and not depot_path.startswith('//'):
                    warnings.append(f"项目 {project_name} 的depot路径格式可能不正确: {depot_path}")

        # 输出验证结果
        logger.info("-" * 60)
        if warnings:
            logger.warning("配置警告:")
            for warning in warnings:
                logger.warning(f"  ⚠ {warning}")

        if errors:
            logger.error("配置错误:")
            for error in errors:
                logger.error(f"  ✗ {error}")
            raise ValueError(f"配置验证失败，发现 {len(errors)} 个错误")

        logger.info("✓ 配置验证通过")
        logger.info("-" * 60)

    def check_p4_connection(self) -> bool:
        """检查P4连接是否正常"""
        try:
            result = subprocess.run(
                'p4 info',
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info("  ✓ Perforce连接正常")
                return True
            else:
                logger.error(f"  ✗ Perforce连接失败: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            logger.error("  ✗ Perforce连接超时")
            return False
        except Exception as e:
            logger.error(f"  ✗ 检查Perforce连接时出错: {e}")
            return False

    def initialize_project_windows(self):
        """为每个项目初始化CMD窗口"""
        logger.info("-" * 60)
        logger.info("初始化项目窗口...")

        for project_name, project_config in self.projects.items():
            scripts_path = Path(project_config['scripts_path'])

            # 创建控制文件路径
            command_file = scripts_path / f"_command_{project_name}.txt"
            status_file = scripts_path / f"_status_{project_name}.txt"
            main_batch_file = scripts_path / f"_monitor_{project_name}.bat"

            # 清理旧文件
            for file_path in [command_file, status_file]:
                if file_path.exists():
                    file_path.unlink()

            # 创建初始命令文件（空文件表示等待命令）
            command_file.write_text("WAIT", encoding='utf-8')

            # 创建主批处理文件（持续运行的监控脚本）
            self.create_monitor_batch(main_batch_file, project_name, project_config,
                                      command_file, status_file)

            # 启动CMD窗口
            window_title = f"P4V Monitor: {project_name}"
            cmd_command = f'start "{window_title}" cmd /k "{main_batch_file}"'

            process = subprocess.Popen(
                cmd_command,
                shell=True,
                cwd=scripts_path
            )

            # 创建ProjectWindow对象
            project_window = ProjectWindow(
                project_name=project_name,
                process=process,
                command_file=command_file,
                status_file=status_file,
                main_batch_file=main_batch_file,
                status=BuildStatus.IDLE
            )

            self.project_windows[project_name] = project_window
            self.test_build_count[project_name] = 0
            logger.info(f"✓ 项目 {project_name} 的监控窗口已启动")

        logger.info("-" * 60)

    def create_monitor_batch(self, batch_file: Path, project_name: str,
                             project_config: Dict, command_file: Path,
                             status_file: Path):
        """创建监控批处理文件（持续运行）"""
        scripts_path = project_config['scripts_path']
        build_scripts = project_config.get('build_scripts', [])

        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write('@echo off\n')
            f.write('setlocal enabledelayedexpansion\n')
            f.write(f'title P4V Monitor: {project_name}\n')
            f.write(f'echo ========================================\n')
            f.write(f'echo P4V Project Manager - Monitor Mode\n')
            f.write(f'echo ========================================\n')
            f.write(f'echo Project: {project_name}\n')
            f.write(f'echo Scripts Path: {scripts_path}\n')
            f.write(f'echo Start Time: %date% %time%\n')
            f.write(f'echo ========================================\n')
            f.write('echo.\n')
            f.write('echo Monitoring for build commands...\n')
            f.write('echo.\n')

            # 主循环
            f.write(':MAIN_LOOP\n')

            # 读取命令文件
            f.write(f'set /p COMMAND=<"{command_file}" 2>nul\n')

            # 检查是否有构建命令
            f.write('if "!COMMAND!"=="BUILD" (\n')
            f.write('    echo.\n')
            f.write('    echo ========================================\n')
            f.write('    echo New build request received!\n')
            f.write('    echo Time: %date% %time%\n')
            f.write('    echo ========================================\n')
            f.write('    echo.\n')

            # 更新状态为运行中
            f.write(f'    echo RUNNING > "{status_file}"\n')

            # 重置命令文件
            f.write(f'    echo WAIT > "{command_file}"\n')

            # 执行所有构建脚本
            for i, script in enumerate(build_scripts, 1):
                script_full_path = Path(scripts_path) / script

                f.write(f'    echo [{i}/{len(build_scripts)}] Executing: {script}\n')
                f.write(f'    echo ----------------------------------------\n')
                f.write(f'    echo RUNNING:{script} > "{status_file}"\n')

                # 执行脚本
                f.write(f'    call "{script_full_path}" "{project_name}"\n')

                # 检查错误
                f.write('    if errorlevel 1 (\n')
                f.write(f'        echo [ERROR] Script {script} failed with error code !errorlevel!\n')
                f.write(f'        echo ERROR:{script}:!errorlevel! >> "{status_file}"\n')
                f.write('    ) else (\n')
                f.write(f'        echo [SUCCESS] Script {script} completed\n')
                f.write(f'        echo COMPLETED:{script} >> "{status_file}"\n')
                f.write('    )\n')
                f.write('    echo.\n')

            # 构建完成
            f.write('    echo ========================================\n')
            f.write('    echo Build completed!\n')
            f.write('    echo End Time: %date% %time%\n')
            f.write('    echo ========================================\n')
            f.write('    echo.\n')
            f.write(f'    echo IDLE > "{status_file}"\n')
            f.write('    echo Waiting for next build command...\n')
            f.write('    echo.\n')

            f.write(') else if "!COMMAND!"=="EXIT" (\n')
            f.write('    echo.\n')
            f.write('    echo Received exit command. Shutting down...\n')
            f.write('    exit\n')
            f.write(')\n')

            # 等待一秒后继续循环
            f.write('timeout /t 1 /nobreak >nul\n')
            f.write('goto MAIN_LOOP\n')

    def check_perforce_changes(self, depot_path: str) -> Tuple[bool, Optional[str]]:
        """
        检查Perforce路径是否有更新

        Returns:
            (是否有更新, 最新版本号)
        """
        if self.test_mode:
            # 测试模式下总是返回有更新
            version = f"test_{int(time.time())}"
            return True, version

        try:
            cmd = f'p4 changes -m 1 "{depot_path}"'
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"P4命令执行失败: {result.stderr}")
                return False, None

            output = result.stdout.strip()
            if output:
                parts = output.split()
                if len(parts) >= 2 and parts[0] == "Change":
                    return True, parts[1]

            return False, None

        except Exception as e:
            logger.error(f"检查Perforce更新时出错: {e}")
            return False, None

    def trigger_build(self, project_name: str):
        """触发项目构建"""
        if project_name not in self.project_windows:
            logger.error(f"项目 {project_name} 的窗口不存在")
            return

        window = self.project_windows[project_name]

        # 检查窗口状态
        current_status = self.get_window_status(window)

        if current_status == BuildStatus.RUNNING:
            logger.info(f"项目 {project_name} 正在构建中，跳过新的构建请求")
            return

        logger.info(f"触发项目 {project_name} 的构建")

        # 写入构建命令
        window.command_file.write_text("BUILD", encoding='utf-8')
        window.status = BuildStatus.RUNNING
        window.last_build_time = time.time()

        # 测试模式下记录构建次数
        if self.test_mode:
            self.test_build_count[project_name] += 1
            logger.info(f"[测试模式] 项目 {project_name} 第 {self.test_build_count[project_name]} 次构建")

    def get_window_status(self, window: ProjectWindow) -> BuildStatus:
        """获取窗口当前状态"""
        try:
            if window.status_file.exists():
                status_text = window.status_file.read_text(encoding='utf-8').strip()

                if status_text == "IDLE":
                    return BuildStatus.IDLE
                elif status_text.startswith("RUNNING"):
                    return BuildStatus.RUNNING
                elif status_text.startswith("ERROR"):
                    return BuildStatus.FAILED
                elif status_text.startswith("COMPLETED"):
                    return BuildStatus.COMPLETED

            return BuildStatus.IDLE

        except Exception as e:
            logger.debug(f"读取状态文件出错: {e}")
            return BuildStatus.IDLE

    def monitor_windows(self):
        """监控所有窗口状态"""
        for project_name, window in self.project_windows.items():
            try:
                old_status = window.status
                new_status = self.get_window_status(window)

                # 状态变化时记录日志
                if old_status != new_status:
                    window.status = new_status

                    if new_status == BuildStatus.IDLE:
                        if old_status == BuildStatus.RUNNING:
                            elapsed_time = (time.time() - window.last_build_time) / 60
                            logger.info(f"项目 {project_name} 构建完成 (耗时: {elapsed_time:.1f} 分钟)")
                            if self.test_mode:
                                logger.info(
                                    f"[测试模式] 项目 {project_name} 已完成 {self.test_build_count[project_name]} 次构建")
                    elif new_status == BuildStatus.RUNNING:
                        # 读取正在执行的脚本
                        if window.status_file.exists():
                            status_text = window.status_file.read_text(encoding='utf-8').strip()
                            if status_text.startswith("RUNNING:"):
                                script_name = status_text.split(":", 1)[1]
                                if script_name != window.current_script:
                                    window.current_script = script_name
                                    logger.info(f"[{project_name}] 正在执行: {script_name}")
                    elif new_status == BuildStatus.FAILED:
                        logger.error(f"项目 {project_name} 构建失败")

                # 检查超时
                if window.status == BuildStatus.RUNNING:
                    elapsed_time = time.time() - window.last_build_time
                    if elapsed_time > self.build_timeout:
                        logger.error(f"项目 {project_name} 构建超时")
                        window.status = BuildStatus.TIMEOUT

            except Exception as e:
                logger.debug(f"监控窗口 {project_name} 时出错: {e}")

    def check_and_build_project(self, project_name: str, project_config: Dict):
        """检查项目更新并在需要时触发构建"""
        try:
            depot_path = project_config.get('depot_path', '')

            # 检查是否有更新
            has_changes, latest_version = self.check_perforce_changes(depot_path)

            # 判断是否需要构建
            last_version = self.last_sync_versions.get(project_name)

            if has_changes and latest_version != last_version:
                logger.info(f"检测到项目 {project_name} 有更新 (版本: {latest_version})")
                self.last_sync_versions[project_name] = latest_version

                # 触发构建
                self.trigger_build(project_name)

        except Exception as e:
            logger.error(f"检查项目 {project_name} 时出错: {e}")

    def shutdown(self):
        """关闭所有窗口"""
        logger.info("关闭所有项目窗口...")

        for project_name, window in self.project_windows.items():
            try:
                # 发送退出命令
                window.command_file.write_text("EXIT", encoding='utf-8')
                time.sleep(0.5)

                # 终止进程
                if window.process:
                    window.process.terminate()

                # 清理文件
                for file_path in [window.command_file, window.status_file, window.main_batch_file]:
                    if file_path.exists():
                        try:
                            file_path.unlink()
                        except:
                            pass

                logger.info(f"已关闭项目 {project_name} 的窗口")

            except Exception as e:
                logger.error(f"关闭项目 {project_name} 窗口时出错: {e}")

    def run(self):
        """主运行循环"""
        logger.info("=" * 60)
        logger.info("P4V Project Manager 开始运行")
        logger.info("=" * 60)

        if self.test_mode:
            # 测试模式：持续运行，定期触发构建来测试窗口重用
            logger.info("测试模式：进入监控循环")
            logger.info("测试模式下会每隔10秒检查并触发构建，测试窗口重用功能")
            logger.info("按 Ctrl+C 停止程序")
            logger.info("-" * 60)

            # 首次触发所有项目构建
            logger.info("第一轮：触发所有项目的构建")
            for project_name in self.projects.keys():
                self.trigger_build(project_name)
                time.sleep(1)

            # 进入测试循环
            test_interval = 10  # 测试模式下每10秒检查一次
            try:
                while True:
                    # 监控窗口状态
                    self.monitor_windows()

                    # 显示当前状态
                    active_builds = sum(1 for w in self.project_windows.values()
                                        if w.status == BuildStatus.RUNNING)
                    idle_projects = [name for name, w in self.project_windows.items()
                                     if w.status == BuildStatus.IDLE]

                    if active_builds > 0:
                        logger.info(f"当前活动构建数: {active_builds}")

                    # 每隔一段时间触发空闲项目的构建
                    if idle_projects:
                        logger.info(f"等待 {test_interval} 秒后触发空闲项目的构建...")

                        # 在等待期间继续监控
                        for _ in range(test_interval):
                            self.monitor_windows()
                            time.sleep(1)

                        # 触发空闲项目的构建（模拟检测到更新）
                        for project_name in idle_projects:
                            # 模拟版本更新
                            self.last_sync_versions[project_name] = f"test_{int(time.time())}"
                            logger.info(f"[测试模式] 模拟项目 {project_name} 有新的更新")
                            self.trigger_build(project_name)
                            time.sleep(1)
                    else:
                        # 所有项目都在构建，等待
                        time.sleep(5)

            except KeyboardInterrupt:
                logger.info("接收到中断信号，正在关闭...")
                self.shutdown()
                logger.info("P4V Project Manager 已关闭")

        else:
            # 正常模式：定期检查更新
            try:
                while True:
                    logger.info(f"检查项目更新... ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})")

                    # 检查所有项目
                    for project_name, project_config in self.projects.items():
                        self.check_and_build_project(project_name, project_config)

                    # 监控窗口状态
                    self.monitor_windows()

                    # 显示当前状态
                    active_builds = sum(1 for w in self.project_windows.values()
                                        if w.status == BuildStatus.RUNNING)
                    if active_builds > 0:
                        logger.info(f"当前活动构建数: {active_builds}")

                    # 计算下次检查时间
                    min_interval = min(
                        project.get('check_interval', self.default_check_interval)
                        for project in self.projects.values()
                    )

                    logger.info(f"等待 {min_interval} 秒后进行下次检查...")

                    # 在等待期间继续监控窗口状态
                    wait_time = 0
                    while wait_time < min_interval:
                        self.monitor_windows()
                        time.sleep(5)
                        wait_time += 5

            except KeyboardInterrupt:
                logger.info("接收到中断信号，正在关闭...")
                self.shutdown()
                logger.info("P4V Project Manager 已关闭")
            except Exception as e:
                logger.error(f"运行时出错: {e}", exc_info=True)
                self.shutdown()
                raise


def main():
    """主函数"""
    try:
        # test_config = r"O:\Person\Projects\interview\TestProject\P4VProjectManager\TestFiles\config.json"
        # manager = P4VProjectManager(test_config)
        config = r"O:\Person\Projects\interview\TestProject\P4VProjectManager\config.json"
        manager = P4VProjectManager(config)
        manager.run()
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        return 1
    return 0


if __name__ == "__main__":
    exit(main())