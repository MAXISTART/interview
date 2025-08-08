import os
import sys
import json
import time
import subprocess
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum
import threading
import re
import queue

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


class ProjectStatus(Enum):
    """项目状态枚举"""
    IDLE = "idle"  # 空闲
    PENDING_SYNC = "pending_sync"  # 等待同步
    SYNCING = "syncing"  # 正在同步
    PENDING_BUILD = "pending_build"  # 等待构建
    BUILDING = "building"  # 正在构建
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败


@dataclass
class ProjectWindow:
    """项目窗口信息"""
    project_name: str
    process: subprocess.Popen
    command_file: Path  # 命令文件，用于传递新的构建命令
    status_file: Path  # 状态文件，用于读取构建状态
    main_batch_file: Path  # 主批处理文件（持续运行的）
    build_status: str = "idle"  # 构建状态
    last_build_time: float = 0
    current_script: str = ""


@dataclass
class ProjectTask:
    """项目任务信息"""
    project_name: str
    depot_path: str
    local_path: str
    version: str
    status: ProjectStatus = ProjectStatus.IDLE
    sync_start_time: float = 0
    build_start_time: float = 0
    last_update_time: float = 0


@dataclass
class SyncProgress:
    """同步进度信息"""
    total_files: int = 0
    completed_files: int = 0
    current_file: str = ""
    bytes_transferred: int = 0
    current_action: str = ""  # updating, added, deleted
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


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
        self.sync_timeout = 7200  # 同步超时2小时

        # 每个项目的CMD窗口
        self.project_windows: Dict[str, ProjectWindow] = {}

        # 项目任务状态
        self.project_tasks: Dict[str, ProjectTask] = {}

        # 当前正在同步的项目
        self.current_sync_project: Optional[str] = None
        self.sync_process: Optional[subprocess.Popen] = None
        self.sync_thread: Optional[threading.Thread] = None
        self.sync_progress: SyncProgress = SyncProgress()

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
        self.sync_timeout = self.config.get('sync_timeout', 7200)

        # 设置日志级别
        log_level = self.config.get('log_level', 'INFO')
        logger.setLevel(getattr(logging, log_level))

        logger.info(f"配置加载成功")
        logger.info(f"- 项目数量: {len(self.projects)}")
        logger.info(f"- 测试模式: {self.test_mode}")
        logger.info(f"- 默认检查间隔: {self.default_check_interval}秒")
        logger.info(f"- 构建超时时间: {self.build_timeout}秒")
        logger.info(f"- 同步超时时间: {self.sync_timeout}秒")

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
                required_fields.extend(['depot_path', 'local_path'])

            for field in required_fields:
                if field not in project_config:
                    errors.append(f"项目 {project_name} 缺少必需字段: {field}")

            # 检查本地路径
            if not self.test_mode:
                local_path = project_config.get('local_path', '')
                if local_path:
                    local_path_obj = Path(local_path)
                    if not local_path_obj.exists():
                        warnings.append(f"项目 {project_name} 的本地路径不存在: {local_path}")
                        # 尝试创建
                        try:
                            local_path_obj.mkdir(parents=True, exist_ok=True)
                            logger.info(f"  已创建本地路径: {local_path}")
                        except Exception as e:
                            errors.append(f"无法创建本地路径 {local_path}: {e}")

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
            try:
                scripts_path = Path(project_config['scripts_path'])

                # 确保脚本路径存在
                if not scripts_path.exists():
                    logger.error(f"脚本路径不存在: {scripts_path}")
                    continue

                # 创建控制文件路径
                command_file = scripts_path / f"_command_{project_name}.txt"
                status_file = scripts_path / f"_status_{project_name}.txt"
                main_batch_file = scripts_path / f"_monitor_{project_name}.bat"

                # 清理旧文件
                for file_path in [command_file, status_file]:
                    if file_path.exists():
                        try:
                            file_path.unlink()
                        except Exception as e:
                            logger.warning(f"无法删除文件 {file_path}: {e}")

                # 创建初始命令文件
                try:
                    command_file.write_text("WAIT", encoding='utf-8')
                except Exception as e:
                    logger.error(f"无法创建命令文件 {command_file}: {e}")
                    continue

                # 创建主批处理文件（持续运行的监控脚本）
                try:
                    self.create_monitor_batch(main_batch_file, project_name, project_config,
                                              command_file, status_file)
                except Exception as e:
                    logger.error(f"无法创建批处理文件 {main_batch_file}: {e}")
                    continue

                # 启动CMD窗口
                window_title = f"P4V Monitor: {project_name}"
                cmd_command = f'start "{window_title}" cmd /k "{main_batch_file}"'

                try:
                    process = subprocess.Popen(
                        cmd_command,
                        shell=True,
                        cwd=str(scripts_path),
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        stdin=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
                    )

                    # 等待一下确保窗口启动
                    time.sleep(0.5)

                except Exception as e:
                    logger.error(f"无法启动项目 {project_name} 的CMD窗口: {e}")
                    continue

                # 创建ProjectWindow对象
                project_window = ProjectWindow(
                    project_name=project_name,
                    process=process,
                    command_file=command_file,
                    status_file=status_file,
                    main_batch_file=main_batch_file,
                    build_status="idle"
                )

                self.project_windows[project_name] = project_window
                self.test_build_count[project_name] = 0

                # 初始化项目任务状态
                self.project_tasks[project_name] = ProjectTask(
                    project_name=project_name,
                    depot_path=project_config.get('depot_path', ''),
                    local_path=project_config.get('local_path', ''),
                    version="",
                    status=ProjectStatus.IDLE
                )

                logger.info(f"✓ 项目 {project_name} 的监控窗口已启动")

            except Exception as e:
                logger.error(f"初始化项目 {project_name} 窗口时出错: {e}")
                import traceback
                logger.error(traceback.format_exc())

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

    def check_and_queue_project(self, project_name: str, project_config: Dict):
        """检查项目更新并加入队列"""
        try:
            task = self.project_tasks[project_name]

            # 如果项目不是空闲状态，跳过
            if task.status != ProjectStatus.IDLE:
                return

            depot_path = project_config.get('depot_path', '')
            local_path = project_config.get('local_path', '')

            # 检查是否有更新
            has_changes, latest_version = self.check_perforce_changes(depot_path)

            # 判断是否需要同步
            last_version = self.last_sync_versions.get(project_name)

            if has_changes and latest_version != last_version:
                logger.info(f"检测到项目 {project_name} 有更新 (版本: {latest_version})")

                # 更新任务信息
                task.depot_path = depot_path
                task.local_path = local_path
                task.version = latest_version
                task.status = ProjectStatus.PENDING_SYNC
                task.last_update_time = time.time()

                logger.info(f"项目 {project_name} 已加入同步队列")

        except Exception as e:
            logger.error(f"检查项目 {project_name} 时出错: {e}")

    def format_progress_bar(self, current: int, total: int, width: int = 40) -> str:
        """格式化进度条"""
        if total == 0:
            return f"[{'=' * width}]"

        percent = current / total
        filled = int(width * percent)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {percent * 100:.1f}%"

    def format_bytes(self, bytes_count: int) -> str:
        """格式化字节数"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.2f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.2f} PB"

    def display_sync_progress(self):
        """显示同步进度"""
        if not self.current_sync_project:
            return

        task = self.project_tasks[self.current_sync_project]
        progress = self.sync_progress
        elapsed_time = time.time() - task.sync_start_time

        # 清除之前的进度显示（在终端中）
        print("\033[2J\033[H", end='')  # 清屏并移动到顶部

        # 显示标题
        print("╔" + "═" * 78 + "╗")
        print(f"║ {'P4V 同步进度':^76} ║")
        print("╠" + "═" * 78 + "╣")

        # 项目信息
        print(f"║ 项目: {self.current_sync_project:<70} ║")
        print(f"║ 版本: {task.version:<70} ║")
        print(f"║ 路径: {task.depot_path[:70]:<70} ║")

        # 进度信息
        print("╠" + "═" * 78 + "╣")

        if progress.total_files > 0:
            # 进度条
            progress_bar = self.format_progress_bar(progress.completed_files, progress.total_files, 50)
            print(f"║ 进度: {progress_bar} {progress.completed_files}/{progress.total_files} ║")

            # 传输信息
            if progress.bytes_transferred > 0:
                bytes_str = self.format_bytes(progress.bytes_transferred)
                print(f"║ 已传输: {bytes_str:<67} ║")

            # 当前文件
            if progress.current_file:
                action_symbol = {
                    'updating': '↻',
                    'added': '+',
                    'deleted': '-',
                    'updated': '✓'
                }.get(progress.current_action, '•')

                file_display = f"{action_symbol} {progress.current_file}"
                if len(file_display) > 70:
                    file_display = file_display[:67] + "..."
                print(f"║ 文件: {file_display:<70} ║")
        else:
            print(f"║ {'正在连接到服务器...':^76} ║")

        # 时间信息
        minutes = int(elapsed_time / 60)
        seconds = int(elapsed_time % 60)
        print(f"║ 耗时: {minutes:02d}:{seconds:02d} {'':>62} ║")

        # 错误信息
        if progress.errors:
            print("╠" + "═" * 78 + "╣")
            print(f"║ {'错误:':^76} ║")
            for error in progress.errors[-3:]:  # 只显示最后3个错误
                if len(error) > 70:
                    error = error[:67] + "..."
                print(f"║ {error:<76} ║")

        print("╚" + "═" * 78 + "╝")

    def sync_output_reader(self, process: subprocess.Popen):
        """读取同步输出的线程函数"""
        try:
            while True:
                if process.stdout:
                    line = process.stdout.readline()
                    if not line:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # 解析P4同步输出
                    # 示例: //depot/path/file.txt#5 - updating /local/path/file.txt
                    if ' - ' in line:
                        parts = line.split(' - ', 1)
                        if len(parts) == 2:
                            file_info, action_info = parts

                            # 提取文件名
                            if '#' in file_info:
                                file_path = file_info.split('#')[0]
                                self.sync_progress.current_file = file_path

                            # 提取动作
                            action = action_info.split()[0] if action_info else ""
                            self.sync_progress.current_action = action

                            # 更新计数
                            self.sync_progress.completed_files += 1

                            # 估算文件大小（这里简化处理）
                            self.sync_progress.bytes_transferred += 1024 * 100  # 假设每个文件100KB

                    # 检查是否是文件总数信息
                    # 示例: 235 files to refresh.
                    if 'files to' in line:
                        match = re.search(r'(\d+)\s+files', line)
                        if match:
                            self.sync_progress.total_files = int(match.group(1))

                    # 记录错误
                    if 'error' in line.lower() or 'failed' in line.lower():
                        self.sync_progress.errors.append(line)

        except Exception as e:
            logger.debug(f"读取同步输出时出错: {e}")

    def process_sync_queue(self):
        """处理同步队列 - 一次只同步一个项目"""
        # 如果正在同步，检查进度
        if self.current_sync_project:
            self.check_sync_progress()
            return

        # 查找下一个需要同步的项目
        for project_name, task in self.project_tasks.items():
            if task.status == ProjectStatus.PENDING_SYNC:
                self.start_sync_project(project_name)
                break

    def start_sync_project(self, project_name: str):
        """开始同步项目"""
        task = self.project_tasks[project_name]
        task.status = ProjectStatus.SYNCING
        task.sync_start_time = time.time()
        self.current_sync_project = project_name

        # 重置进度信息
        self.sync_progress = SyncProgress()

        logger.info("")
        logger.info("┌" + "─" * 78 + "┐")
        logger.info(f"│ 开始同步项目: {project_name:<62} │")
        logger.info("├" + "─" * 78 + "┤")
        logger.info(f"│ Depot路径: {task.depot_path[:65]:<65} │")
        logger.info(f"│ 本地路径: {task.local_path[:65]:<65} │")
        logger.info(f"│ 目标版本: {task.version:<66} │")
        logger.info("└" + "─" * 78 + "┘")
        logger.info("")

        if self.test_mode:
            # 测试模式，模拟同步进度
            self.simulate_sync_progress()
        else:
            # 实际同步
            try:
                # 首先获取文件列表以确定总数
                cmd_count = f'p4 sync -n "{task.depot_path}" 2>&1 | find /c " - "'
                result = subprocess.run(
                    cmd_count,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=task.local_path,
                    timeout=30
                )

                if result.returncode == 0:
                    try:
                        file_count = int(result.stdout.strip())
                        self.sync_progress.total_files = file_count
                        logger.info(f"需要同步 {file_count} 个文件")
                    except:
                        pass

                # 构建同步命令
                cmd = f'p4 sync "{task.depot_path}"'

                # 启动同步进程
                self.sync_process = subprocess.Popen(
                    cmd,
                    shell=True,
                    cwd=task.local_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    bufsize=1,
                    universal_newlines=True
                )

                # 启动输出读取线程
                self.sync_thread = threading.Thread(
                    target=self.sync_output_reader,
                    args=(self.sync_process,),
                    daemon=True
                )
                self.sync_thread.start()

                logger.info(f"同步进程已启动 (PID: {self.sync_process.pid})")

            except Exception as e:
                logger.error(f"启动同步进程失败: {e}")
                task.status = ProjectStatus.FAILED
                self.current_sync_project = None
                self.sync_process = None

    def simulate_sync_progress(self):
        """模拟同步进度（测试模式）"""
        # 设置模拟参数
        self.sync_progress.total_files = 150
        self.sync_progress.completed_files = 0

        # 模拟文件列表
        test_files = [
            "//depot/project/src/main.cpp",
            "//depot/project/include/header.h",
            "//depot/project/assets/texture.png",
            "//depot/project/docs/readme.md",
            "//depot/project/build/makefile"
        ]

        # 启动模拟线程
        def simulate():
            import random
            for i in range(self.sync_progress.total_files):
                time.sleep(0.1)  # 模拟每个文件需要0.1秒
                self.sync_progress.completed_files = i + 1
                self.sync_progress.current_file = random.choice(test_files)
                self.sync_progress.current_action = random.choice(['updating', 'added', 'updated'])
                self.sync_progress.bytes_transferred += random.randint(1024, 1024 * 1024)

                # 偶尔产生错误
                if random.random() < 0.05:
                    self.sync_progress.errors.append(f"Warning: file {self.sync_progress.current_file} is locked")

        thread = threading.Thread(target=simulate, daemon=True)
        thread.start()

    def check_sync_progress(self):
        """检查同步进度"""
        if not self.current_sync_project:
            return

        task = self.project_tasks[self.current_sync_project]
        elapsed_time = time.time() - task.sync_start_time

        # 显示进度
        if self.sync_progress.total_files > 0:
            percent = (self.sync_progress.completed_files / self.sync_progress.total_files) * 100
            progress_bar = self.format_progress_bar(
                self.sync_progress.completed_files,
                self.sync_progress.total_files,
                30
            )

            status_msg = f"同步 {self.current_sync_project}: {progress_bar} "
            status_msg += f"{self.sync_progress.completed_files}/{self.sync_progress.total_files} 文件"

            if self.sync_progress.current_file:
                file_name = os.path.basename(self.sync_progress.current_file)
                status_msg += f" - {file_name}"

            logger.info(status_msg)

        if self.test_mode:
            # 测试模式：检查是否完成
            if self.sync_progress.completed_files >= self.sync_progress.total_files:
                logger.info("")
                logger.info("┌" + "─" * 78 + "┐")
                logger.info(f"│ {'✓ 同步完成':^76} │")
                logger.info("├" + "─" * 78 + "┤")
                logger.info(f"│ 项目: {self.current_sync_project:<70} │")
                logger.info(f"│ 文件数: {self.sync_progress.total_files:<69} │")
                logger.info(f"│ 传输量: {self.format_bytes(self.sync_progress.bytes_transferred):<69} │")
                logger.info(f"│ 耗时: {elapsed_time / 60:.1f} 分钟 {'':>60} │")
                logger.info("└" + "─" * 78 + "┘")
                logger.info("")

                task.status = ProjectStatus.PENDING_BUILD
                self.last_sync_versions[self.current_sync_project] = task.version
                self.current_sync_project = None
            return

        # 实际同步进度检查
        if not self.sync_process:
            return

        # 检查进程是否还在运行
        poll_result = self.sync_process.poll()

        if poll_result is None:
            # 进程还在运行
            # 检查超时
            if elapsed_time > self.sync_timeout:
                logger.error(f"项目 {self.current_sync_project} 同步超时")
                self.sync_process.terminate()
                task.status = ProjectStatus.FAILED
                self.current_sync_project = None
                self.sync_process = None
                return
        else:
            # 进程已结束
            if self.sync_thread:
                self.sync_thread.join(timeout=1)

            logger.info("")
            if poll_result == 0:
                # 同步成功
                logger.info("┌" + "─" * 78 + "┐")
                logger.info(f"│ {'✓ 同步完成':^76} │")
                logger.info("├" + "─" * 78 + "┤")
                logger.info(f"│ 项目: {self.current_sync_project:<70} │")
                logger.info(f"│ 文件数: {self.sync_progress.completed_files:<69} │")
                logger.info(f"│ 传输量: {self.format_bytes(self.sync_progress.bytes_transferred):<69} │")
                logger.info(f"│ 耗时: {elapsed_time / 60:.1f} 分钟 {'':>60} │")

                if self.sync_progress.errors:
                    logger.info("├" + "─" * 78 + "┤")
                    logger.info(f"│ 警告: {len(self.sync_progress.errors)} 个 {'':>67} │")

                logger.info("└" + "─" * 78 + "┘")
                logger.info("")

                task.status = ProjectStatus.PENDING_BUILD
                self.last_sync_versions[self.current_sync_project] = task.version
            else:
                # 同步失败
                logger.error("┌" + "─" * 78 + "┐")
                logger.error(f"│ {'✗ 同步失败':^76} │")
                logger.error("├" + "─" * 78 + "┤")
                logger.error(f"│ 项目: {self.current_sync_project:<70} │")
                logger.error(f"│ 错误码: {poll_result:<68} │")

                if self.sync_progress.errors:
                    logger.error("├" + "─" * 78 + "┤")
                    for error in self.sync_progress.errors[-5:]:
                        if len(error) > 70:
                            error = error[:67] + "..."
                        logger.error(f"│ {error:<76} │")

                logger.error("└" + "─" * 78 + "┘")
                logger.error("")

                task.status = ProjectStatus.FAILED
                # 失败后重置为IDLE，允许重试
                task.status = ProjectStatus.IDLE

            self.current_sync_project = None
            self.sync_process = None
            self.sync_thread = None

    def process_build_queue(self):
        """处理构建队列"""
        for project_name, task in self.project_tasks.items():
            if task.status == ProjectStatus.PENDING_BUILD:
                # 检查窗口是否空闲
                window = self.project_windows[project_name]
                if self.get_window_status(window) == "idle":
                    self.start_build_project(project_name)

    def start_build_project(self, project_name: str):
        """开始构建项目"""
        task = self.project_tasks[project_name]
        window = self.project_windows[project_name]

        logger.info(f"触发项目 {project_name} 的构建")
        logger.info(f"  同步版本: {task.version}")

        # 写入构建命令
        window.command_file.write_text("BUILD", encoding='utf-8')
        window.build_status = "running"
        window.last_build_time = time.time()

        task.status = ProjectStatus.BUILDING
        task.build_start_time = time.time()

        # 测试模式下记录构建次数
        if self.test_mode:
            self.test_build_count[project_name] += 1
            logger.info(f"[测试模式] 项目 {project_name} 第 {self.test_build_count[project_name]} 次构建")

    def get_window_status(self, window: ProjectWindow) -> str:
        """获取窗口当前状态"""
        try:
            if window.status_file.exists():
                status_text = window.status_file.read_text(encoding='utf-8').strip()

                if status_text == "IDLE":
                    return "idle"
                elif status_text.startswith("RUNNING"):
                    return "running"
                elif status_text.startswith("ERROR"):
                    return "failed"
                elif status_text.startswith("COMPLETED"):
                    return "completed"

            return "idle"

        except Exception as e:
            logger.debug(f"读取状态文件出错: {e}")
            return "idle"

    def monitor_build_windows(self):
        """监控构建窗口状态"""
        for project_name, window in self.project_windows.items():
            try:
                task = self.project_tasks[project_name]

                if task.status != ProjectStatus.BUILDING:
                    continue

                old_status = window.build_status
                new_status = self.get_window_status(window)

                # 状态变化时记录日志
                if old_status != new_status:
                    window.build_status = new_status

                    if new_status == "idle":
                        # 构建完成
                        elapsed_time = (time.time() - window.last_build_time) / 60
                        logger.info(f"项目 {project_name} 构建完成 (耗时: {elapsed_time:.1f} 分钟)")
                        task.status = ProjectStatus.COMPLETED
                        task.last_update_time = time.time()

                        # 一段时间后重置为IDLE状态，允许下次更新
                        task.status = ProjectStatus.IDLE

                    elif new_status == "running":
                        # 读取正在执行的脚本
                        if window.status_file.exists():
                            status_text = window.status_file.read_text(encoding='utf-8').strip()
                            if status_text.startswith("RUNNING:"):
                                script_name = status_text.split(":", 1)[1]
                                if script_name != window.current_script:
                                    window.current_script = script_name
                                    logger.info(f"[{project_name}] 正在执行: {script_name}")

                    elif new_status == "failed":
                        logger.error(f"项目 {project_name} 构建失败")
                        task.status = ProjectStatus.FAILED
                        # 失败后也重置为IDLE，允许重试
                        task.status = ProjectStatus.IDLE

                # 检查超时
                if window.build_status == "running":
                    elapsed_time = time.time() - window.last_build_time
                    if elapsed_time > self.build_timeout:
                        logger.error(f"项目 {project_name} 构建超时")
                        task.status = ProjectStatus.FAILED
                        task.status = ProjectStatus.IDLE  # 重置状态

            except Exception as e:
                logger.debug(f"监控窗口 {project_name} 时出错: {e}")

    def show_status(self):
        """显示当前状态"""
        status_info = []

        # 统计各种状态的项目数
        status_count = {}
        for task in self.project_tasks.values():
            status_count[task.status] = status_count.get(task.status, 0) + 1

        # 显示等待同步的项目
        pending_sync = [name for name, task in self.project_tasks.items()
                        if task.status == ProjectStatus.PENDING_SYNC]
        if pending_sync:
            status_info.append(f"等待同步: {', '.join(pending_sync)}")

        # 显示正在构建的项目
        building = []
        for name, task in self.project_tasks.items():
            if task.status == ProjectStatus.BUILDING:
                elapsed = (time.time() - task.build_start_time) / 60
                building.append(f"{name} ({elapsed:.1f}分钟)")
        if building:
            status_info.append(f"正在构建: {', '.join(building)}")

        # 显示等待构建的项目
        pending_build = [name for name, task in self.project_tasks.items()
                         if task.status == ProjectStatus.PENDING_BUILD]
        if pending_build:
            status_info.append(f"等待构建: {', '.join(pending_build)}")

        # 输出状态信息
        if status_info:
            for info in status_info:
                logger.info(f"  {info}")

    def shutdown(self):
        """关闭所有窗口"""
        logger.info("关闭所有项目窗口...")

        # 终止同步进程
        if self.sync_process:
            logger.info("终止同步进程...")
            self.sync_process.terminate()

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

        # 检查是否有成功初始化的窗口
        if not self.project_windows:
            logger.error("没有成功初始化的项目窗口，程序退出")
            return

        try:
            loop_count = 0
            while True:
                loop_count += 1
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                if self.test_mode:
                    logger.info(f"[测试模式] 循环 #{loop_count} - 检查更新... ({current_time})")
                else:
                    logger.info(f"循环 #{loop_count} - 检查项目更新... ({current_time})")

                # 检查所有项目并加入队列
                for project_name, project_config in self.projects.items():
                    if project_name in self.project_tasks:  # 确保项目已初始化
                        self.check_and_queue_project(project_name, project_config)

                # 处理同步队列（一次只同步一个）
                self.process_sync_queue()

                # 处理构建队列
                self.process_build_queue()

                # 监控构建窗口状态
                self.monitor_build_windows()

                # 显示当前状态
                self.show_status()

                # 计算下次检查时间
                if self.test_mode:
                    check_interval = 30  # 测试模式30秒
                else:
                    check_interval = min(
                        project.get('check_interval', self.default_check_interval)
                        for project in self.projects.values()
                    )

                logger.info(f"等待 {check_interval} 秒后进行下次检查...")
                logger.info("-" * 60)

                # 在等待期间继续处理队列和监控
                wait_time = 0
                while wait_time < check_interval:
                    # 处理同步队列
                    self.process_sync_queue()

                    # 处理构建队列
                    self.process_build_queue()

                    # 监控窗口状态
                    self.monitor_build_windows()

                    time.sleep(2)
                    wait_time += 2

        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
            self.shutdown()
            logger.info("P4V Project Manager 已关闭")
        except Exception as e:
            logger.error(f"运行时出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.shutdown()
            raise


def main():
    """主函数"""
    try:
        logger.info("启动 P4V Project Manager...")
        config = r"O:\Person\Projects\interview\TestProject\P4VProjectManager\config.json"
        manager = P4VProjectManager(config)
        logger.info("开始运行主循环...")
        manager.run()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        return 0
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())