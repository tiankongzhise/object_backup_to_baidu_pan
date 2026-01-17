"""主入口

提供命令行和图形界面两种启动方式。
"""

import sys
import argparse
from pathlib import Path


def run_gui():
    """运行图形界面"""
    from ui import MainWindow
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def run_cli(config_path: str):
    """运行命令行模式

    Args:
        config_path: 配置文件路径
    """
    from config import load_config
    from service.database_service import DatabaseService
    from service.orchestrator import MainOrchestrator

    # 加载配置
    config = load_config(config_path)
    if not config:
        print("错误: 无法加载配置文件")
        sys.exit(1)

    # 创建数据库服务
    db_service = DatabaseService(config.database)

    # 检查数据库连接
    if not db_service.check_connection():
        print("错误: 无法连接到数据库")
        sys.exit(1)

    # 创建协调器并运行
    orchestrator = MainOrchestrator(config, db_service)

    try:
        orchestrator.run()
        print("备份完成")
    except KeyboardInterrupt:
        print("\n用户中断")
        orchestrator.stop()
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="百度网盘备份工具")
    parser.add_argument(
        '--gui', action='store_true',
        help='运行图形界面（默认）'
    )
    parser.add_argument(
        '--config', type=str, default='config.toml',
        help='配置文件路径（CLI模式）'
    )
    parser.add_argument(
        '--version', action='version',
        version='%(prog)s 0.2.0'
    )

    args = parser.parse_args()

    if args.gui or len(sys.argv) == 1:
        run_gui()
    else:
        run_cli(args.config)


if __name__ == "__main__":
    main()
