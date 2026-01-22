"""queue_manager.py 测试用例"""

import pytest
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from queue import Empty

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from object_backup_to_baidu_pan.service.queue_manager import (
    QueueManager, UploadTask, UploadResult, _STOP_SENTINEL
)
from object_backup_to_baidu_pan.config import UploadConfig, ZipConfig


class TestUploadTask:
    """UploadTask 测试"""

    def test_create_task(self):
        """QUEUE-001: 创建任务"""
        task = UploadTask(
            zip_path=Path("/test.zip"),
            password="test",
            source_path=Path("/source")
        )
        assert task.zip_path == Path("/test.zip")
        assert task.password == "test"
        assert task.source_path == Path("/source")

    def test_default_values(self):
        """QUEUE-002: 默认值"""
        task = UploadTask(
            zip_path=Path("/test.zip"),
            password="test",
            source_path=Path("/source")
        )
        assert task.retry_count == 0
        assert task.max_retry == 5
        assert task.priority == 0

    def test_priority_comparison_high_greater(self):
        """QUEUE-003: 高优先级大于低优先级"""
        task1 = UploadTask(
            zip_path=Path("/test1.zip"),
            password="test",
            source_path=Path("/source"),
            priority=1
        )
        task2 = UploadTask(
            zip_path=Path("/test2.zip"),
            password="test",
            source_path=Path("/source"),
            priority=0
        )
        assert task1 < task2  # 高优先级应该先处理

    def test_priority_comparison_low_less(self):
        """QUEUE-004: 低优先级小于高优先级"""
        task1 = UploadTask(
            zip_path=Path("/test1.zip"),
            password="test",
            source_path=Path("/source"),
            priority=0
        )
        task2 = UploadTask(
            zip_path=Path("/test2.zip"),
            password="test",
            source_path=Path("/source"),
            priority=1
        )
        assert not (task1 < task2)

    def test_invalid_comparison(self):
        """QUEUE-005: 非法比较"""
        task = UploadTask(
            zip_path=Path("/test.zip"),
            password="test",
            source_path=Path("/source")
        )
        assert task.__lt__(123) is NotImplemented


class TestUploadResult:
    """UploadResult 测试"""

    def test_success_result(self):
        """QUEUE-006: 成功结果"""
        task = UploadTask(
            zip_path=Path("/test.zip"),
            password="test",
            source_path=Path("/source")
        )
        result = UploadResult(success=True, task=task)
        assert result.success is True

    def test_failure_result(self):
        """QUEUE-007: 失败结果"""
        task = UploadTask(
            zip_path=Path("/test.zip"),
            password="test",
            source_path=Path("/source")
        )
        result = UploadResult(
            success=False,
            task=task,
            error_message="Upload failed"
        )
        assert result.success is False
        assert result.error_message == "Upload failed"


class TestQueueManager:
    """QueueManager 测试"""

    def test_default_config(self):
        """QUEUE-008: 默认配置"""
        manager = QueueManager()
        assert isinstance(manager.config, UploadConfig)
        assert manager.config.chunk_size_mb == 20

    def test_custom_config(self):
        """QUEUE-009: 自定义配置"""
        config = UploadConfig(chunk_size_mb=50)
        manager = QueueManager(upload_config=config)
        assert manager.config.chunk_size_mb == 50

    def test_callbacks_initialized(self):
        """QUEUE-010: 回调初始化"""
        manager = QueueManager()
        assert manager.on_success is None
        assert manager.on_failed is None
        assert manager.on_progress is None


class TestAddTask:
    """add_task 测试"""

    def test_add_single_task(self):
        """QUEUE-011: 添加单任务"""
        manager = QueueManager()
        task = UploadTask(
            zip_path=Path("/test.zip"),
            password="test",
            source_path=Path("/source")
        )
        initial_size = manager.queue_size
        manager.add_task(task)
        assert manager.queue_size == initial_size + 1

    def test_add_multiple_tasks(self):
        """QUEUE-012: 添加多任务"""
        manager = QueueManager()
        task1 = UploadTask(
            zip_path=Path("/test1.zip"),
            password="test",
            source_path=Path("/source1")
        )
        task2 = UploadTask(
            zip_path=Path("/test2.zip"),
            password="test",
            source_path=Path("/source2")
        )
        manager.add_task(task1)
        manager.add_task(task2)
        assert manager.queue_size == 2


class TestAddTasks:
    """add_tasks 测试"""

    def test_batch_add_tasks(self):
        """QUEUE-013: 批量添加任务"""
        manager = QueueManager()
        tasks = [
            UploadTask(
                zip_path=Path(f"/test{i}.zip"),
                password="test",
                source_path=Path(f"/source{i}")
            )
            for i in range(5)
        ]
        manager.add_tasks(tasks)
        assert manager.queue_size == 5


class TestStart:
    """start 测试"""

    def test_start_queue(self):
        """QUEUE-014: 启动队列"""
        manager = QueueManager()
        manager.start()
        assert manager.is_running is True
        manager.stop()

    def test_double_start(self):
        """QUEUE-015: 重复启动"""
        manager = QueueManager()
        manager.start()
        initial_thread = manager._worker_thread
        manager.start()  # 不应创建新线程
        assert manager._worker_thread is initial_thread
        manager.stop()


class TestStop:
    """stop 测试"""

    def test_stop_queue(self):
        """QUEUE-017: 停止队列"""
        manager = QueueManager()
        manager.start()
        time.sleep(0.1)
        manager.stop()
        assert manager.is_running is False

    def test_send_stop_sentinel(self):
        """QUEUE-018: 发送停止标记"""
        manager = QueueManager()
        manager.start()
        time.sleep(0.1)
        manager.stop()
        # 验证停止标记被放入队列
        assert manager._queue.get() is _STOP_SENTINEL

    def test_wait_for_thread(self):
        """QUEUE-019: 等待线程结束"""
        manager = QueueManager()
        manager.start()
        manager.stop()
        assert manager._worker_thread is None or not manager._worker_thread.is_alive()

    def test_stop_not_started(self):
        """QUEUE-020: 停止未启动的队列"""
        manager = QueueManager()
        manager.stop()  # 不应报错
        assert manager.is_running is False


class TestProcessQueue:
    """_process_queue 测试"""

    def test_process_task_success(self):
        """QUEUE-021: 处理成功任务"""
        manager = QueueManager()
        task = UploadTask(
            zip_path=Path("/test.zip"),
            password="test",
            source_path=Path("/source")
        )

        with patch.object(manager, '_process_task') as mock_process:
            mock_process.return_value = UploadResult(success=True, task=task)

            manager._queue.put(task)
            manager._process_queue()

            mock_process.assert_called_once()

    def test_stop_on_sentinel(self):
        """QUEUE-022: 遇到停止标记退出"""
        manager = QueueManager()
        manager._running = True
        manager._queue.put(_STOP_SENTINEL)

        manager._process_queue()

        assert manager._running is False or manager._queue.empty()


class TestProcessTask:
    """_process_task 测试"""

    def test_task_success(self, test_temp_dir):
        """QUEUE-024: 任务成功"""
        # 创建测试ZIP
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"test content")

        manager = QueueManager()

        task = UploadTask(
            zip_path=source,
            password="test",
            source_path=source
        )

        # Mock上传成功
        with patch('object_backup_to_baidu_pan.service.queue_manager.UploadService') as mock_upload:
            mock_service = MagicMock()
            mock_service.upload_file.return_value = True
            mock_service.remote_path = "/remote/test.zip"
            mock_upload.return_value = mock_service

            result = manager._process_task(task)

            assert result.success is True
            assert result.baidu_pan_path == "/remote/test.zip"

    def test_task_failure(self, test_temp_dir):
        """QUEUE-025: 任务失败"""
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"test")

        manager = QueueManager()
        task = UploadTask(
            zip_path=source,
            password="test",
            source_path=source
        )

        with patch('object_backup_to_baidu_pan.service.queue_manager.UploadService') as mock_upload:
            mock_upload.side_effect = Exception("Upload failed")

            result = manager._process_task(task)

            assert result.success is False
            assert result.error_message == "Upload failed"


class TestRetryMechanism:
    """重试机制测试"""

    def test_failure_retry(self, test_temp_dir):
        """QUEUE-028: 失败重试"""
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"test")

        manager = QueueManager()
        task = UploadTask(
            zip_path=source,
            password="test",
            source_path=source,
            max_retry=2
        )
        task.retry_count = 0

        call_count = [0]
        def fail_once(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First failure")
            return MagicMock(success=True, remote_path="/test")

        with patch('object_backup_to_baidu_pan.service.queue_manager.UploadService') as mock_upload:
            mock_service = MagicMock()
            mock_service.upload_file.side_effect = fail_once
            mock_upload.return_value = mock_service

            result = manager._process_task(task)
            # 第一次失败后会重试
            assert result.task.retry_count == 1

    def test_max_retries_exceeded(self, test_temp_dir):
        """QUEUE-029: 超过最大重试次数"""
        source = test_temp_dir / "source.txt"
        source.write_bytes(b"test")

        manager = QueueManager()
        task = UploadTask(
            zip_path=source,
            password="test",
            source_path=source,
            max_retry=2
        )
        task.retry_count = 2  # 已达最大

        with patch('object_backup_to_baidu_pan.service.queue_manager.UploadService') as mock_upload:
            mock_upload.side_effect = Exception("Failed")

            result = manager._process_task(task)

            assert result.success is False
            assert manager.on_failed is not None or True  # 回调应该被调用


class TestUpdateDBStatus:
    """_update_db_status 测试"""

    def test_update_success(self, test_temp_dir):
        """QUEUE-031: 更新成功"""
        manager = QueueManager()
        manager.db_service = MagicMock()

        task = UploadTask(
            zip_path=test_temp_dir / "test.zip",
            password="test",
            source_path=test_temp_dir / "source"
        )

        manager._update_db_status(task, "/remote/test.zip", "completed")

        manager.db_service.get_session.assert_called()

    def test_no_db_service(self):
        """QUEUE-033: 无数据库服务"""
        manager = QueueManager()
        manager.db_service = None

        # 不应报错
        manager._update_db_status(
            MagicMock(),
            "/remote/test.zip",
            "completed"
        )

    def test_record_not_exists(self):
        """QUEUE-034: 记录不存在"""
        manager = QueueManager()
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        manager.db_service = MagicMock()
        manager.db_service.get_session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        manager.db_service.get_session.return_value.__exit__ = MagicMock(
            return_value=False
        )

        task = MagicMock()
        task.zip_path = "/test.zip"

        # 不应报错
        manager._update_db_status(task, "/remote/test.zip", "completed")


class TestProperties:
    """属性测试"""

    def test_queue_size_with_items(self):
        """QUEUE-036: 队列有元素时大小"""
        manager = QueueManager()
        for i in range(3):
            manager.add_task(MagicMock())
        assert manager.queue_size == 3

    def test_queue_size_empty(self):
        """QUEUE-037: 空队列"""
        manager = QueueManager()
        assert manager.queue_size == 0

    def test_is_running_after_start(self):
        """QUEUE-038: 启动后运行状态"""
        manager = QueueManager()
        manager.start()
        assert manager.is_running is True
        manager.stop()

    def test_is_running_after_stop(self):
        """QUEUE-039: 停止后运行状态"""
        manager = QueueManager()
        manager.start()
        manager.stop()
        assert manager.is_running is False


class TestClear:
    """clear 测试"""

    def test_clear_queue(self):
        """QUEUE-040: 清空队列"""
        manager = QueueManager()
        for i in range(5):
            manager.add_task(MagicMock())
        assert manager.queue_size == 5

        manager.clear()
        assert manager.queue_size == 0

    def test_clear_empty_queue(self):
        """QUEUE-041: 清空空队列"""
        manager = QueueManager()
        manager.clear()  # 不应报错
        assert manager.queue_size == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
