# 百度网盘备份工具 - API文档

## 项目概述

**object_backup_to_baidu_pan** - 将本地文件/文件夹加密打包后备份到百度网盘的工具。

- **版本**: 0.2.0
- **Python版本**: 3.13+
- **主要依赖**: SQLAlchemy, PyQt6, pyzipper, tqdm

---

## 目录

1. [系统架构](#系统架构)
2. [主流程图](#主流程图)
3. [模块详解](#模块详解)
4. [配置说明](#配置说明)
5. [数据库模型](#数据库模型)
6. [API参考](#api参考)
7. [调用关系图](#调用关系图)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                          入口层 (main.py)                            │
│  run_gui() / run_cli()                                              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       协调层 (orchestrator.py)                       │
│                     MainOrchestrator - 主协调器                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  run() 执行流程:                                              │   │
│  │  1. 检查磁盘空间 → 2. 创建数据库表 → 3. 扫描分类             │   │
│  │  4. 保存人工处理项 → 5. 去重比对 → 6. 压缩验证               │   │
│  │  7. 异步上传 → 8. 人工处理检查                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐    ┌───────────────────────┐    ┌───────────────┐
│   分类服务     │    │       去重服务        │    │   验证服务    │
│classify_service│    │   dedupe_service      │    │verify_service │
│ - 扫描文件夹   │    │ - Hash计算            │    │ - 解压验证    │
│ - 分类检查     │    │ - 数据库比对          │    │ - Hash比对    │
└───────┬───────┘    └───────────┬───────────┘    └───────┬───────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌───────────────┐    ┌───────────────────────┐    ┌───────────────┐
│   Hash服务     │    │       ZIP服务         │    │   空间管理    │
│hash_service   │    │    zip_service         │    │space_manager │
│ - 文件Hash    │    │ - AES加密压缩          │    │ - 磁盘空间    │
│ - 文件夹Hash  │    │ - 解压验证             │    │ - 空间预留    │
└───────┬───────┘    └───────────┬───────────┘    └───────────────┘
        │                        │
        ▼                        ▼
┌─────────────────────────────────────────────────────┐
│              队列管理 (queue_manager.py)             │
│            QueueManager - 异步任务队列               │
│  ┌─────────────────────────────────────────────┐   │
│  │  add_task() → start() → _process_queue()   │   │
│  └─────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────┐
│              上传服务 (upload_service.py)            │
│            UploadService - 百度网盘上传              │
│  ┌─────────────────────────────────────────────┐   │
│  │  precreate() → upload() → create()          │   │
│  └─────────────────────────────────────────────┘   │
└───────────────────────────────┬─────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────┐
│                    数据库层                          │
│              DatabaseService + Models               │
│  source_files / backup_packages /                   │
│  manual_review_items / operation_logs              │
└─────────────────────────────────────────────────────┘
```

---

## 主流程图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           MainOrchestrator.run()                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    1. 检查磁盘空间            │
                    │    SpaceManager               │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    2. 创建数据库表            │
                    │    DatabaseService            │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    3. 扫描并分类              │
                    │    ClassifyService            │
                    │                               │
                    │  ┌─────────────────────────┐  │
                    │  │ scan_source_folder()    │  │
                    │  │ ├─ _classify_file()     │  │
                    │  │ └─ _classify_folder()   │  │
                    │  └─────────────────────────┘  │
                    └───────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    ▼                               ▼
            ┌───────────────┐               ┌───────────────┐
            │  正常文件/     │               │  超限项目     │
            │  文件夹        │               │  (Manual      │
            │  FileInfo/     │               │  ReviewItem)  │
            │  FolderInfo    │               └───────────────┘
            └───────┬───────┘                       │
                    │                               ▼
                    │               ┌───────────────────────────────┐
                    │               │    4. 保存人工处理项          │
                    │               │    保存到DB (pending状态)     │
                    │               └───────────────────────────────┘
                    │                               │
                    ▼                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          5. 去重比对                                     │
│                          DedupeService                                   │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  compare_and_dedupe()                                           │   │
│  │                                                                 │   │
│  │  For each FileInfo/FolderInfo:                                  │   │
│  │    1. CalculateHashService.calculate_file_hash()               │   │
│  │       or calculate_folder_hash()                               │   │
│  │    2. Query DB by MD5/SHA1/SHA256                              │   │
│  │    3. Classify:                                                 │   │
│  │       - Found in DB → already_backup                           │   │
│  │       - Not found → to_backup                                  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          6. 同步处理                                     │
│                          循环处理 to_backup 列表                         │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  For each item in to_backup:                                   │   │
│  │                                                                 │   │
│  │  6.1 预留磁盘空间                                               │   │
│  │      SpaceManager.reserve_space()                              │   │
│  │                                                                 │   │
│  │  6.2 ZIP压缩                                                    │   │
│  │      ZipService.zip_item()                                     │   │
│  │      ↓                                                          │   │
│  │      生成: /tmp/compress/YYYYMMDD/解压密码_{pwd}/xxx.zip       │   │
│  │                                                                 │   │
│  │  6.3 解压验证                                                   │   │
│  │      VerifyService.verify_package()                            │   │
│  │      ├─ ZipService.unzip_item()                               │   │
│  │      ├─ CalculateHashService.calculate_xxx_hash()             │   │
│  │      └─ _compare_hashes()                                     │   │
│  │                                                                 │   │
│  │  6.4 保存到数据库                                               │   │
│  │      - SourceFile (文件信息)                                   │   │
│  │      - BackupPackage (压缩包信息)                              │   │
│  │                                                                 │   │
│  │  6.5 创建上传任务                                               │   │
│  │      UploadTask(zip_path, password, source_path)              │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          7. 异步上传                                     │
│                          QueueManager                                    │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  add_tasks() → start()                                         │   │
│  │                                                                 │   │
│  │  Worker Thread:                                                 │   │
│  │    For each UploadTask:                                        │   │
│  │      1. UploadService.precreate()     ← 创建上传任务           │   │
│  │      2. UploadService.upload()        ← 分片上传               │   │
│  │      3. UploadService.create()        ← 合并分片               │   │
│  │      4. Update DB status (completed)                          │   │
│  │      5. Cleanup local ZIP file                                 │   │
│  │                                                                 │   │
│  │  Callbacks:                                                     │   │
│  │    - on_success: 标记文件已备份                                 │   │
│  │    - on_failed: 记录失败日志                                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    8. 人工处理检查            │
                    │    检查pending项 → 发送邮件   │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │           完成                │
                    └───────────────────────────────┘
```

---

## 模块详解

### 1. main.py - 入口模块

#### 函数

| 函数名 | 入参 | 返回值 | 说明 |
|--------|------|--------|------|
| `run_gui()` | 无 | None | 启动PyQt6图形界面 |
| `run_cli(config_path: str)` | config_path: 配置文件路径 | None | 命令行模式运行 |
| `main()` | 无 | None | 主入口，根据参数决定运行模式 |

#### 使用示例

```bash
# GUI模式（默认）
python -m object_backup_to_baidu_pan

# CLI模式
python -m object_backup_to_baidu_pan --config config.toml

# 指定配置文件
python -m object_backup_to_baidu_pan --config /path/to/config.toml
```

---

### 2. config.py - 配置模块

#### 配置类

##### HashConfig
```python
@dataclass
class HashConfig:
    required_hash_algorithms: list[str]  # 默认: ['md5', 'sha1', 'sha256']
```

##### ClassifyConfig
```python
@dataclass
class ClassifyConfig:
    file_oversize: int       # 文件大小限制，默认20GB
    folder_oversize: int     # 文件夹大小限制，默认20GB
    overcount: int           # 直接子文件数限制，默认200
    unzip_folder: Path       # 解压目录，默认/tmp/unzip
```

##### ZipConfig
```python
@dataclass
class ZipConfig:
    salt: dict               # AES加密盐值
    salt_length: int         # 盐长度，默认16
    compress_level: int      # 压缩级别，0-9，默认0（存储模式）
    default_password: str    # 默认密码，默认'backup123'
```

##### UploadConfig
```python
@dataclass
class UploadConfig:
    chunk_size_mb: int       # 分片大小(MB)，默认20
    retry_times: int         # 重试次数，默认5
    baidu_pan_dir: str       # 百度盘目录，默认'/item_backup'
    default_password: str    # 默认密码
```

##### SpaceConfig
```python
@dataclass
class SpaceConfig:
    disk_limit_gb: int       # 磁盘使用限制(GB)，默认80
```

##### DatabasePoolConfig
```python
@dataclass
class DatabasePoolConfig:
    pool_size: int           # 连接池大小，默认5
    max_overflow: int        # 最大溢出连接，默认10
    pool_timeout: int        # 连接超时(秒)，默认30
    pool_recycle: int        # 连接回收时间(秒)，默认3600
    pool_pre_ping: bool      # 连接前检测，默认True
    echo: bool               # SQL日志，默认False

    def get_url(self, host, port, username, password, name) -> str:
        """构建数据库URL"""
        # 返回: mysql+pymysql://user:pass@host:port/name
```

#### 凭证类（从环境变量读取）

##### DatabaseCredentials
```python
class DatabaseCredentials:
    host: str        # MYSQL_HOST，默认localhost
    port: int        # MYSQL_PORT，默认3306
    username: str    # MYSQL_USER，默认root
    password: str    # MYSQL_PASSWORD，默认空
    name: str        # MYSQL_DATABASE，默认backup_db

    @property
    def url(self) -> str:
        """返回完整数据库URL"""
```

##### BaiduPanCredentials
```python
class BaiduPanCredentials:
    access_token: str   # BAIDU_PAN_ACCESS_TOKEN
    refresh_token: str  # BAIDU_PAN_REFRESH_TOKEN
    app_key: str        # BAIDU_PAN_APP_KEY
    secret_key: str     # BAIDU_PAN_SECRET_KEY
```

##### SMTPCredentials
```python
class SMTPCredentials:
    host: str     # SMTP_HOST
    port: int     # SMTP_PORT，默认465
    username: str # SMTP_USER
    password: str # SMTP_PASSWORD
```

#### 环境变量读取函数

| 函数名 | 入参 | 返回值 | 说明 |
|--------|------|--------|------|
| `get_env(key, default)` | key: str, default: str | str | 获取字符串环境变量 |
| `get_env_int(key, default)` | key: str, default: int | int | 获取整数环境变量 |
| `get_env_bool(key, default)` | key: str, default: bool | bool | 获取布尔环境变量 |

---

### 3. service/classify_service.py - 分类服务

#### 枚举

##### ItemType
```python
class ItemType(Enum):
    FILE = "file"     # 文件
    FOLDER = "folder" # 文件夹
```

##### ClassifyResult
```python
class ClassifyResult(Enum):
    NORMAL_FILE = "normal_file"       # 正常文件
    NORMAL_FOLDER = "normal_folder"   # 正常文件夹
    OVERSIZE_FILE = "oversize_file"   # 超大文件
    OVERSIZE_FOLDER = "oversize_folder" # 超大文件夹
    OVERCOUNT = "overcount"           # 文件数超限
    EMPTY_FOLDER = "empty_folder"     # 空文件夹
```

#### 数据类

##### FileInfo
```python
@dataclass
class FileInfo:
    source_path: Path              # 文件路径
    file_name: str                 # 文件名
    file_size: int                 # 文件大小(字节)
    classify_result: ClassifyResult  # 分类结果
    item_type: ItemType = ItemType.FILE  # 项目类型（只读属性）
```

##### FolderInfo
```python
@dataclass
class FolderInfo:
    source_path: Path              # 文件夹路径
    folder_name: str               # 文件夹名
    file_count: int                # 子文件总数（递归）
    total_size: int                # 总大小(字节)
    classify_result: ClassifyResult  # 分类结果
    item_type: ItemType = ItemType.FOLDER  # 项目类型（只读属性）
```

##### ManualReviewItem
```python
@dataclass
class ManualReviewItem:
    source_path: Path              # 项目路径
    reason: str                    # 原因: size_exceeded / overcount / empty_folder
    file_size: int | None          # 文件大小
    file_count: int | None         # 文件数
    classify_result: ClassifyResult  # 分类结果
```

#### 类型别名

```python
ScanResult = Union[FileInfo, FolderInfo, ManualReviewItem]
```

#### ClassifyService

```python
class ClassifyService:
    def __init__(self, config: ClassifyConfig | None = None):
        """初始化分类服务"""

    def scan_source_folder(self, source_path: str | Path) -> list[ScanResult]:
        """扫描源文件夹，返回分类结果列表

        Args:
            source_path: 源文件夹路径

        Returns:
            list[ScanResult]: 包含FileInfo/FolderInfo/ManualReviewItem的列表

        Raises:
            FileNotFoundError: 源文件夹不存在
            NotADirectoryError: 路径不是文件夹
        """

    def _classify_file(self, file_path: Path) -> FileInfo | ManualReviewItem:
        """分类单个文件"""

    def _classify_folder(self, folder_path: Path) -> FolderInfo | ManualReviewItem:
        """分类单个文件夹"""

    def _count_all_files(self, folder_path: Path) -> tuple[int, int]:
        """递归统计文件夹的文件数和总大小

        Returns:
            tuple[int, int]: (文件数量, 总大小)
        """
```

---

### 4. service/dedupe_service.py - 去重服务

#### DedupeResult
```python
@dataclass
class DedupeResult:
    to_backup: list[DedupeResultItem]      # 需要备份
    already_backup: list[DedupeResultItem] # 已备份（可跳过）
    not_found_in_db: list[DedupeResultItem] # 数据库无记录
```

#### DedupeService

```python
class DedupeService:
    def __init__(self, hash_config: HashConfig | None = None):
        """初始化去重服务"""

    def compare_and_dedupe(
        self,
        items: list[ScanResult],
        session: Session
    ) -> DedupeResult:
        """与数据库比对，进行去重处理

        Args:
            items: 分类后的项目列表（仅处理FileInfo/FolderInfo）
            session: SQLAlchemy会话

        Returns:
            DedupeResult: 去重结果
        """

    def _query_by_hashes(
        self,
        session: Session,
        hashes: dict
    ) -> SourceFile | None:
        """根据Hash值查询数据库

        Returns:
            匹配的SourceFile记录，不存在返回None
        """

    def save_source_files(
        self,
        items: list[DedupeResultItem],
        session: Session
    ):
        """保存源文件信息到数据库"""

    def mark_as_backup(
        self,
        item: DedupeResultItem,
        session: Session
    ):
        """标记文件为已备份"""
```

---

### 5. service/zip_service.py - ZIP服务

#### ZipService

```python
class ZipService:
    @staticmethod
    def zip_item(
        source_item: PathLike,
        target_dir: PathLike,
        password: str | None = None,
        compress_level: int = 6
    ) -> pathlib.Path:
        """压缩文件或文件夹为AES加密ZIP

        Args:
            source_item: 源文件或文件夹路径
            target_dir: 目标目录
            password: 压缩密码（可选，设置则使用AES加密）
            compress_level: 压缩级别0-9，默认0（存储模式）

        Returns:
            pathlib.Path: 生成的ZIP文件路径

        Raises:
            FileNotFoundError: 源路径不存在
            IsADirectoryError: 目标路径是文件
            TypeError: 压缩级别不是整数

        Example:
            >>> ZipService.zip_item('/path/folder', '/tmp/compress', 'password', 0)
            PosixPath('/tmp/compress/20260118/解压密码_password/folder.zip')
        """

    @staticmethod
    def unzip_item(
        zip_path: PathLike,
        target_dir: PathLike | None = None,
        password: str | None = None
    ) -> pathlib.Path:
        """解压ZIP文件到目标目录

        Args:
            zip_path: ZIP文件路径
            target_dir: 目标目录（默认使用ZipConfig.unzip_folder）
            password: 解压密码（可选）

        Returns:
            pathlib.Path: 解压后的根目录路径

        Raises:
            FileNotFoundError: ZIP文件不存在
            RuntimeError: 解压失败（如密码错误）
        """
```

---

### 6. service/verify_service.py - 验证服务

#### VerifyResult
```python
@dataclass
class VerifyResult:
    is_valid: bool                    # 验证是否通过
    extracted_path: Path | None       # 解压目录路径
    extracted_hashes: dict | None     # 解压后的Hash值
    source_hashes: dict | None        # 源文件的Hash值
    error_message: str | None         # 错误信息
```

#### VerifyService

```python
class VerifyService:
    def __init__(
        self,
        hash_config: HashConfig | None = None,
        zip_config: ZipConfig | None = None,
        storage_config: StorageConfig | None = None
    ):
        """初始化验证服务"""

    def verify_package(
        self,
        zip_path: Path,
        source_info: FileInfo | FolderInfo,
        password: str | None = None
    ) -> VerifyResult:
        """验证ZIP压缩包

        流程:
        1. 解压ZIP到临时目录
        2. 计算解压后文件的Hash
        3. 与源文件Hash比对

        Args:
            zip_path: ZIP文件路径
            source_info: 源文件/文件夹信息
            password: ZIP解压密码

        Returns:
            VerifyResult: 验证结果
        """

    def _compare_hashes(self, extracted: dict, source: dict) -> bool:
        """比较两组Hash值"""

    def cleanup_extracted(self, extracted_path: Path):
        """清理解压目录"""
```

---

### 7. service/space_manager.py - 空间管理

#### SpaceInfo
```python
@dataclass
class SpaceInfo:
    total_bytes: int      # 总空间(字节)
    used_bytes: int       # 已使用空间(字节)
    available_bytes: int  # 可用空间(字节)
    used_percent: float   # 使用百分比
```

#### SpaceManager

```python
class SpaceManager:
    def __init__(self, config: SpaceConfig | None = None):
        """初始化空间管理器"""

    def get_disk_space(self, path: Path) -> SpaceInfo:
        """获取磁盘空间信息

        Returns:
            SpaceInfo: 磁盘空间信息
        """

    def calculate_required_space(
        self,
        item: FileInfo | FolderInfo
    ) -> int:
        """计算处理文件所需空间

        Returns:
            int: 所需空间（字节）
        """

    def can_process(
        self,
        item: FileInfo | FolderInfo,
        path: Path
    ) -> bool:
        """检查是否可以处理该文件"""

    def check_initial_space(self, path: Path) -> bool:
        """检查初始化时的磁盘空间

        Raises:
            ValueError: 磁盘空间不足
        """

    @contextmanager
    def reserve_space(self, item: FileInfo | FolderInfo, path: Path):
        """预留空间上下文管理器

        用法:
            with space_manager.reserve_space(item, target_dir):
                # 处理文件
                # 空间自动预留和释放
        """

    def wait_for_space(
        self,
        item: FileInfo | FolderInfo,
        path: Path,
        timeout: int = 300
    ) -> bool:
        """等待可用空间

        Args:
            timeout: 超时时间（秒），默认300

        Raises:
            TimeoutError: 等待超时
        """

    def release_space(self, item: FileInfo | FolderInfo):
        """释放预留空间"""
```

---

### 8. service/queue_manager.py - 队列管理

#### UploadTask
```python
@dataclass
class UploadTask:
    zip_path: Path           # ZIP文件路径
    password: str            # ZIP密码
    source_path: Path        # 源文件路径
    retry_count: int = 0     # 已重试次数
    max_retry: int = 5       # 最大重试次数
    priority: int = 0        # 优先级（0普通，1高）
```

#### UploadResult
```python
@dataclass
class UploadResult:
    success: bool              # 是否成功
    task: UploadTask           # 关联的任务
    baidu_pan_path: str | None # 百度盘路径
    error_message: str | None  # 错误信息
```

#### QueueManager

```python
class QueueManager:
    def __init__(
        self,
        upload_config: UploadConfig | None = None,
        zip_config: ZipConfig | None = None,
        db_service: DatabaseService | None = None
    ):
        """初始化队列管理器"""

    def add_task(self, task: UploadTask):
        """添加单个上传任务"""

    def add_tasks(self, tasks: list[UploadTask]):
        """批量添加上传任务"""

    def start(self):
        """启动队列处理（后台线程）"""

    def stop(self):
        """停止队列处理"""

    def clear(self):
        """清空队列"""

    @property
    def queue_size(self) -> int:
        """获取队列大小"""

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
```

---

### 9. service/upload_service/upload_service.py - 百度网盘上传

#### UploadService

```python
class UploadService:
    def __init__(
        self,
        file_path: str | Path = '',
        chunk_size: int = 20 * 1024 * 1024,  # 默认20MB
        rtype: int = 1,
        env_path: str | Path = 'upload.env',
        temp_dir: str | Path | None = None
    ):
        """初始化上传服务

        Args:
            file_path: 文件路径
            chunk_size: 分片大小（字节），默认20MB
            rtype: 上传类型
            env_path: 环境变量文件路径
            temp_dir: 临时目录
        """

    def precreate(self) -> 'UploadService':
        """预创建上传任务

        流程:
        1. 分片文件
        2. 计算每个分片的MD5
        3. 调用百度API预创建

        Returns:
            self: 返回自身以便链式调用

        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件路径是目录
        """

    def upload(self) -> 'UploadService':
        """上传文件分片

        Returns:
            self: 返回自身以便链式调用
        """

    def create(self) -> dict:
        """合并分片完成上传

        Returns:
            dict: API响应
        """

    def upload_file(
        self,
        file_path: str | Path,
        chunk_size: int = 20 * 1024 * 1024,
        rtype: int = 1,
        temp_dir: str | Path | None = None
    ) -> dict:
        """一键上传（便捷方法）

        等价于: precreate().upload().create()

        Args:
            file_path: 文件路径
            chunk_size: 分片大小
            rtype: 上传类型
            temp_dir: 临时目录

        Returns:
            dict: API响应
        """
```

---

### 10. service/upload_service/utils.py - 路径解析

```python
def extract_date_and_password_from_path(path: str) -> tuple[str | None, str | None]:
    """从路径中提取日期和压缩密码

    Args:
        path: 文件路径

    Returns:
        tuple: (日期, 密码)
            - 日期格式: YYYYMMDD
            - 密码: 从"解压密码_"后提取

    Example:
        >>> extract_date_and_password_from_path(
        ...     "D:/compress/20260118/解压密码_password/file.zip"
        ... )
        ('20260118', 'password')
    """


def extract_date_and_password_from_path_strict(path: str) -> tuple[str | None, str | None]:
    """从路径中严格提取日期和压缩密码"""
```

---

## 数据库模型

### 1. SourceFile - 源文件表
```python
class SourceFile(Base):
    __tablename__ = 'source_files'

    id: Mapped[int]              # 主键
    file_path: Mapped[str]       # 文件路径（唯一索引）
    file_name: Mapped[str]       # 文件名
    file_size: Mapped[int]       # 文件大小

    # Hash值（联合索引用于去重）
    md5_hash: Mapped[str]        # MD5 (CHAR[32])
    sha1_hash: Mapped[str]       # SHA1 (CHAR[40])
    sha256_hash: Mapped[str]     # SHA256 (CHAR[64])

    is_backup: Mapped[bool]      # 是否已备份
    backup_time: Mapped[datetime | None]  # 备份时间

    created_at: Mapped[datetime] # 创建时间
    updated_at: Mapped[datetime] # 更新时间
```

### 2. BackupPackage - 备份压缩包表
```python
class BackupPackage(Base):
    __tablename__ = 'backup_packages'

    id: Mapped[int]              # 主键
    package_path: Mapped[str]    # 本地ZIP路径（唯一）
    baidu_pan_path: Mapped[str | None]  # 百度盘路径

    source_file_id: Mapped[int | None]  # 关联的源文件ID

    # Hash值
    md5_hash: Mapped[str]
    sha1_hash: Mapped[str]
    sha256_hash: Mapped[str]

    password: Mapped[str | None] # ZIP密码
    file_count: Mapped[int]      # 文件数
    package_size: Mapped[int]    # 压缩包大小

    status: Mapped[str]          # 状态: pending/uploading/completed/failed

    created_at: Mapped[datetime] # 创建时间
    uploaded_at: Mapped[datetime | None]  # 上传时间
```

### 3. ManualReviewItem - 人工审核表
```python
class ManualReviewItem(Base):
    __tablename__ = 'manual_review_items'

    id: Mapped[int]              # 主键
    file_path: Mapped[str]       # 文件路径（唯一）
    file_size: Mapped[int | None]  # 文件大小
    file_count: Mapped[int | None] # 文件数

    reason: Mapped[str]          # 原因: size_exceeded/overcount/empty_folder
    status: Mapped[str]          # 状态: pending/processed
    notes: Mapped[str | None]    # 备注

    created_at: Mapped[datetime] # 创建时间
    processed_at: Mapped[datetime | None]  # 处理时间
```

### 4. OperationLog - 操作日志表
```python
class OperationLog(Base):
    __tablename__ = 'operation_logs'

    id: Mapped[int]              # 主键
    operation_type: Mapped[str]  # 操作类型（索引）
    file_path: Mapped[str | None]  # 文件路径
    status: Mapped[str]          # 状态: success/failed/running
    message: Mapped[str | None]  # 消息
    duration_ms: Mapped[int | None]  # 耗时（毫秒）
    created_at: Mapped[datetime] # 创建时间
```

---

## API参考

### 常用调用示例

#### 1. 完整备份流程
```python
from config import load_config, DatabaseCredentials
from service.database_service import DatabaseService
from service.orchestrator import MainOrchestrator

# 加载配置
config = load_config('config.toml')

# 创建数据库服务
credentials = DatabaseCredentials()
db_service = DatabaseService(credentials, config.database)

# 创建协调器并运行
orchestrator = MainOrchestrator(config, credentials, config.database)
orchestrator.run()
```

#### 2. 仅计算文件Hash
```python
from service.hash_service import CalculateHashService

hashes = CalculateHashService.calculate_file_hash('/path/to/file.txt')
print(f"MD5: {hashes['md5']}")
print(f"SHA256: {hashes['sha256']}")
```

#### 3. 压缩文件
```python
from service.zip_service import ZipService

zip_path = ZipService.zip_item(
    source_item='/path/to/file',
    target_dir='/tmp/compress',
    password='my_password',
    compress_level=0
)
```

#### 4. 验证ZIP包
```python
from service.verify_service import VerifyService
from service.classify_service import FileInfo

file_info = FileInfo(source_path=Path('/path/to/file'), ...)
verify_service = VerifyService()
result = verify_service.verify_package('/path/to/file.zip', file_info)
print(f"验证通过: {result.is_valid}")
```

#### 5. 上传到百度网盘
```python
from service.upload_service import UploadService

result = UploadService().upload_file(
    file_path='/path/to/file.zip',
    chunk_size=20 * 1024 * 1024  # 20MB
)
```

---

## 调用关系图

```
                    ┌─────────────────────┐
                    │      main.py        │
                    │ run_gui() / run_cli │
                    └──────────┬──────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         MainOrchestrator                              │
├──────────────────────────────────────────────────────────────────────┤
│ run()                                                                │
│  ├─ SpaceManager.check_initial_space()                               │
│  ├─ DatabaseService.create_tables()                                  │
│  ├─ ClassifyService.scan_source_folder()                             │
│  │   └─ _classify_file() / _classify_folder()                        │
│  │       └─ _count_all_files()                                       │
│  ├─ DedupeService.compare_and_dedupe()                               │
│  │   └─ CalculateHashService.calculate_xxx_hash()                    │
│  ├─ ZipService.zip_item()                                            │
│  ├─ VerifyService.verify_package()                                   │
│  │   └─ ZipService.unzip_item()                                      │
│  ├─ QueueManager.add_tasks() / start()                               │
│  │   └─ UploadService.upload_file()                                  │
│  │       ├─ precreate()                                              │
│  │       ├─ upload()                                                 │
│  │       └─ create()                                                 │
│  └─ _send_manual_review_notification()                               │
│      └─ smtplib.SMTP_SSL                                             │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 配置文件示例 (config.toml)

```toml
[source]
path = "/path/to/source/folder"
password = ""  # 推荐从环境变量读取

[storage]
compress_dir = "/tmp/compress"
extract_dir = "/tmp/extract"
disk_limit_gb = 80

[database]
pool_size = 5
max_overflow = 10
pool_timeout = 30
pool_recycle = 3600
echo = false

[limits]
max_file_size_gb = 20
max_files_per_folder = 200

[compression]
level = 0  # 存储模式

[upload]
chunk_size_mb = 20
retry_times = 5
```

---

## 环境变量

```bash
# 数据库
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=backup_db

# 百度网盘
BAIDU_PAN_ACCESS_TOKEN=xxx
BAIDU_PAN_REFRESH_TOKEN=xxx
BAIDU_PAN_APP_KEY=xxx
BAIDU_PAN_SECRET_KEY=xxx

# 邮件通知 (可选)
SMTP_HOST=smtp.example.com
SMTP_PORT=465
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_email_password
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 0.2.0 | 2026-01-18 | 添加详细注释和API文档 |
| 0.1.0 | 2026-01-15 | 初始版本 |

---

*文档生成时间: 2026-01-18*
