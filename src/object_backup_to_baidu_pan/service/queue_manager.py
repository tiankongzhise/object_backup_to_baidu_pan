"""队列管理器

管理上传任务队列，支持后台线程处理、失败重试和断点续传。
"""

from dataclasses import dataclass
from pathlib import Path
from queue import Queue, Empty
from threading import Thread, Event
from typing import Callable, Optional
from typing import Union
from sqlalchemy.orm import Session
from .upload_service import UploadService
from .space_manager import SpaceManager
from .hash_service import CalculateHashService
from ..config import UploadConfig, ZipConfig
from ..models import BackupPackage
from datetime import datetime


# 停止标记，用于唤醒阻塞的队列获取
_STOP_SENTINEL = object()


@dataclass
class UploadTask:
    """上传任务"""
    zip_path: Path
    password: str
    source_path: Path
    source_folder_name: str = ""  # 源文件夹名称，用于远端路径生成
    retry_count: int = 0
    max_retry: int = 5
    priority: int = 0  # 0=普通, 1=高优先级

    def __lt__(self, other):
        """用于优先级队列排序"""
        if not isinstance(other, UploadTask):
            return NotImplemented
        return self.priority > other.priority  # 高优先级先处理


@dataclass
class UploadResult:
    """上传结果"""
    success: bool
    task: UploadTask
    baidu_pan_path: Optional[str] = None
    error_message: Optional[str] = None


class QueueManager:
    """队列管理器"""

    def __init__(
        self,
        upload_config: UploadConfig | None = None,
        zip_config: ZipConfig | None = None,
        db_service=None  # DatabaseService
    ):
        """初始化队列管理器

        Args:
            upload_config: 上传配置
            zip_config: ZIP配置
            db_service: 数据库服务（用于更新状态）
        """
        self.config = upload_config or UploadConfig()
        self.zip_config = zip_config or ZipConfig()
        self.db_service = db_service

        self._queue: Queue = Queue()
        self._running = False
        self._worker_thread: Thread | None = None
        self._stop_event = Event()

        # 回调函数
        self.on_success: Optional[Callable[[UploadResult], None]] = None
        self.on_failed: Optional[Callable[[UploadResult], None]] = None
        self.on_progress: Optional[Callable[[UploadTask, float], None]] = None

    def add_task(self, task: UploadTask):
        """添加上传任务

        Args:
            task: 上传任务
        """
        self._queue.put(task)

    def add_tasks(self, tasks: list[UploadTask]):
        """批量添加上传任务

        Args:
            tasks: 上传任务列表
        """
        for task in tasks:
            self.add_task(task)

    def start(self):
        """启动队列处理"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()
        self._worker_thread = Thread(target=self._process_queue, daemon=True)
        self._worker_thread.start()

    def stop(self):
        """停止队列处理"""
        self._running = False
        self._stop_event.set()

        # 发送停止标记以唤醒阻塞的队列获取
        try:
            self._queue.put_nowait(_STOP_SENTINEL)
        except Exception:
            pass

        if self._worker_thread:
            self._worker_thread.join(timeout=5)
            self._worker_thread = None

    def _process_queue(self):
        """队列处理主循环"""
        while self._running and not self._stop_event.is_set():
            try:
                # 获取任务，超时1秒
                task = self._queue.get(timeout=1)

                # 检查是否是停止标记
                if task is _STOP_SENTINEL:
                    # 标记完成并退出
                    self._queue.task_done()
                    break

            except Empty:
                continue

            try:
                result = self._process_task(task)

                if result.success:
                    if self.on_success:
                        self.on_success(result)
                else:
                    if result.task.retry_count < result.task.max_retry:
                        # 重试
                        result.task.retry_count += 1
                        self._queue.put(result.task)
                    else:
                        if self.on_failed:
                            self.on_failed(result)

            except Exception as e:
                # 处理异常
                if task.retry_count < task.max_retry:
                    task.retry_count += 1
                    self._queue.put(task)
                else:
                    if self.on_failed:
                        self.on_failed(UploadResult(
                            success=False,
                            task=task,
                            error_message=str(e)
                        ))

            finally:
                self._queue.task_done()

    def _process_task(self, task: UploadTask) -> UploadResult:
        """处理单个上传任务

        Args:
            task: 上传任务

        Returns:
            UploadResult: 上传结果
        """
        try:
            # 执行上传
            upload_service = UploadService(
                file_path=str(task.zip_path),
                chunk_size=self.config.chunk_size_mb * 1024 * 1024,
                source_folder_name=task.source_folder_name
            )

            result = upload_service.upload_file(
                file_path=task.zip_path,
                chunk_size=self.config.chunk_size_mb * 1024 * 1024
            )

            # 获取远程路径
            remote_path = upload_service.remote_path

            # 更新数据库
            if self.db_service:
                self._update_db_status(task, remote_path, 'completed')

            return UploadResult(
                success=True,
                task=task,
                baidu_pan_path=remote_path,
            )

        except Exception as e:
            # 更新数据库状态
            if self.db_service:
                self._update_db_status(task, None, 'failed', str(e))

            return UploadResult(
                success=False,
                task=task,
                error_message=str(e),
            )

    def _update_db_status(
        self,
        task: UploadTask,
        baidu_pan_path: str | None,
        status: str,
        error_message: str | None = None
    ):
        """更新数据库状态

        Args:
            task: 上传任务
            baidu_pan_path: 百度云盘路径
            status: 状态
            error_message: 错误信息
        """
        if not self.db_service:
            return

        try:
            with self.db_service.get_session() as session:
                # 查找记录
                package = session.query(BackupPackage).filter(
                    BackupPackage.package_path == str(task.zip_path)
                ).first()

                if package:
                    package.status = status
                    if baidu_pan_path:
                        package.baidu_pan_path = baidu_pan_path
                    package.uploaded_at = datetime.utcnow()

        except Exception:
            pass  # 静默处理数据库更新错误

    @property
    def queue_size(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running

    def clear(self):
        """清空队列"""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except Empty:
                break
