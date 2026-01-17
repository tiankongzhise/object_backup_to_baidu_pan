"""PyQt6 桌面UI

提供备份系统的图形界面。
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QSpinBox, QDoubleSpinBox,
    QProgressBar, QTextEdit, QGroupBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog,
    QComboBox, QCheckBox, QGridLayout, QSplitter
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont, QIcon, QAction

from ..config import Config, load_config, SourceConfig, StorageConfig, SpaceConfig, DatabaseCredentials, DatabasePoolConfig
from ..service.database_service import DatabaseService
from ..service.orchestrator import MainOrchestrator, BackupProgress
from ..service.space_manager import SpaceManager


class BackupWorker(QThread):
    """备份工作线程"""

    progress_updated = pyqtSignal(BackupProgress)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, config: Config, credentials: DatabaseCredentials, pool_config: DatabasePoolConfig):
        super().__init__()
        self.config = config
        self.credentials = credentials
        self.pool_config = pool_config

    def run(self):
        """运行备份"""
        try:
            orchestrator = MainOrchestrator(
                self.config,
                credentials=self.credentials,
                pool_config=self.pool_config
            )

            # 设置回调，将进度和日志传递到UI
            orchestrator.config.on_progress = self.progress_updated.emit
            orchestrator.config.on_log = self.log_message.emit

            orchestrator.run()

            self.finished.emit(True, "备份完成")
        except Exception as e:
            self.finished.emit(False, str(e))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("百度网盘备份工具")
        self.setMinimumSize(900, 700)

        # 配置和数据
        self.config = Config()
        self.db_service: Optional[DatabaseService] = None
        self.backup_worker: Optional[BackupWorker] = None
        self.is_backup_running = False

        # 初始化UI
        self._init_ui()
        self._init_menu()
        self._load_config()
        self._update_disk_space()

        # 定时更新磁盘空间
        self._space_timer = QTimer()
        self._space_timer.timeout.connect(self._update_disk_space)
        self._space_timer.start(5000)  # 每5秒更新

    def _init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # 创建选项卡
        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Tab 1: 备份控制
        backup_tab = self._create_backup_tab()
        tabs.addTab(backup_tab, "备份")

        # Tab 2: 配置
        config_tab = self._create_config_tab()
        tabs.addTab(config_tab, "配置")

        # Tab 3: 日志
        log_tab = self._create_log_tab()
        tabs.addTab(log_tab, "日志")

        # Tab 4: 状态
        status_tab = self._create_status_tab()
        tabs.addTab(status_tab, "状态")

    def _init_menu(self):
        """初始化菜单"""
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu("文件")

        load_config_action = QAction("加载配置", self)
        load_config_action.triggered.connect(self._load_config_dialog)
        file_menu.addAction(load_config_action)

        save_config_action = QAction("保存配置", self)
        save_config_action.triggered.connect(self._save_config)
        file_menu.addAction(save_config_action)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _create_backup_tab(self) -> QWidget:
        """创建备份Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 源文件夹选择
        source_group = QGroupBox("源文件夹")
        source_layout = QHBoxLayout()

        self.source_path_edit = QLineEdit()
        self.source_path_edit.setPlaceholderText("选择要备份的文件夹")
        source_layout.addWidget(self.source_path_edit)

        source_btn = QPushButton("选择")
        source_btn.clicked.connect(self._select_source_folder)
        source_layout.addWidget(source_btn)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # 磁盘空间信息
        space_group = QGroupBox("磁盘空间")
        space_layout = QGridLayout()

        self.disk_path_label = QLabel("D:\\")
        space_layout.addWidget(QLabel("磁盘:"), 0, 0)
        space_layout.addWidget(self.disk_path_label, 0, 1)

        self.disk_total_label = QLabel("0 GB")
        space_layout.addWidget(QLabel("总空间:"), 1, 0)
        space_layout.addWidget(self.disk_total_label, 1, 1)

        self.disk_used_label = QLabel("0 GB")
        space_layout.addWidget(QLabel("已使用:"), 1, 2)
        space_layout.addWidget(self.disk_used_label, 1, 3)

        self.disk_available_label = QLabel("0 GB")
        space_layout.addWidget(QLabel("可用:"), 2, 0)
        space_layout.addWidget(self.disk_available_label, 2, 1)

        self.disk_limit_label = QLabel("80 GB")
        space_layout.addWidget(QLabel("限制:"), 2, 2)
        space_layout.addWidget(self.disk_limit_label, 2, 3)

        space_group.setLayout(space_layout)
        layout.addWidget(space_group)

        # 进度信息
        progress_group = QGroupBox("备份进度")
        progress_layout = QGridLayout()

        self.phase_label = QLabel("就绪")
        progress_layout.addWidget(QLabel("当前阶段:"), 0, 0)
        progress_layout.addWidget(self.phase_label, 0, 1)

        self.status_label = QLabel("")
        progress_layout.addWidget(QLabel("状态:"), 1, 0)
        progress_layout.addWidget(self.status_label, 1, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar, 2, 0, 1, 4)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # 统计信息
        stats_group = QGroupBox("统计")
        stats_layout = QHBoxLayout()

        self.total_items_label = QLabel("总计: 0")
        stats_layout.addWidget(self.total_items_label)

        self.completed_label = QLabel("完成: 0")
        stats_layout.addWidget(self.completed_label)

        self.failed_label = QLabel("失败: 0")
        stats_layout.addWidget(self.failed_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # 按钮
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("开始备份")
        self.start_btn.clicked.connect(self._start_backup)
        self.start_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._stop_backup)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        return widget

    def _create_config_tab(self) -> QWidget:
        """创建配置Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 存储路径配置
        storage_group = QGroupBox("存储路径")
        storage_layout = QGridLayout()

        storage_layout.addWidget(QLabel("压缩目录:"), 0, 0)
        self.compress_dir_edit = QLineEdit("/tmp/compress")
        storage_layout.addWidget(self.compress_dir_edit, 0, 1)

        compress_dir_btn = QPushButton("选择")
        compress_dir_btn.clicked.connect(lambda: self._select_dir(self.compress_dir_edit))
        storage_layout.addWidget(compress_dir_btn, 0, 2)

        storage_layout.addWidget(QLabel("解压目录:"), 1, 0)
        self.extract_dir_edit = QLineEdit("/tmp/extract")
        storage_layout.addWidget(self.extract_dir_edit, 1, 1)

        extract_dir_btn = QPushButton("选择")
        extract_dir_btn.clicked.connect(lambda: self._select_dir(self.extract_dir_edit))
        storage_layout.addWidget(extract_dir_btn, 1, 2)

        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)

        # 空间限制
        space_group = QGroupBox("空间限制")
        space_layout = QHBoxLayout()

        space_layout.addWidget(QLabel("磁盘限制 (GB):"))
        self.disk_limit_spin = QSpinBox()
        self.disk_limit_spin.setRange(1, 1000)
        self.disk_limit_spin.setValue(80)
        space_layout.addWidget(self.disk_limit_spin)

        space_layout.addWidget(QLabel("文件大小限制 (GB):"))
        self.file_limit_spin = QSpinBox()
        self.file_limit_spin.setRange(1, 1000)
        self.file_limit_spin.setValue(20)
        space_layout.addWidget(self.file_limit_spin)

        space_layout.addWidget(QLabel("文件数限制:"))
        self.file_count_spin = QSpinBox()
        self.file_count_spin.setRange(1, 10000)
        self.file_count_spin.setValue(200)
        space_layout.addWidget(self.file_count_spin)

        space_group.setLayout(space_layout)
        layout.addWidget(space_group)

        # 数据库连接池配置
        db_group = QGroupBox("数据库连接池配置")
        db_layout = QGridLayout()

        db_layout.addWidget(QLabel("连接池大小:"), 0, 0)
        self.db_pool_size_spin = QSpinBox()
        self.db_pool_size_spin.setRange(1, 100)
        self.db_pool_size_spin.setValue(5)
        db_layout.addWidget(self.db_pool_size_spin, 0, 1)

        db_layout.addWidget(QLabel("最大溢出:"), 0, 2)
        self.db_max_overflow_spin = QSpinBox()
        self.db_max_overflow_spin.setRange(0, 100)
        self.db_max_overflow_spin.setValue(10)
        db_layout.addWidget(self.db_max_overflow_spin, 0, 3)

        db_layout.addWidget(QLabel("超时(秒):"), 1, 0)
        self.db_pool_timeout_spin = QSpinBox()
        self.db_pool_timeout_spin.setRange(1, 600)
        self.db_pool_timeout_spin.setValue(30)
        db_layout.addWidget(self.db_pool_timeout_spin, 1, 1)

        db_layout.addWidget(QLabel("回收时间(秒):"), 1, 2)
        self.db_pool_recycle_spin = QSpinBox()
        self.db_pool_recycle_spin.setRange(0, 86400)
        self.db_pool_recycle_spin.setValue(3600)
        db_layout.addWidget(self.db_pool_recycle_spin, 1, 3)

        db_layout.addWidget(QLabel("连接预检测:"), 2, 0)
        self.db_pool_pre_ping_check = QCheckBox("启用")
        self.db_pool_pre_ping_check.setChecked(True)
        db_layout.addWidget(self.db_pool_pre_ping_check, 2, 1)

        db_group.setLayout(db_layout)
        layout.addWidget(db_group)

        # 数据库连接信息说明
        info_label = QLabel("提示: 数据库连接信息请在 .env 文件中配置 MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD 等环境变量")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray;")
        layout.addWidget(info_label)

        # 测试连接按钮
        test_btn = QPushButton("测试数据库连接")
        test_btn.clicked.connect(self._test_db_connection)
        layout.addWidget(test_btn)

        # 保存配置按钮
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self._save_config)
        layout.addWidget(save_btn)

        layout.addStretch()

        return widget

    def _create_log_tab(self) -> QWidget:
        """创建日志Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # 按钮
        btn_layout = QHBoxLayout()

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.log_text.clear)
        btn_layout.addWidget(clear_btn)

        export_btn = QPushButton("导出日志")
        export_btn.clicked.connect(self._export_log)
        btn_layout.addWidget(export_btn)

        layout.addLayout(btn_layout)

        return widget

    def _create_status_tab(self) -> QWidget:
        """创建状态Tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 文件状态表格
        self.status_table = QTableWidget()
        self.status_table.setColumnCount(5)
        self.status_table.setHorizontalHeaderLabels([
            "文件名", "大小", "状态", "Hash", "路径"
        ])
        self.status_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        layout.addWidget(self.status_table)

        layout.addStretch()

        return widget

    def _select_source_folder(self):
        """选择源文件夹"""
        path = QFileDialog.getExistingDirectory(
            self, "选择源文件夹", str(Path.home())
        )
        if path:
            self.source_path_edit.setText(path)
            self.config.source.path = Path(path)
            self._update_disk_space()
            # 启用开始按钮
            if self.config.source.path and self.config.source.path.exists():
                self.start_btn.setEnabled(True)

    def _select_dir(self, line_edit: QLineEdit):
        """选择目录"""
        path = QFileDialog.getExistingDirectory(
            self, "选择目录", str(Path.home())
        )
        if path:
            line_edit.setText(path)

    def _update_disk_space(self):
        """更新磁盘空间显示"""
        try:
            if self.config.source.path:
                manager = SpaceManager(self.config.space)
                space = manager.get_disk_space(self.config.source.path)

                self.disk_path_label.setText(str(self.config.source.path)[:2])

                total_gb = space.total_bytes / (1024**3)
                used_gb = space.used_bytes / (1024**3)
                avail_gb = space.available_bytes / (1024**3)
                limit_gb = self.config.space.disk_limit_gb

                self.disk_total_label.setText(f"{total_gb:.1f} GB")
                self.disk_used_label.setText(f"{used_gb:.1f} GB")
                self.disk_available_label.setText(f"{avail_gb:.1f} GB")
                self.disk_limit_label.setText(f"{limit_gb:.1f} GB")

                # 更新进度条
                progress = min(100, (used_gb / limit_gb) * 100)
                self.progress_bar.setValue(int(progress))

        except Exception as e:
            self._log(f"获取磁盘空间失败: {e}")

    def _load_config(self):
        """加载配置"""
        try:
            config = load_config('config.toml')
            if config:
                self.config = config
                self._apply_config_to_ui()
                self._log("配置已加载")
        except Exception as e:
            self._log(f"加载配置失败: {e}")

    def _load_config_dialog(self):
        """加载配置对话框"""
        path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", str(Path.home()), "TOML Files (*.toml)"
        )
        if path:
            try:
                config = load_config(path)
                if config:
                    self.config = config
                    self._apply_config_to_ui()
                    self._log(f"配置已加载: {path}")
            except Exception as e:
                self._log(f"加载配置失败: {e}")

    def _apply_config_to_ui(self):
        """应用配置到UI"""
        # 源路径
        if self.config.source.path:
            self.source_path_edit.setText(str(self.config.source.path))

        # 存储路径
        self.compress_dir_edit.setText(str(self.config.storage.compress_dir))
        self.extract_dir_edit.setText(str(self.config.storage.extract_dir))

        # 空间限制
        self.disk_limit_spin.setValue(self.config.space.disk_limit_gb)
        self.file_limit_spin.setValue(self.config.classify.file_oversize // (1024**3))
        self.file_count_spin.setValue(self.config.classify.overcount)

        # 数据库连接池
        self.db_pool_size_spin.setValue(self.config.database.pool_size)
        self.db_max_overflow_spin.setValue(self.config.database.max_overflow)
        self.db_pool_timeout_spin.setValue(self.config.database.pool_timeout)
        self.db_pool_recycle_spin.setValue(self.config.database.pool_recycle)
        self.db_pool_pre_ping_check.setChecked(self.config.database.pool_pre_ping)

        # 启用开始按钮
        if self.config.source.path and self.config.source.path.exists():
            self.start_btn.setEnabled(True)

    def _save_config(self):
        """保存配置"""
        # 从UI更新配置
        self.config.source.path = Path(self.source_path_edit.text())
        self.config.storage.compress_dir = Path(self.compress_dir_edit.text())
        self.config.storage.extract_dir = Path(self.extract_dir_edit.text())
        self.config.space.disk_limit_gb = self.disk_limit_spin.value()
        self.config.classify.file_oversize = self.file_limit_spin.value() * (1024**3)
        self.config.classify.folder_oversize = self.file_limit_spin.value() * (1024**3)
        self.config.classify.overcount = self.file_count_spin.value()
        self.config.database.pool_size = self.db_pool_size_spin.value()
        self.config.database.max_overflow = self.db_max_overflow_spin.value()
        self.config.database.pool_timeout = self.db_pool_timeout_spin.value()
        self.config.database.pool_recycle = self.db_pool_recycle_spin.value()
        self.config.database.pool_pre_ping = self.db_pool_pre_ping_check.isChecked()

        self._log("配置已保存")

    def _test_db_connection(self):
        """测试数据库连接"""
        from ..config import DatabaseCredentials, DatabasePoolConfig

        # 创建临时数据库服务（使用环境变量中的凭证）
        credentials = DatabaseCredentials()
        pool_config = self.config.database

        db_service = DatabaseService(credentials, pool_config)

        if db_service.check_connection():
            QMessageBox.information(self, "成功", f"数据库连接正常\n主机: {credentials.host}:{credentials.port}\n数据库: {credentials.name}")
        else:
            QMessageBox.warning(self, "失败", "无法连接到数据库，请检查 .env 文件中的 MYSQL_* 环境变量")

        db_service.close()

    def _start_backup(self):
        """开始备份"""
        from ..config import DatabaseCredentials

        if not self.config.source.path:
            QMessageBox.warning(self, "警告", "请先选择源文件夹")
            return

        if not self.config.source.path.exists():
            QMessageBox.warning(self, "警告", "源文件夹不存在")
            return

        # 保存当前配置
        self._save_config()

        # 从环境变量获取数据库凭证
        credentials = DatabaseCredentials()

        # 创建数据库服务
        self.db_service = DatabaseService(credentials, self.config.database)

        # 检查数据库连接
        if not self.db_service.check_connection():
            QMessageBox.warning(self, "警告", "无法连接到数据库，请检查 .env 文件中的 MYSQL_* 环境变量")
            return

        # 创建工作线程
        self.backup_worker = BackupWorker(self.config, credentials, self.config.database)
        self.backup_worker.progress_updated.connect(self._update_backup_progress)
        self.backup_worker.log_message.connect(self._log)
        self.backup_worker.finished.connect(self._on_backup_finished)

        # 更新UI状态
        self.is_backup_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # 开始备份
        self.backup_worker.start()

    def _stop_backup(self):
        """停止备份"""
        if self.backup_worker and self.backup_worker.isRunning():
            self.backup_worker.terminate()
            self.backup_worker.wait()

        if self.db_service:
            self.db_service.close()

        self.is_backup_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._log("备份已停止")

    def _update_backup_progress(self, progress: BackupProgress):
        """更新备份进度"""
        self.phase_label.setText(progress.phase)
        self.status_label.setText(progress.current_status)

        if progress.total_items > 0:
            percent = (progress.completed_items + progress.failed_items) / progress.total_items * 100
            self.progress_bar.setValue(int(percent))

        self.total_items_label.setText(f"总计: {progress.total_items}")
        self.completed_label.setText(f"完成: {progress.completed_items}")
        self.failed_label.setText(f"失败: {progress.failed_items}")

    def _on_backup_finished(self, success: bool, message: str):
        """备份完成"""
        self.is_backup_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        if self.db_service:
            self.db_service.close()

        if success:
            QMessageBox.information(self, "完成", message)
        else:
            QMessageBox.critical(self, "失败", message)

        self._log(f"备份结束: {message}")

    def _log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.log_text.append(log_msg)

    def _export_log(self):
        """导出日志"""
        path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
            "Log Files (*.log);;Text Files (*.txt)"
        )
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            self._log(f"日志已导出: {path}")

    def _show_about(self):
        """显示关于"""
        QMessageBox.about(
            self,
            "关于",
            "百度网盘备份工具 v0.2.0\n\n"
            "将本地文件加密备份到百度网盘\n\n"
            "功能:\n"
            "- 文件夹扫描和分类\n"
            "- Hash去重比对\n"
            "- AES加密压缩\n"
            "- 解压验证\n"
            "- 断点续传\n"
            "- 磁盘空间管理"
        )

    def closeEvent(self, event):
        """关闭事件"""
        if self.is_backup_running:
            reply = QMessageBox.question(
                self, "确认", "备份正在运行，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            self._stop_backup()

        event.accept()


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
