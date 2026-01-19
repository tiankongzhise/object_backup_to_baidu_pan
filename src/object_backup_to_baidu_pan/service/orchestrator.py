"""主协调器

协调整个备份流程，连接各个服务模块。

流程说明：
1. 文件扫描分类 → 标记人工处理项到DB，只处理正常项
2. 去重比对 → 计算Hash，与DB比对
3. 启动上传队列，并发处理每个项目：
   - 压缩+验证 → 立即提交上传任务到队列（异步上传）
   - 后续项目继续压缩+验证，与上传并发执行
4. 等待所有上传任务完成
5. 人工处理检查 → 流程结束后检查是否有pending的人工处理项，发送邮件通知
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from datetime import datetime
import logging
import shutil
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

from ..config import Config, SpaceConfig, DatabaseCredentials, DatabasePoolConfig
from .database_service import DatabaseService
from .classify_service import (
    ClassifyService, FileInfo, FolderInfo,
    ManualReviewItem, ClassifyResult, ScanResult
)
from .dedupe_service import DedupeService, DedupeResult, DedupeResultItem
from .hash_service import CalculateHashService
from .zip_service import ZipService
from .verify_service import VerifyService
from .space_manager import SpaceManager
from .queue_manager import QueueManager, UploadTask, UploadResult
from ..models import (
    SourceFile, BackupPackage, ManualReviewItem as ManualReviewItemModel,
    OperationLog
)


@dataclass
class BackupProgress:
    """备份进度"""
    phase: str  # scanning/classifying/deduplicating/compressing/verifying/uploading/completed
    current_item: str
    total_items: int
    completed_items: int
    failed_items: int
    current_status: str
    error_message: Optional[str] = None


@dataclass
class OrchestratorConfig:
    """协调器配置"""
    config: Config
    db_service: DatabaseService
    on_progress: Optional[Callable[[BackupProgress], None]] = None
    on_log: Optional[Callable[[str], None]] = None


class MainOrchestrator:
    """主协调器"""

    def __init__(
        self,
        config: Config,
        credentials: DatabaseCredentials | None = None,
        pool_config: DatabasePoolConfig | None = None
    ):
        """初始化主协调器

        Args:
            config: 应用配置（非敏感）
            credentials: 数据库凭证（从环境变量读取）
            pool_config: 连接池配置
        """
        self.config = config
        self.credentials = credentials or DatabaseCredentials()
        self.pool_config = pool_config or DatabasePoolConfig()

        # 创建数据库服务
        self.db_service = DatabaseService(self.credentials, self.pool_config)

        # 初始化各服务
        self.classify_service = ClassifyService(config.classify)
        self.dedupe_service = DedupeService(config.hash)
        self.verify_service = VerifyService(config.hash, config.zip, config.storage)
        self.space_manager = SpaceManager(config.space)
        self.queue_manager = QueueManager(config.upload, config.zip, self.db_service)

        # 进度状态
        self._progress = BackupProgress(
            phase='idle',
            current_item='',
            total_items=0,
            completed_items=0,
            failed_items=0,
            current_status='就绪'
        )

        # 日志
        self._logger = logging.getLogger(__name__)

    def run(self):
        """运行备份流程"""
        try:
            self._update_progress(
                phase='initializing',
                current_status='正在初始化...'
            )

            # 1. 检查磁盘空间
            self._check_disk_space()

            # 2. 创建数据库表
            self.db_service.create_tables()

            # 3. 扫描源文件夹并进行分类
            scan_results = self._scan_and_classify()

            # 4. 保存人工处理项到数据库（只保存，不处理）
            self._save_manual_review_items(scan_results)

            # 5. 去重比对（只处理正常文件/文件夹，跳过ManualReviewItem）
            deduplicate_results = self._deduplicate(scan_results)

            # 6. 同步处理（压缩+验证），验证完一个立即提交上传任务
            self._start_uploader()
            upload_tasks = self._process_items(deduplicate_results)

            # 7. 等待上传完成
            self._wait_for_uploads()

            # 8. 人工处理检查
            self._check_manual_review_items()

            self._update_progress(
                phase='completed',
                current_status='备份完成'
            )

        except Exception as e:
            self._logger.error(f"备份失败: {e}")
            self._update_progress(
                phase='failed',
                current_status='备份失败',
                error_message=str(e)
            )
            raise

    def _check_disk_space(self):
        """检查磁盘空间"""
        self._update_progress(
            phase='checking_space',
            current_status='正在检查磁盘空间...'
        )
        self.space_manager.check_initial_space(self.config.storage.compress_dir)

    def _scan_source(self) -> list[ScanResult]:
        """扫描源文件夹"""
        self._update_progress(
            phase='scanning',
            current_status='正在扫描源文件夹...'
        )

        source_path = self.config.source.path
        self._log(f"扫描源文件夹: {source_path}")

        results = self.classify_service.scan_source_folder(source_path)

        # 统计
        normal_count = sum(1 for r in results if isinstance(r, (FileInfo, FolderInfo)))
        manual_count = sum(1 for r in results if isinstance(r, ManualReviewItem))

        self._log(f"扫描完成: 正常项目 {normal_count}, 需人工处理 {manual_count}")

        return results

    def _scan_and_classify(self) -> list[ScanResult]:
        """扫描源文件夹并进行分类

        流程：扫描 → 分类检查 → 分离正常项和需人工处理项

        Returns:
            list[ScanResult]: 分类后的结果列表
        """
        self._update_progress(
            phase='scanning',
            current_status='正在扫描并分类...'
        )

        source_path = self.config.source.path
        self._log(f"扫描源文件夹: {source_path}")

        results = self.classify_service.scan_source_folder(source_path)

        # 统计
        normal_count = sum(1 for r in results if isinstance(r, (FileInfo, FolderInfo)))
        manual_count = sum(1 for r in results if isinstance(r, ManualReviewItem))

        self._log(f"扫描完成: 正常项目 {normal_count}, 需人工处理 {manual_count}")

        return results

    def _save_manual_review_items(self, scan_results: list[ScanResult]):
        """保存人工处理项到数据库

        Args:
            scan_results: 扫描分类结果
        """
        self._update_progress(
            phase='saving_manual_review',
            current_status='正在保存人工处理项...'
        )

        # 过滤出需要人工处理的项目
        manual_items = [r for r in scan_results if isinstance(r, ManualReviewItem)]

        if not manual_items:
            self._log("无需人工处理的项目")
            return

        with self.db_service.get_session() as session:
            for item in manual_items:
                # 检查是否已存在
                existing = session.query(ManualReviewItemModel).filter(
                    ManualReviewItemModel.file_path == str(item.source_path)
                ).first()

                if existing:
                    # 已存在，更新状态
                    existing.status = 'pending'
                    self._log(f"更新人工处理项: {item.source_path}")
                else:
                    # 新建记录
                    review_item = ManualReviewItemModel(
                        file_path=str(item.source_path),
                        file_size=item.file_size,
                        file_count=item.file_count,
                        reason=item.reason,
                        status='pending',
                    )
                    session.add(review_item)
                    self._log(f"添加人工处理项: {item.source_path}, 原因: {item.reason}")

        self._log(f"已保存 {len(manual_items)} 个人工处理项")

    def _deduplicate(self, scan_results: list[ScanResult]) -> DedupeResult:
        """去重比对

        注意：只对正常文件/文件夹进行去重，跳过ManualReviewItem

        Args:
            scan_results: 扫描分类结果

        Returns:
            DedupeResult: 去重结果
        """
        self._update_progress(
            phase='deduplicating',
            current_status='正在比对去重...'
        )

        # 过滤出正常文件/文件夹，跳过ManualReviewItem
        normal_items = [
            r for r in scan_results
            if isinstance(r, (FileInfo, FolderInfo))
        ]

        if not normal_items:
            self._log("没有需要处理的文件")
            return DedupeResult(
                to_backup=[],
                already_backup=[],
                not_found_in_db=[]
            )

        with self.db_service.get_session() as session:
            results = self.dedupe_service.compare_and_dedupe(normal_items, session)

        self._log(f"去重完成: 待备份 {len(results.to_backup)}, 已备份 {len(results.already_backup)}")

        return results

    def _check_manual_review_items(self):
        """检查人工处理项并发送邮件通知"""
        self._update_progress(
            phase='checking_manual_review',
            current_status='正在检查人工处理项...'
        )

        with self.db_service.get_session() as session:
            # 查询状态为pending的人工处理项
            pending_items = session.query(ManualReviewItemModel).filter(
                ManualReviewItemModel.status == 'pending'
            ).all()

            if not pending_items:
                self._log("没有待人工处理的项目")
                return

            # 有待处理项，发送邮件通知
            self._send_manual_review_notification(pending_items)

    def _send_manual_review_notification(self, pending_items: list[ManualReviewItemModel]):
        """发送人工处理邮件通知

        Args:
            pending_items: 待处理的人工处理项列表
        """
        from ..config import SMTPCredentials

        credentials = SMTPCredentials()

        # 如果没有配置邮件，跳过
        if not credentials.host or not credentials.username:
            self._log("未配置邮件服务器，跳过人工处理通知")
            return

        # 构建邮件内容
        items_html = ""
        for item in pending_items:
            file_size_gb = (item.file_size / (1024**3)) if item.file_size else 0
            items_html += f"""
            <tr>
                <td>{item.file_path}</td>
                <td>{item.reason}</td>
                <td>{file_size_gb:.2f} GB</td>
                <td>{item.file_count or '-'}</td>
            </tr>
            """

        html_content = f"""
        <html>
        <body>
            <h2>百度网盘备份系统 - 人工处理通知</h2>
            <p>以下项目需要人工处理：</p>
            <table border="1" cellpadding="5">
                <tr>
                    <th>文件路径</th>
                    <th>原因</th>
                    <th>大小</th>
                    <th>文件数</th>
                </tr>
                {items_html}
            </table>
            <p>请登录系统处理这些项目。</p>
        </body>
        </html>
        """

        try:
            msg = MIMEText(html_content, 'html', 'utf-8')
            msg['Subject'] = f'备份系统人工处理通知 - {len(pending_items)}个项目待处理'
            msg['From'] = formataddr(['备份系统', credentials.username])

            # 发送给所有管理员
            recipients = credentials.admin_emails
            msg['To'] = ', '.join(recipients)

            with smtplib.SMTP_SSL(credentials.host, credentials.port) as server:
                server.login(credentials.username, credentials.password)
                server.send_message(msg, from_addr=credentials.username, to_addrs=recipients)

            self._log(f"已发送人工处理通知邮件给 {len(recipients)} 位管理员，包含 {len(pending_items)} 个项目")

        except Exception as e:
            self._log(f"发送人工处理通知邮件失败: {e}")

    def _process_items(self, dedupe_results: DedupeResult) -> list[UploadTask]:
        """同步处理所有项目（压缩+验证），验证完一个立即提交上传任务

        注意：不再返回任务列表，而是立即将任务提交到队列
        """
        total = len(dedupe_results.to_backup)
        self._progress.total_items = total

        for i, item in enumerate(dedupe_results.to_backup):
            self._progress.current_item = str(item.source_path)
            self._progress.completed_items = i

            try:
                # 预留空间
                with self.space_manager.reserve_space(item, self.config.storage.compress_dir):
                    # 压缩
                    self._update_progress(
                        phase='compressing',
                        current_status=f'正在压缩 ({i+1}/{total})'
                    )
                    zip_path = self._compress_item(item)

                    # 验证
                    self._update_progress(
                        phase='verifying',
                        current_status=f'正在验证 ({i+1}/{total})'
                    )
                    if not self._verify_item(item, zip_path):
                        continue  # 验证失败，重新压缩

                    # 记录到数据库
                    self._save_package_info(item, zip_path)

                    # 创建上传任务并立即提交到队列
                    task = UploadTask(
                        zip_path=zip_path,
                        password=self.config.zip.default_password,
                        source_path=item.source_path
                    )
                    self._submit_upload_task(task)

                    self._progress.completed_items += 1

            except Exception as e:
                self._log(f"处理失败: {item.source_path}, 错误: {e}")
                self._progress.failed_items += 1

        return []  # 任务已直接提交到队列，不再返回

    def _compress_item(self, item: DedupeResultItem) -> Path:
        """压缩单个项目"""
        password = self.config.source.password or self.config.zip.default_password

        zip_path = ZipService.zip_item(
            source_item=item.source_path,
            target_dir=self.config.storage.compress_dir,
            password=password,
            compress_level=self.config.zip.compress_level
        )

        return zip_path

    def _verify_item(self, item: DedupeResultItem, zip_path: Path) -> bool:
        """验证单个压缩包"""
        password = self.config.source.password or self.config.zip.default_password

        result = self.verify_service.verify_package(
            zip_path=zip_path,
            source_info=item,
            password=password
        )

        if not result.is_valid:
            self._log(f"验证失败: {zip_path}")
            if result.extracted_path:
                self.verify_service.cleanup_extracted(result.extracted_path)
            # 删除压缩包，重新压缩
            zip_path.unlink(missing_ok=True)
            return False

        # 清理解压目录
        if result.extracted_path:
            self.verify_service.cleanup_extracted(result.extracted_path)

        return True

    def _save_package_info(self, item: DedupeResultItem, zip_path: Path):
        """保存压缩包信息到数据库

        注意：SourceFile保存源文件的hash（用于去重），BackupPackage保存ZIP的hash（用于完整性验证）
        """
        password = self.config.source.password or self.config.zip.default_password

        # 计算源文件Hash（用于去重）
        if isinstance(item, FileInfo):
            source_hashes = CalculateHashService.calculate_file_hash(
                item.source_path,
                self.config.hash.required_hash_algorithms
            )
        else:
            source_hashes = CalculateHashService.calculate_folder_hash(
                {
                    'source_path': str(item.source_path),
                    'classify_result': item.classify_result.value
                },
                self.config.hash.required_hash_algorithms
            )

        # 计算ZIP Hash（用于BackupPackage）
        zip_hashes = CalculateHashService.calculate_file_hash(
            zip_path,
            self.config.hash.required_hash_algorithms
        )

        with self.db_service.get_session() as session:
            # 保存源文件信息（使用源文件hash，用于去重）
            if isinstance(item, FileInfo):
                source_file = SourceFile(
                    file_path=str(item.source_path),
                    file_name=item.source_path.name,
                    file_size=item.file_size,
                    md5_hash=source_hashes['md5'],
                    sha1_hash=source_hashes['sha1'],
                    sha256_hash=source_hashes['sha256'],
                    is_backup=False,
                )
            else:
                source_file = SourceFile(
                    file_path=str(item.source_path),
                    file_name=item.source_path.name,
                    file_size=item.total_size,
                    md5_hash=source_hashes['md5'],
                    sha1_hash=source_hashes['sha1'],
                    sha256_hash=source_hashes['sha256'],
                    is_backup=False,
                )
            session.add(source_file)
            session.flush()

            # 保存压缩包信息（使用ZIP hash，用于完整性验证）
            package = BackupPackage(
                package_path=str(zip_path),
                source_file_id=source_file.id,
                md5_hash=zip_hashes['md5'],
                sha1_hash=zip_hashes['sha1'],
                sha256_hash=zip_hashes['sha256'],
                password=password,
                file_count=1 if isinstance(item, FileInfo) else item.file_count,
                package_size=zip_path.stat().st_size,
                status='pending',
            )
            session.add(package)

    def _start_uploader(self):
        """启动上传队列"""
        self._update_progress(
            phase='uploading',
            current_status='正在上传...'
        )

        # 设置回调
        self.queue_manager.on_success = self._on_upload_success
        self.queue_manager.on_failed = self._on_upload_failed

        # 启动队列
        self.queue_manager.start()
        self._log("上传队列已启动")

    def _submit_upload_task(self, task: UploadTask):
        """提交上传任务到队列"""
        self.queue_manager.add_task(task)
        self._log(f"已提交上传任务: {task.zip_path.name}")

    def _wait_for_uploads(self):
        """等待所有上传任务完成"""
        self._log("等待上传完成...")

        # 等待队列完成
        self.queue_manager._queue.join()

        # 停止队列
        self.queue_manager.stop()

        self._log(f"上传完成: 成功 {self._progress.completed_items}, 失败 {self._progress.failed_items}")

    def _on_upload_success(self, result: UploadResult):
        """上传成功回调"""
        self._log(f"上传成功: {result.task.zip_path}")

        # 清理本地压缩包
        try:
            if result.task.zip_path.exists():
                result.task.zip_path.unlink()
        except Exception:
            pass

        # 清理源文件/文件夹
        try:
            if result.task.source_path.exists():
                if result.task.source_path.is_file():
                    result.task.source_path.unlink()
                else:
                    import shutil
                    shutil.rmtree(result.task.source_path)
                self._log(f"已清理源文件: {result.task.source_path}")
        except Exception as e:
            self._log(f"清理源文件失败: {result.task.source_path}, 错误: {e}")

        # 标记源文件为已备份
        with self.db_service.get_session() as session:
            source_file = session.query(SourceFile).filter(
                SourceFile.file_path == str(result.task.source_path)
            ).first()

            if source_file:
                source_file.is_backup = True
                source_file.backup_time = datetime.utcnow()

    def _on_upload_failed(self, result: UploadResult):
        """上传失败回调"""
        self._log(f"上传失败: {result.task.zip_path}, 错误: {result.error_message}")
        self._progress.failed_items += 1

    def _update_progress(
        self,
        phase: str,
        current_status: str,
        error_message: str | None = None
    ):
        """更新进度"""
        self._progress.phase = phase
        self._progress.current_status = current_status
        if error_message:
            self._progress.error_message = error_message

        if self.config is not None and hasattr(self.config, 'on_progress') and self.config.on_progress:
            self.config.on_progress(self._progress)

    def _log(self, message: str):
        """记录日志"""
        self._logger.info(message)

        if hasattr(self.config, 'on_log') and self.config.on_log:
            self.config.on_log(message)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def stop(self):
        """停止备份"""
        self.queue_manager.stop()

    @property
    def progress(self) -> BackupProgress:
        """获取当前进度"""
        return self._progress
