# -*- coding: utf-8 -*-

import subprocess
import time
import logging
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Dict, List, Set, Tuple
import random
import sys

# ========== 英文 Windows 设置 ==========
if sys.platform == 'win32':
    # 英文 Windows 通常是 cp1252 或 cp437
    # 设置控制台为 UTF-8（推荐）
    os.system('chcp 65001 > nul')

    # 或使用 ctypes
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleCP(65001)
    kernel32.SetConsoleOutputCP(65001)

# ========== 配置 Logging ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler('TestFiles/P4VProjectManager/p4v_build_automation.log', encoding='utf-8')  # 文件输出
    ]
)

logger = logging.getLogger(__name__)


class ConfigValidator:
    """配置验证器"""

    @staticmethod
    def validate_p4_connection(config: Dict) -> Tuple[bool, List[str]]:
        """
        验证P4连接配置

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 如果是测试模式，跳过P4验证
        if config.get('test_mode', False):
            logger.info("测试模式启用，跳过P4连接验证")
            return True, errors

        # 检查必要的P4配置
        required_fields = ['p4_client', 'p4_user', 'p4_port']
        for field in required_fields:
            if not config.get(field):
                errors.append(f"缺少必要的P4配置: {field}")

        if not errors:
            # 尝试执行P4命令验证连接
            try:
                os.environ['P4CLIENT'] = config['p4_client']
                os.environ['P4USER'] = config['p4_user']
                os.environ['P4PORT'] = config['p4_port']

                result = subprocess.run(
                    'p4 info',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode != 0:
                    errors.append(f"无法连接到P4服务器: {result.stderr}")
                else:
                    logger.info("P4连接验证成功")

            except subprocess.TimeoutExpired:
                errors.append("P4连接超时")
            except Exception as e:
                errors.append(f"P4连接测试失败: {str(e)}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_projects(projects: Dict, test_mode: bool = False) -> Tuple[bool, List[str]]:
        """
        验证项目配置

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        if not projects:
            errors.append("没有配置任何项目")
            return False, errors

        for project_name, project_config in projects.items():
            # 如果不是测试模式，检查P4路径
            if not test_mode and 'path' not in project_config:
                errors.append(f"项目 {project_name} 缺少 'path' 配置")

            if 'local_path' not in project_config:
                errors.append(f"项目 {project_name} 缺少 'local_path' 配置")
            else:
                # 检查本地路径是否存在
                local_path = Path(project_config['local_path'])
                if not local_path.exists():
                    errors.append(f"项目 {project_name} 的本地路径不存在: {local_path}")
                elif not local_path.is_dir():
                    errors.append(f"项目 {project_name} 的本地路径不是目录: {local_path}")
                else:
                    # 检查编译脚本是否存在
                    build_scripts = project_config.get('build_scripts', [])
                    if not build_scripts:
                        logger.warning(f"项目 {project_name} 没有配置编译脚本")
                    else:
                        for script in build_scripts:
                            script_path = local_path / script
                            if not script_path.exists():
                                errors.append(f"项目 {project_name} 的编译脚本不存在: {script_path}")
                            elif not script_path.is_file():
                                errors.append(f"项目 {project_name} 的编译脚本路径不是文件: {script_path}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_config(config: Dict) -> Tuple[bool, List[str]]:
        """
        验证整个配置

        Returns:
            (是否有效, 错误信息列表)
        """
        all_errors = []
        test_mode = config.get('test_mode', False)

        if test_mode:
            logger.info("=" * 60)
            logger.info("测试模式已启用")
            logger.info("将跳过所有P4V操作，并模拟代码更新")
            logger.info("=" * 60)

        # 验证P4连接
        p4_valid, p4_errors = ConfigValidator.validate_p4_connection(config)
        all_errors.extend(p4_errors)

        # 验证项目配置
        projects_valid, projects_errors = ConfigValidator.validate_projects(
            config.get('projects', {}),
            test_mode
        )
        all_errors.extend(projects_errors)

        # 验证更新间隔
        update_interval = config.get('update_interval_seconds', 0)
        if update_interval < 60:
            all_errors.append(f"更新间隔太短 ({update_interval}秒)，建议至少60秒")

        # 如果是测试模式，验证测试配置
        if test_mode:
            test_config = config.get('test_config', {})
            update_probability = test_config.get('update_probability', 0.5)
            if not 0 <= update_probability <= 1:
                all_errors.append(f"update_probability 必须在0-1之间，当前值: {update_probability}")

        return len(all_errors) == 0, all_errors


class P4VProjectManager:
    def __init__(self, config_file='config.json'):
        """
        初始化P4V项目管理器

        Args:
            config_file: 配置文件路径
        """
        self.config = self.load_config(config_file)

        # 测试模式相关配置
        self.test_mode = self.config.get('test_mode', False)
        self.test_config = self.config.get('test_config', {})
        self.update_probability = self.test_config.get('update_probability', 0.5)
        self.simulate_p4_errors = self.test_config.get('simulate_p4_errors', False)
        self.error_probability = self.test_config.get('error_probability', 0.1)

        # 在初始化时验证配置
        self.validate_configuration()

        # P4配置（测试模式下可能不使用）
        self.p4_client = self.config.get('p4_client', '')
        self.p4_user = self.config.get('p4_user', '')
        self.p4_port = self.config.get('p4_port', '')
        self.projects = self.config.get('projects', {})
        self.update_interval = self.config.get('update_interval_seconds', 3600)

        # 用于跟踪正在编译的项目
        self.compiling_projects: Set[str] = set()
        self.compile_lock = Lock()

        # 测试模式下的更新历史（用于模拟）
        self.test_update_history: Dict[str, int] = {}

    def load_config(self, config_file: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"配置文件 {config_file} 不存在")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            raise

    def validate_configuration(self):
        """验证配置的有效性"""
        logger.info("开始验证配置...")

        is_valid, errors = ConfigValidator.validate_config(self.config)

        if not is_valid:
            logger.error("配置验证失败，发现以下问题：")
            for error in errors:
                logger.error(f"  - {error}")
            raise ValueError("配置验证失败，请检查配置文件")

        logger.info("配置验证成功")

    def setup_p4_environment(self):
        """设置P4环境变量"""
        if not self.test_mode:
            os.environ['P4CLIENT'] = self.p4_client
            os.environ['P4USER'] = self.p4_user
            os.environ['P4PORT'] = self.p4_port
            logger.info("P4环境变量已设置")
        else:
            logger.info("测试模式：跳过P4环境设置")

    def simulate_p4_update_check(self, project_name: str) -> bool:
        """
        模拟P4更新检查（测试模式）

        Args:
            project_name: 项目名称

        Returns:
            bool: 模拟是否有更新
        """
        # 获取项目的更新历史
        update_count = self.test_update_history.get(project_name, 0)

        # 根据配置的概率决定是否有更新
        has_update = random.random() < self.update_probability

        if has_update:
            self.test_update_history[project_name] = update_count + 1
            logger.info(f"[测试模式] 项目 {project_name} 模拟检测到更新 (第{update_count + 1}次)")
        else:
            logger.info(f"[测试模式] 项目 {project_name} 模拟没有更新")

        # 模拟可能的P4错误
        if self.simulate_p4_errors and random.random() < self.error_probability:
            logger.error(f"[测试模式] 模拟P4错误：项目 {project_name} 更新失败")
            return False

        return has_update

    def check_for_updates(self, project_name: str, project_config: Dict) -> bool:
        """
        检查项目是否有更新

        Args:
            project_name: 项目名称
            project_config: 项目配置

        Returns:
            bool: 如果有更新返回True，否则返回False
        """
        # 如果项目正在编译，跳过更新
        with self.compile_lock:
            if project_name in self.compiling_projects:
                logger.info(f"项目 {project_name} 正在编译中，跳过更新检查")
                return False

        # 测试模式：模拟P4更新
        if self.test_mode:
            return self.simulate_p4_update_check(project_name)

        # 正常模式：执行真实的P4操作
        try:
            depot_path = project_config['path']
            local_path = project_config['local_path']

            # 首先检查是否有新的变更
            cmd = f'p4 sync -n {depot_path}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

            # 如果输出包含文件更新信息，说明有更新
            if result.stdout and 'up-to-date' not in result.stdout:
                logger.info(f"项目 {project_name} 检测到更新")

                # 执行实际的同步
                sync_cmd = f'p4 sync {depot_path}'
                sync_result = subprocess.run(sync_cmd, shell=True, capture_output=True, text=True)

                if sync_result.returncode == 0:
                    logger.info(f"项目 {project_name} 更新成功")
                    return True
                else:
                    logger.error(f"项目 {project_name} 更新失败: {sync_result.stderr}")
                    return False
            else:
                logger.debug(f"项目 {project_name} 没有新的更新")
                return False

        except Exception as e:
            logger.error(f"检查项目 {project_name} 更新时出错: {str(e)}")
            return False

    def build_project(self, project_name: str, project_config: Dict):
        """
        编译项目

        Args:
            project_name: 项目名称
            project_config: 项目配置
        """
        # 标记项目开始编译
        with self.compile_lock:
            self.compiling_projects.add(project_name)

        try:
            local_path = project_config['local_path']
            build_scripts = project_config.get('build_scripts', [])

            if not build_scripts:
                logger.warning(f"项目 {project_name} 没有配置编译脚本")
                return

            logger.info(f"开始编译项目 {project_name}")

            # 切换到项目目录
            original_dir = os.getcwd()
            os.chdir(local_path)

            # 按顺序执行编译脚本
            for i, script in enumerate(build_scripts, 1):
                script_path = Path(local_path) / script

                if not script_path.exists():
                    logger.warning(f"编译脚本 {script} 不存在，跳过")
                    continue

                logger.info(f"[{i}/{len(build_scripts)}] 执行编译脚本: {script}")

                try:
                    # 执行bat脚本，等待其完成
                    start_time = time.time()
                    result = subprocess.run(
                        str(script_path),
                        shell=True,
                        capture_output=True,
                        text=True,
                        encoding='utf-8',  # 改为utf-8
                        errors='replace',  # 替换无法解码的字符
                        timeout=1800  # 30分钟超时
                    )

                    elapsed_time = time.time() - start_time

                    if result.returncode != 0:
                        logger.error(f"脚本 {script} 执行失败 (返回码: {result.returncode}, 耗时: {elapsed_time:.1f}秒)")
                        if result.stderr:
                            logger.error(f"错误输出: {result.stderr}")
                        # 继续执行下一个脚本
                    else:
                        logger.info(f"脚本 {script} 执行成功 (耗时: {elapsed_time:.1f}秒)")

                except subprocess.TimeoutExpired:
                    logger.error(f"脚本 {script} 执行超时(超过30分钟)")
                except Exception as e:
                    logger.error(f"执行脚本 {script} 时出错: {str(e)}")

            # 恢复原始目录
            os.chdir(original_dir)
            logger.info(f"项目 {project_name} 编译完成")

        except Exception as e:
            logger.error(f"编译项目 {project_name} 时出错: {str(e)}")
        finally:
            # 编译完成后，从编译列表中移除
            with self.compile_lock:
                self.compiling_projects.discard(project_name)

    def update_and_build_cycle(self):
        """执行一次更新和编译循环"""
        logger.info("=" * 60)
        logger.info("开始执行更新检查循环")
        logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.test_mode:
            logger.info("[测试模式] 模拟P4更新检查")
        logger.info("=" * 60)

        for project_name, project_config in self.projects.items():
            try:
                # 检查并更新项目
                has_updates = self.check_for_updates(project_name, project_config)

                # 如果有更新，启动编译流程
                if has_updates:
                    self.build_project(project_name, project_config)

            except Exception as e:
                logger.error(f"处理项目 {project_name} 时出错: {str(e)}")

        logger.info("更新检查循环完成")

    def run(self):
        """主运行循环"""
        logger.info("=" * 60)
        logger.info("P4V自动化更新和编译系统启动")
        logger.info(f"运行模式: {'测试模式' if self.test_mode else '正常模式'}")
        logger.info(f"更新间隔: {self.update_interval} 秒")
        logger.info(f"监控项目数: {len(self.projects)}")

        if self.test_mode:
            logger.info(f"模拟更新概率: {self.update_probability * 100}%")
            if self.simulate_p4_errors:
                logger.info(f"模拟错误概率: {self.error_probability * 100}%")

        logger.info("=" * 60)

        # 设置P4环境
        self.setup_p4_environment()

        cycle_count = 0
        while True:
            try:
                cycle_count += 1
                logger.info(f"\n### 第 {cycle_count} 次循环 ###")

                start_time = time.time()

                # 执行更新和编译循环
                self.update_and_build_cycle()

                # 计算下次执行时间
                elapsed_time = time.time() - start_time
                sleep_time = max(0, self.update_interval - elapsed_time)

                if sleep_time > 0:
                    next_check = datetime.now() + timedelta(seconds=sleep_time)
                    logger.info(f"下次检查时间: {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.info(f"等待 {sleep_time:.0f} 秒...")
                    time.sleep(sleep_time)

            except KeyboardInterrupt:
                logger.info("收到中断信号，正在退出...")
                break
            except Exception as e:
                logger.error(f"主循环出错: {str(e)}")
                time.sleep(60)  # 出错后等待1分钟再重试


if __name__ == "__main__":
    import sys

    config = r"TestFiles/P4VProjectManager/config.json"

    # 检查配置文件是否存在
    if not Path(config).exists():
        print("配置文件 config.json 不存在")
        print("运行 'python script.py --create-config' 创建示例配置文件")
        sys.exit(1)

    try:
        # 启动管理器
        manager = P4VProjectManager(config)
        manager.run()
    except Exception as e:
        logger.error(f"启动失败: {e}")
        sys.exit(1)