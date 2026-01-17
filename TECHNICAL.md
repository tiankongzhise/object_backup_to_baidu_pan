# 技术文档

## object_backup_to_baidu_pan - 百度网盘备份系统

| 版本 | 日期 | 描述 |
|------|------|------|
| 1.2 | 2026-01-17 | 分离敏感配置到.env |
| 1.1 | 2026-01-17 | 按PRD流程细化技术文档 |
| 1.0 | 2026-01-17 | 初始技术文档 |

---

## 一、系统架构总览

### 1.1 整体处理流程

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           阶段1：文件扫描                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ClassifyService          DedupeService                                     │
│  ┌─────────────────┐     ┌──────────────────────────────────────────────┐   │
│  │ 扫描源文件夹    │ --> │ 与数据库比对                                  │   │
│  │ 获取一级子项    │     │ 计算Hash (MD5/SHA1/SHA256)                   │   │
│  │ 检查大小限制    │     │ 标记已备份文件                                │   │
│  │ 检查数量限制    │     │ 标记需要备份的文件                            │   │
│  └─────────────────┘     └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           阶段2：同步处理                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  ZipService               VerifyService                                     │
│  ┌─────────────────┐     ┌──────────────────────────────────────────────┐   │
│  │ 加密打包为ZIP   │ --> │ 解压ZIP                                      │   │
│  │ ZIP Hash计算    │     │ 计算解压文件Hash                             │   │
│  │ 记录Hash到DB    │     │ 与源文件Hash比对                             │   │
│  └─────────────────┘     └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           阶段3：异步上传                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  QueueManager             UploadService                                     │
│  ┌─────────────────┐     ┌──────────────────────────────────────────────┐   │
│  │ 上传任务入队列  │ --> │ 后台上传到百度网盘                           │   │
│  │ 后台线程处理    │     │ 回调处理                                     │   │
│  │ 失败重试        │     │ 数据库更新                                   │   │
│  │                 │     │ 删除源文件和压缩包                          │   │
│  └─────────────────┘     └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↑
                    ┌───────────────┴───────────────┐
                    │     SpaceManager (全程资源管理)   │
                    │  - 磁盘空间监控                  │
                    │  - 动态空间控制                  │
                    └───────────────────────────────┘
```

### 1.2 服务模块清单

| 阶段 | 服务模块 | 状态 | 说明 |
|------|----------|------|------|
| 1 | ClassifyService | 🔲 待实现 | 文件扫描、分类、超限检查 |
| 1 | DedupeService | 🔲 待实现 | 去重比对、Hash比较 |
| 1 | HashService | ✅ 已完成 | 文件/文件夹Hash计算 |
| 2 | ZipService | ✅ 已完成 | ZIP压缩/解压、AES加密 |
| 2 | VerifyService | 🔲 待实现 | 解压验证、Hash比对 |
| 3 | UploadService | ✅ 已完成 | 百度网盘分片上传 |
| 全程 | DatabaseService | 🔲 待实现 | 数据库ORM模型 |
| 全程 | SpaceManager | 🔲 待实现 | 磁盘空间管理 |
| 全程 | QueueManager | 🔲 待实现 | 上传队列管理 |
| 全程 | MainOrchestrator | 🔲 待实现 | 主协调器 |

---

## 二、HashService - 哈希计算服务

### 2.1 服务结构

```
service/hash_service/
├── __init__.py              # CalculateHashService 统一接口
├── core.py                  # 基础哈希计算函数
├── file_hash.py             # 文件哈希计算
└── folder_hash.py           # 文件夹哈希计算
```

### 2.2 API 参考

#### 2.2.1 CalculateHashService

统一入口类，封装文件和文件夹的哈希计算功能。

```python
from service.hash_service import CalculateHashService

# 计算文件夹哈希
CalculateHashService.calculate_folder_hash(
    folder_info: str | Path | dict,
    algorithm: list | None = None,
    display_hash_progress: bool = True
) -> dict

# 计算文件哈希
CalculateHashService.calculate_file_hash(
    file_info: str | Path | dict,
    algorithm: list | None = None
) -> dict
```

#### 2.2.2 calculate_file_hash_base

基础文件哈希计算函数。

```python
from service.hash_service.core import calculate_file_hash_base

hash_obj = calculate_file_hash_base(
    file_path: pathlib.Path | str,
    algorithm: str = 'sha256'
)
hexdigest = hash_obj.hexdigest().upper()
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| file_path | Path \| str | 必填 | 文件路径 |
| algorithm | str | 'sha256' | 算法: md5, sha1, sha256 等 |

**特性：** 大文件分块读取，每块 500MB，内存占用低

#### 2.2.3 calculate_file_hash

计算单个文件的多种哈希值。

```python
from service.hash_service import CalculateHashService

result = CalculateHashService.calculate_file_hash(
    file_info=Path('/path/to/file'),
    algorithm=['md5', 'sha1', 'sha256']
)
# 返回: {'md5': '...', 'sha1': '...', 'sha256': '...'}
```

**校验：** 检查文件大小是否超过 `ClassifyConfig.file_oversize`

#### 2.2.4 calculate_folder_hash

计算文件夹的哈希值（合并文件夹内所有文件的哈希）。

```python
result = CalculateHashService.calculate_folder_hash(
    folder_info=Path('/path/to/folder'),
    algorithm=['md5', 'sha1', 'sha256'],
    display_hash_progress=True
)
```

**校验：** 检查空文件夹、文件数限制、总大小限制

---

## 三、ZipService - ZIP 压缩/解压服务

### 3.1 服务结构

```
service/zip_service.py
```

### 3.2 API 参考

#### 3.2.1 zip_item

将文件或文件夹打包为加密 ZIP 文件。

```python
from service.zip_service import ZipService

zip_path = ZipService.zip_item(
    source_item=Path('/path/to/source'),
    target_dir=Path('/path/to/compress'),
    password='your_password',
    compress_level=6
)
```

**路径生成规则：**
```
{target_dir}/YYYYMMDD/{源文件夹名}/解压密码_{password}/{文件名}.zip
```

**特性：**
- AES-256 加密
- 文件按路径排序添加
- 压缩失败自动清理

#### 3.2.2 unzip_item

解压 ZIP 文件到目标目录。

```python
extract_path = ZipService.unzip_item(
    zip_path=Path('/path/to/file.zip'),
    target_dir=Path('/path/to/extract'),
    password='your_password'
)
# 返回解压后的根目录路径
```

---

## 四、待实现服务模块

### 4.1 ClassifyService - 分类服务（阶段1）

**功能职责：**
- 扫描源文件夹，获取一级子文件和文件夹列表
- 检查文件/文件夹大小是否超过限制 (>20GB)
- 检查文件夹包含文件数是否超过限制 (>200)
- 标记需要人工处理的文件

**API 设计：**

```python
from service.classify_service import ClassifyService

classify_result = ClassifyService.scan_source_folder(
    source_path: Path,
    config: ClassifyConfig
)
# 返回: list[FileInfo | FolderInfo | ManualReviewItem]
```

**FileInfo 结构：**
```python
@dataclass
class FileInfo:
    source_path: Path
    file_name: str
    file_size: int
    classify_result: str = 'normal_file'
```

**FolderInfo 结构：**
```python
@dataclass
class FolderInfo:
    source_path: Path
    folder_name: str
    file_count: int  # 直接子文件数
    total_size: int
    classify_result: str = 'normal_folder'
```

**ManualReviewItem 结构：**
```python
@dataclass
class ManualReviewItem:
    source_path: Path
    reason: str  # 'size_exceeded' | 'overcount'
    file_size: int | None
    file_count: int | None
```

---

### 4.2 DedupeService - 去重服务（阶段1）

**功能职责：**
- 与数据库比对文件 Hash
- 识别已备份的文件
- 标记需要备份的文件
- 清理已备份的源文件

**API 设计：**

```python
from service.dedupe_service import DedupeService

dedupe_result = DedupeService.compare_and_dedupe(
    items: list[FileInfo | FolderInfo],
    db_session: Session
)
# 返回: DedupeResult
```

**DedupeResult 结构：**
```python
@dataclass
class DedupeResult:
    to_backup: list[FileInfo | FolderInfo]  # 需要备份
    already_backup: list[FileInfo | FolderInfo]  # 已备份，直接删除
    not_found_in_db: list[FileInfo | FolderInfo]  # 数据库无记录
```

**去重逻辑：**
```python
def _check_file_backup_status(file_info: FileInfo, session: Session) -> bool:
    """检查文件是否已备份"""
    # 查询数据库中是否存在相同 Hash 的记录
    hashes = CalculateHashService.calculate_file_hash(file_info)
    existing = session.query(SourceFile).filter(
        and_(
            SourceFile.md5_hash == hashes['md5'],
            SourceFile.sha1_hash == hashes['sha1'],
            SourceFile.sha256_hash == hashes['sha256']
        )
    ).first()
    return existing is not None
```

---

### 4.3 VerifyService - 验证服务（阶段2）

**功能职责：**
- 解压 ZIP 压缩包
- 计算解压后文件/文件夹的 Hash
- 与源文件 Hash 进行比对
- 验证失败触发重新压缩

**API 设计：**

```python
from service.verify_service import VerifyService

verify_result = VerifyService.verify_package(
    zip_path: Path,
    source_info: FileInfo | FolderInfo,
    password: str | None = None
) -> VerifyResult
```

**VerifyResult 结构：**
```python
@dataclass
class VerifyResult:
    is_valid: bool
    extracted_path: Path | None
    extracted_hashes: dict | None
    source_hashes: dict | None
    error_message: str | None
```

**验证流程：**
```python
def verify_package(zip_path: Path, source_info, password: str | None) -> VerifyResult:
    # 1. 解压ZIP
    extracted_path = ZipService.unzip_item(zip_path, password=password)

    # 2. 计算解压后Hash
    if source_info.is_file():
        extracted_hashes = CalculateHashService.calculate_file_hash(extracted_path)
    else:
        extracted_hashes = CalculateHashService.calculate_folder_hash(extracted_path)

    # 3. 与源文件Hash比对
    source_hashes = source_info.hashes  # 从源信息获取

    # 4. 比对结果
    is_valid = all(
        extracted_hashes[alg] == source_hashes[alg]
        for alg in HashConfig.required_hash_algorithms
    )

    return VerifyResult(is_valid, extracted_path, extracted_hashes, source_hashes, None)
```

---

### 4.4 DatabaseService - 数据库服务（全程）

**数据库模型：**

```python
# models/source_file.py
class SourceFile(Base):
    __tablename__ = 'source_files'

    id = Column(BigInteger, primary_key=True)
    file_path = Column(String(1024), unique=True)
    file_name = Column(String(255))
    file_size = Column(BigInteger)
    md5_hash = Column(CHAR(32), index=True)
    sha1_hash = Column(CHAR(40), index=True)
    sha256_hash = Column(CHAR(64), index=True)
    is_backup = Column(Boolean, default=False)
    backup_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

# models/backup_package.py
class BackupPackage(Base):
    __tablename__ = 'backup_packages'

    id = Column(BigInteger, primary_key=True)
    package_path = Column(String(1024))
    baidu_pan_path = Column(String(1024))
    source_file_id = Column(BigInteger, ForeignKey('source_files.id'))
    md5_hash = Column(CHAR(32))
    sha1_hash = Column(CHAR(40))
    sha256_hash = Column(CHAR(64))
    password = Column(String(64))
    file_count = Column(Integer)
    package_size = Column(BigInteger)
    status = Column(String(20))  # pending/uploading/completed/failed
    created_at = Column(DateTime, default=datetime.utcnow)
    uploaded_at = Column(DateTime)

# models/manual_review_item.py
class ManualReviewItem(Base):
    __tablename__ = 'manual_review_items'

    id = Column(BigInteger, primary_key=True)
    file_path = Column(String(1024))
    file_size = Column(BigInteger)
    file_count = Column(Integer)
    reason = Column(String(100))  # size_exceeded/overcount
    status = Column(String(20), default='pending')
    created_at = Column(DateTime, default=datetime.utcnow)

# models/operation_log.py
class OperationLog(Base):
    __tablename__ = 'operation_logs'

    id = Column(BigInteger, primary_key=True)
    operation_type = Column(String(50))
    file_path = Column(String(1024))
    status = Column(String(20))
    message = Column(Text)
    duration_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

### 4.5 SpaceManager - 空间管理器（全程）

**功能职责：**
- 监控磁盘空间使用量
- 计算下一文件所需空间
- 动态控制处理流程
- 等待空间释放

**API 设计：**

```python
from service.space_manager import SpaceManager

with SpaceManager.reserve_space(required_bytes):
    process_file(file_info)
```

**各阶段空间占用：**

| 阶段 | 操作 | 额外空间 |
|------|------|----------|
| 1 | Hash计算 | 0 |
| 2 | 压缩处理 | 压缩包大小 |
| 3 | 解压验证 | 压缩包 + 解压文件 |
| 4 | 验证完成 | 压缩包大小 |
| 5 | 上传完成 | 0 |

---

### 4.6 QueueManager - 队列管理器（阶段3）

**功能职责：**
- 管理上传任务队列
- 后台线程处理上传
- 失败重试机制
- 断点续传支持

**API 设计：**

```python
from service.queue_manager import QueueManager

# 添加任务到队列
QueueManager.add_task(package_info)

# 启动队列处理
QueueManager.start()

# 停止队列处理
QueueManager.stop()
```

**处理流程：**
```python
class QueueManager:
    def _process_queue(self):
        while self._running:
            if self.upload_queue.empty():
                sleep(1)
                continue

            package = self.upload_queue.get()
            try:
                result = UploadService.upload_file(package.zip_path)
                if result.success:
                    self._on_upload_success(package, result)
                else:
                    self._on_upload_failed(package, result)
            except Exception as e:
                self._on_upload_error(package, e)
```

---

### 4.7 MainOrchestrator - 主协调器

**功能职责：**
- 加载配置
- 初始化各服务
- 协调处理流程
- 错误处理和恢复

**API 设计：**

```python
from service.orchestrator import MainOrchestrator

orchestrator = MainOrchestrator(config_path='config.toml')
orchestrator.run()
```

**主流程：**

```python
def run(self):
    # 1. 初始化
    self._init_services()
    SpaceManager.check_disk_space()

    # 2. 扫描源文件夹
    items = ClassifyService.scan_source_folder(self.config.source_path)

    # 3. 去重比对
    to_backup = DedupeService.compare_and_dedupe(items, self.db_session)

    # 4. 同步处理（压缩+验证）
    for item in to_backup:
        with SpaceManager.reserve_space(calculate_required_space(item)):
            # 压缩
            zip_path = ZipService.zip_item(
                item.source_path,
                self.config.compress_dir,
                password=self.config.default_password
            )

            # 记录Hash到数据库
            zip_hashes = CalculateHashService.calculate_file_hash(zip_path)
            self._save_package_info(item, zip_path, zip_hashes)

            # 验证
            if not VerifyService.verify_package(zip_path, item):
                # 验证失败，重新压缩
                continue

            # 5. 加入上传队列
            QueueManager.add_task({
                'zip_path': zip_path,
                'item': item
            })

    # 6. 启动上传队列
    QueueManager.start()
```

---

## 五、配置模块

### 5.1 配置分离原则

| 配置类型 | 存储位置 | 说明 |
|----------|----------|------|
| 敏感信息 | `.env` 文件 | 数据库密码、百度Token、邮箱密码等 |
| 应用配置 | `config.toml` | 路径、限制参数、连接池配置等 |

### 5.2 非敏感配置 (config.toml)

```toml
[source]
path = "/path/to/source"
password = ""

[storage]
compress_dir = "/path/to/compress"
extract_dir = "/path/to/extract"
disk_limit_gb = 80

[limits]
max_file_size_gb = 20
max_files_per_folder = 200

[compression]
level = 0

[upload]
chunk_size_mb = 20
retry_times = 5

[database]
pool_size = 5
max_overflow = 10
pool_timeout = 30
pool_recycle = 3600
pool_pre_ping = true
echo = false
```

### 5.3 敏感配置 (.env)

```env
# 数据库连接
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=backup_db

# 百度网盘
BAIDU_PAN_ACCESS_TOKEN=your_token
BAIDU_PAN_REFRESH_TOKEN=your_refresh_token
BAIDU_PAN_APP_KEY=your_app_key
BAIDU_PAN_SECRET_KEY=your_secret_key
```

### 5.4 配置类定义

```python
# config.py

from pathlib import Path
from dataclasses import dataclass, field
import os

@dataclass
class HashConfig:
    required_hash_algorithms: list[str] = field(default_factory=lambda: ['md5', 'sha1', 'sha256'])

@dataclass
class ClassifyConfig:
    file_oversize: int = 20 * 1024**3
    folder_oversize: int = 20 * 1024**3
    overcount: int = 200
    unzip_folder: Path = Path('/tmp/unzip')

@dataclass
class ZipConfig:
    compress_level: int = 0
    default_password: str = 'backup123'

@dataclass
class DatabasePoolConfig:
    """数据库连接池配置（非敏感）"""
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True
    echo: bool = False

@dataclass
class UploadConfig:
    chunk_size_mb: int = 20
    retry_times: int = 5
    baidu_pan_dir: str = '/item_backup'

@dataclass
class SpaceConfig:
    disk_limit_gb: int = 80

@dataclass
class SourceConfig:
    path: Path = Path('')
    password: str = ''

@dataclass
class StorageConfig:
    compress_dir: Path = Path('/tmp/compress')
    extract_dir: Path = Path('/tmp/extract')

@dataclass
class Config:
    """主配置类（非敏感配置）"""
    source: SourceConfig = field(default_factory=SourceConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    database: DatabasePoolConfig = field(default_factory=DatabasePoolConfig)
    hash: HashConfig = field(default_factory=HashConfig)
    classify: ClassifyConfig = field(default_factory=ClassifyConfig)
    zip: ZipConfig = field(default_factory=ZipConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    space: SpaceConfig = field(default_factory=SpaceConfig)

# 凭证类（从环境变量读取）
class DatabaseCredentials:
    """数据库连接凭证（从环境变量读取）"""
    def __init__(self):
        self.host = os.environ.get('MYSQL_HOST', 'localhost')
        self.port = int(os.environ.get('MYSQL_PORT', 3306))
        self.username = os.environ.get('MYSQL_USER', 'root')
        self.password = os.environ.get('MYSQL_PASSWORD', '')
        self.name = os.environ.get('MYSQL_DATABASE', 'backup_db')

    @property
    def url(self) -> str:
        return f"mysql+pymysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.name}"

class BaiduPanCredentials:
    def __init__(self):
        self.access_token = os.environ.get('BAIDU_PAN_ACCESS_TOKEN', '')
        self.refresh_token = os.environ.get('BAIDU_PAN_REFRESH_TOKEN', '')
        self.app_key = os.environ.get('BAIDU_PAN_APP_KEY', '')
        self.secret_key = os.environ.get('BAIDU_PAN_SECRET_KEY', '')
```

---

## 六、目录结构

```
src/object_backup_to_baidu_pan/
├── __init__.py
├── config.py                  # 配置模块 (待实现)
├── main.py                    # 主入口 (待实现)
├── models/                    # 数据库模型 (待实现)
│   ├── __init__.py
│   ├── source_file.py
│   ├── backup_package.py
│   ├── manual_review_item.py
│   └── operation_log.py
└── service/
    ├── __init__.py
    ├── hash_service/          # ✅ 已完成
    │   ├── __init__.py
    │   ├── core.py
    │   ├── file_hash.py
    │   └── folder_hash.py
    ├── classify_service/      # 🔲 待实现
    │   └── __init__.py
    ├── dedupe_service/        # 🔲 待实现
    │   └── __init__.py
    ├── zip_service.py         # ✅ 已完成
    ├── verify_service/        # 🔲 待实现
    │   └── __init__.py
    ├── upload_service/        # ✅ 已完成
    │   ├── __init__.py
    │   ├── upload_service.py
    │   ├── utils.py
    │   └── openapi_client/
    ├── queue_manager/         # 🔲 待实现
    │   └── __init__.py
    ├── space_manager/         # 🔲 待实现
    │   └── __init__.py
    └── orchestrator/          # 🔲 待实现
        └── __init__.py
```

---

## 七、状态速查表

| 模块 | 状态 | PRD阶段 | 主要职责 |
|------|------|---------|----------|
| ClassifyService | 🔲 待实现 | 1-扫描 | 扫描、检查限制 |
| DedupeService | 🔲 待实现 | 1-比对 | 去重、Hash比对 |
| HashService | ✅ 已完成 | 1-计算 | 文件/文件夹Hash |
| ZipService | ✅ 已完成 | 2-压缩 | ZIP打包、AES加密 |
| VerifyService | 🔲 待实现 | 2-验证 | 解压验证 |
| UploadService | ✅ 已完成 | 3-上传 | 百度网盘上传 |
| DatabaseService | 🔲 待实现 | 全程 | 数据持久化 |
| SpaceManager | 🔲 待实现 | 全程 | 空间管理 |
| QueueManager | 🔲 待实现 | 3-队列 | 队列管理 |
| MainOrchestrator | 🔲 待实现 | 全程 | 流程协调 |

---

## 八、开发顺序建议

1. **第一优先级**（核心依赖）
   - DatabaseService（其他服务依赖）
   - Config（配置模块）

2. **第二优先级**（阶段1）
   - ClassifyService
   - DedupeService

3. **第三优先级**（阶段2）
   - VerifyService

4. **第四优先级**（阶段3 + 资源管理）
   - SpaceManager
   - QueueManager

5. **最后**（集成）
   - MainOrchestrator
