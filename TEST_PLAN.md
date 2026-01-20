# 测试用例规划文档

## 项目概述
**object_backup_to_baidu_pan** - 百度网盘备份系统，v0.1.0

本文档规划了实现100%代码覆盖率所需的测试用例，包括单元测试和集成测试。

---

## 测试框架
```bash
# 推荐测试框架
uv add pytest pytest-cov pytest-mock pytest-asyncio

# 运行测试
uv run pytest --cov=src --cov-report=html --cov-report=term-missing
```

---

## 模块测试规划

### 1. config.py - 配置模块

#### 1.1 配置类测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CONFIG-001 | 默认HashConfig | 无 | required_algorithms = ['md5', 'sha1', 'sha256'] |
| CONFIG-002 | 自定义HashConfig | ['md5'] | 只使用md5 |
| CONFIG-003 | 默认ClassifyConfig | 无 | 20GB大小限制，200文件数限制 |
| CONFIG-004 | 自定义ClassifyConfig | file_oversize=1GB | 限制正确生效 |
| CONFIG-005 | 默认ZipConfig | 无 | AES-256, 压缩级别0, 默认密码 |
| CONFIG-006 | ZipConfig盐值验证 | 无 | 8/12/16字节盐值正确 |
| CONFIG-007 | 默认DatabasePoolConfig | 无 | pool_size=5, max_overflow=10 |
| CONFIG-008 | DatabasePoolConfig.get_url | 完整参数 | 生成正确mysql URL |
| CONFIG-009 | DatabasePoolConfig.get_url | 特殊字符密码 | URL编码正确 |
| CONFIG-010 | 默认UploadConfig | 无 | chunk_size=20MB, retry=5次 |
| CONFIG-011 | 默认SpaceConfig | 无 | disk_limit=80GB |
| CONFIG-012 | 默认SourceConfig | 无 | 空paths, 空password |
| CONFIG-013 | 默认StorageConfig | 无 | 临时目录路径正确 |
| CONFIG-014 | 默认Config | 无 | 所有子配置正确初始化 |

#### 1.2 Config.from_dict测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CONFIG-015 | 解析完整配置 | 完整dict | 所有配置正确解析 |
| CONFIG-016 | 解析paths字符串 | "path": "/test" | 转换为Path对象 |
| CONFIG-017 | 解析paths列表 | "paths": ["/a", "/b"] | 列表正确解析 |
| CONFIG-018 | 解析单个路径 | "path": "/test" | 单路径模式 |
| CONFIG-019 | 解析空配置 | {} | 使用默认值 |
| CONFIG-020 | 解析limits配置 | max_file_size_gb=10 | 文件大小限制=10GB |
| CONFIG-021 | 解析compression配置 | level=9 | 压缩级别=9 |
| CONFIG-022 | 解析upload配置 | chunk_size_mb=50 | 分片大小=50MB |
| CONFIG-023 | 解析storage配置 | disk_limit_gb=100 | 磁盘限制=100GB |

#### 1.3 环境变量函数测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CONFIG-024 | get_env存在 | KEY=value | 返回value |
| CONFIG-025 | get_env不存在 | KEY不存在, default=abc | 返回abc |
| CONFIG-026 | get_env_int有效 | KEY=123 | 返回int 123 |
| CONFIG-027 | get_env_int无效 | KEY=abc, default=0 | 返回0 |
| CONFIG-028 | get_env_bool true | KEY=true | 返回True |
| CONFIG-029 | get_env_bool 1 | KEY=1 | 返回True |
| CONFIG-030 | get_env_bool false | KEY=false | 返回False |
| CONFIG-031 | get_env_bool 0 | KEY=0 | 返回False |
| CONFIG-032 | get_env_bool无效 | KEY=invalid, default=False | 返回False |
| CONFIG-033 | get_hostname成功 | 无 | 返回主机名 |
| CONFIG-034 | get_hostname失败 | socket异常 | 返回'localhost' |

#### 1.4 工具函数测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CONFIG-035 | is_archive_file ZIP | "file.zip" | True |
| CONFIG-036 | is_archive_file 7Z | "file.7z" | True |
| CONFIG-037 | is_archive_file TAR | "file.tar" | True |
| CONFIG-038 | is_archive_file 普通文件 | "file.txt" | False |
| CONFIG-039 | is_archive_file APK | "app.apk" | True |
| CONFIG-040 | is_archive_file 大小写 | ".ZIP" | True (不区分大小写) |
| CONFIG-041 | ARCHIVE_EXTENSIONS完整 | 无 | 包含所有标准压缩扩展名 |

#### 1.5 凭证类测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CONFIG-042 | DatabaseCredentials默认 | 环境变量空 | 使用默认值 |
| CONFIG-043 | DatabaseCredentials URL | 完整环境变量 | 正确URL格式 |
| CONFIG-044 | BaiduPanCredentials默认 | 环境变量空 | 属性为空字符串 |
| CONFIG-045 | SMTPCredentials默认 | 环境变量空 | 使用默认配置 |
| CONFIG-046 | SMTPCredentials多邮箱 | ADMIN_EMAILS="a@b.com,c@d.com" | 正确解析列表 |
| CONFIG-047 | SMTPCredentials备用变量名 | SMTP_SERVER而非SMTP_HOST | 兼容备用名称 |

---

### 2. hash_service/core.py - Hash计算核心

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CORE-001 | 计算文件MD5 | 存在的文件, 'md5' | 返回hashlib.Hash对象 |
| CORE-002 | 计算文件SHA256 | 存在的文件, 'sha256' | 返回正确的Hash值 |
| CORE-003 | 计算不存在文件 | 不存在路径 | FileNotFoundError |
| CORE-004 | 空文件 | 0字节文件 | 返回正确空内容Hash |
| CORE-005 | 大文件(>500MB) | 大文件路径 | 正确分块读取 |
| CORE-006 | 无效算法 | 'invalid_alg' | ValueError |
| CORE-007 | 二进制模式读取 | 二进制文件 | 正确处理二进制数据 |

---

### 3. hash_service/file_hash.py - 文件Hash计算

#### 3.1 _is_oversize测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FILEHASH-001 | 文件未超限 | Path(小文件) | False |
| FILEHASH-002 | 文件超限 | Path(>20GB文件) | True |
| FILEHASH-003 | 字典-oversize | {'classify_result': 'oversize_file'} | True |
| FILEHASH-004 | 字典-normal | {'classify_result': 'normal_file'} | False |
| FILEHASH-005 | 字符串路径 | "/path/to/file" | 正确解析并检查 |

#### 3.2 _is_file测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FILEHASH-006 | Path-文件 | Path(存在的文件) | True |
| FILEHASH-007 | Path-目录 | Path(存在的目录) | False |
| FILEHASH-008 | Path-不存在 | Path(不存在) | False |
| FILEHASH-009 | dict | {'source_path': '/file'} | True |
| FILEHASH-010 | str | "/file" | True |
| FILEHASH-011 | 非法类型 | 123 | ValueError |

#### 3.3 _verify_file_for_hashing测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FILEHASH-012 | 有效文件 | 有效小文件Path | 返回Path对象 |
| FILEHASH-013 | 超限文件 | >20GB文件Path | ValueError |
| FILEHASH-014 | 不存在文件 | 不存在Path | ValueError |
| FILEHASH-015 | 字典形式 | 包含source_path的dict | 返回Path |

#### 3.4 calculate_file_hash测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FILEHASH-016 | 单算法 | 文件Path, ['md5'] | 返回只包含md5的dict |
| FILEHASH-017 | 多算法 | 文件Path, ['md5', 'sha1'] | 返回包含两者的dict |
| FILEHASH-018 | 默认算法 | 无algorithm参数 | 使用HashConfig配置 |
| FILEHASH-019 | 文件不存在 | 不存在路径 | FileNotFoundError |
| FILEHASH-020 | Hash值格式 | 任意文件 | 值都是大写十六进制 |
| FILEHASH-021 | 只读文件 | 无写权限文件 | 正常读取并计算 |

---

### 4. hash_service/folder_hash.py - 文件夹Hash计算

#### 4.1 _is_empty_folder测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FOLDERHASH-001 | 空目录 | Path(空目录) | True |
| FILEHASH-002 | 非空目录 | Path(非空目录) | False |
| FOLDERHASH-003 | 字典-空 | {'classify_result': 'empty_folder'} | True |
| FOLDERHASH-004 | 字典-非空 | {'classify_result': 'normal_folder'} | False |
| FOLDERHASH-005 | 非法类型 | 123 | TypeError |

#### 4.2 _is_overcount测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FOLDERHASH-006 | 文件数<200 | [1-200个Path] | False |
| FOLDERHASH-007 | 文件数>200 | [>200个Path] | True |
| FOLDERHASH-008 | 字典-overcount | {'classify_result': 'overcount'} | True |
| FOLDERHASH-009 | 字典-normal | {'classify_result': 'normal'} | False |
| FOLDERHASH-010 | 非法类型 | Path | TypeError |

#### 4.3 _is_oversize测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FOLDERHASH-011 | 大小<20GB | 文件列表, 总大小<20GB | False |
| FOLDERHASH-012 | 大小>20GB | 文件列表, 总大小>20GB | True |
| FOLDERHASH-013 | 字典-oversize | {'classify_result': 'oversize'} | True |
| FOLDERHASH-014 | 字典-normal | {'classify_result': 'normal'} | False |

#### 4.4 _verify_folder_for_hashing测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FOLDERHASH-015 | 有效目录 | 正常目录Path | 返回排序后的文件列表 |
| FOLDERHASH-016 | 空目录 | 空目录Path | ValueError |
| FOLDERHASH-017 | 文件数超限 | >200文件目录 | ValueError |
| FOLDERHASH-018 | 大小超限 | >20GB目录 | ValueError |
| FOLDERHASH-019 | 字典形式-空 | {'classify_result': 'empty_folder'} | ValueError |
| FOLDERHASH-020 | 字典形式-正常 | 包含source_path的dict | 返回文件列表 |
| FOLDERHASH-021 | 文件排序 | 多文件目录 | 按路径排序 |

#### 4.5 _display_hash_progress测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FOLDERHASH-022 | 显示进度条 | 文件列表, 'sha256' | 返回大写Hash值 |
| FOLDERHASH-023 | 空列表 | [] | 返回空内容Hash |
| FOLDERHASH-024 | 单文件 | [一个文件] | 正确计算 |

#### 4.6 _not_display_hash_progress测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FOLDERHASH-025 | 不显示进度 | 文件列表, 'md5' | 返回Hash值 |
| FOLDERHASH-026 | 大文件列表 | 多文件 | 正确累加各文件Hash |

#### 4.7 calculate_folder_hash测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| FOLDERHASH-027 | 默认算法 | 目录Path | 使用默认算法列表 |
| FILEHASH-028 | 自定义算法 | 目录Path, ['sha256'] | 只返回sha256 |
| FOLDERHASH-029 | 显示进度 | display_hash_progress=True | 进度条正常显示 |
| FOLDERHASH-030 | 隐藏进度 | display_hash_progress=False | 无进度条输出 |
| FOLDERHASH-031 | 目录不存在 | 不存在Path | FileNotFoundError |
| FOLDERHASH-032 | Hash一致性 | 同一目录两次调用 | Hash值相同 |
| FOLDERHASH-033 | 跨平台排序 | 不同操作系统 | 排序一致 |

---

### 5. hash_service/__init__.py - Hash服务统一入口

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| HASH-001 | calculate_file_hash | 文件Path | 正确调用file_hash函数 |
| HASH-002 | calculate_folder_hash | 目录Path | 正确调用folder_hash函数 |
| HASH-003 | 异常传播 | file_hash抛异常 | 异常正确传播 |
| HASH-004 | 异常传播 | folder_hash抛异常 | 异常正确传播 |

---

### 6. classify_service.py - 分类服务

#### 6.1 枚举测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-001 | ItemType.FILE | 无 | 值="file" |
| CLASS-002 | ItemType.FOLDER | 无 | 值="folder" |
| CLASS-003 | ClassifyResult枚举值 | 无 | 6种分类结果 |

#### 6.2 FileInfo测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-004 | 创建FileInfo | Path, name, size | 对象正确创建 |
| CLASS-005 | FileInfo字符串path | "path" | 自动转换为Path |
| CLASS-006 | FileInfo.item_type | FileInfo对象 | ItemType.FILE |
| CLASS-007 | FileInfo默认分类 | 无classify_result | ClassifyResult.NORMAL_FILE |

#### 6.3 FolderInfo测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-008 | 创建FolderInfo | Path, name, count, size | 对象正确创建 |
| CLASS-009 | FolderInfo字符串path | "path" | 自动转换为Path |
| CLASS-010 | FolderInfo.item_type | FolderInfo对象 | ItemType.FOLDER |
| CLASS-011 | FolderInfo默认分类 | 无classify_result | ClassifyResult.NORMAL_FOLDER |

#### 6.4 ManualReviewItem测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-012 | 创建ManualReviewItem | Path, reason | 对象正确创建 |
| CLASS-013 | OVERCOUNT reason自动设置 | reason不传 | 自动设为"overcount" |
| CLASS-014 | 其他reason自动设置 | reason不传, 非OVERCOUNT | 自动设为"size_exceeded" |
| CLASS-015 | 字符串path转换 | "path" | 自动转换为Path |

#### 6.5 ClassifyService测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-016 | 默认配置 | 无config | 使用ClassifyConfig默认 |
| CLASS-017 | 自定义配置 | ClassifyConfig(file_oversize=1GB) | 限制生效 |

#### 6.6 scan_source_folder测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-018 | 目录不存在 | 不存在路径 | FileNotFoundError |
| CLASS-019 | 路径是文件 | 文件路径 | NotADirectoryError |
| CLASS-020 | 空目录 | 空目录 | 返回空列表 |
| CLASS-021 | 单文件 | 包含一个文件的目录 | 返回FileInfo列表 |
| CLASS-022 | 多文件 | 包含多个文件的目录 | 返回多个FileInfo |
| CLASS-023 | 超大文件 | >20GB文件 | 返回ManualReviewItem |
| CLASS-024 | 子目录 | 包含子目录的目录 | 递归统计后分类 |
| CLASS-025 | 超文件数 | >200文件的目录 | 返回ManualReviewItem |
| CLASS-026 | 空子目录 | 目录中包含空文件夹 | 返回ManualReviewItem |
| CLASS-027 | 混合结果 | 目录含不同类型子项 | 混合结果列表 |
| CLASS-028 | 排序结果 | 多子项 | 按名称排序 |
| CLASS-029 | 分类异常处理 | 某子项分类出错 | 降级为ManualReviewItem |

#### 6.7 _classify_file测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-030 | 正常文件 | <20GB文件Path | FileInfo, NORMAL_FILE |
| CLASS-031 | 超大文件 | >20GB文件Path | ManualReviewItem, OVERSIZE_FILE |
| CLASS-032 | 文件不存在 | 不存在Path | 依赖stat调用, 可能OSError |

#### 6.8 _count_all_files测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-033 | 空目录 | 空目录Path | (0, 0) |
| CLASS-034 | 单文件 | 单文件目录 | (1, 文件大小) |
| CLASS-035 | 多文件 | 多文件目录 | 正确统计数量和大小 |
| CLASS-036 | 嵌套目录 | 嵌套目录 | 递归统计所有文件 |
| CLASS-037 | 访问失败 | 无权限文件 | 跳过该文件继续统计 |

#### 6.9 _classify_folder测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| CLASS-038 | 空目录 | 空目录Path | ManualReviewItem, EMPTY_FOLDER |
| CLASS-039 | 超文件数 | >200文件目录 | ManualReviewItem, OVERCOUNT |
| CLASS-040 | 超大小 | >20GB目录 | ManualReviewItem, OVERSIZE_FOLDER |
| CLASS-041 | 正常目录 | 正常目录Path | FolderInfo, NORMAL_FOLDER |

---

### 7. zip_service.py - ZIP服务

#### 7.1 辅助函数测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ZIP-001 | _add_self_salt | AESZipEncrypter实例 | salt正确设置 |
| ZIP-002 | _add_file_to_zip | 有效zipf, file, arcname | 文件添加到ZIP |
| ZIP-003 | _add_directory_to_zip 空目录 | 空目录 | 不添加任何文件 |
| ZIP-004 | _add_directory_to_zip 单文件 | 单文件目录 | 添加文件 |
| ZIP-005 | _add_directory_to_zip 多文件 | 多文件目录 | 按路径排序添加 |
| ZIP-006 | _add_directory_to_zip 嵌套 | 嵌套目录 | 保持目录结构 |

#### 7.2 ZipService.zip_item测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ZIP-007 | 源不存在 | 不存在路径 | FileNotFoundError |
| ZIP-008 | 目标是文件 | target_dir是文件 | IsADirectoryError |
| ZIP-009 | 压缩级别无效 | compress_level="high" | TypeError |
| ZIP-010 | 压缩级别边界-0 | compress_level=0 | 正常处理 |
| ZIP-011 | 压缩级别边界-9 | compress_level=9 | 正常处理 |
| ZIP-012 | 压缩级别越界<0 | compress_level=-1 | 修正为0 |
| ZIP-013 | 压缩级别越界>9 | compress_level=10 | 修正为9 |
| ZIP-014 | 单文件无密码 | 文件Path, 无password | 生成无密码ZIP |
| ZIP-015 | 单文件有密码 | 文件Path, password="test" | 生成加密ZIP |
| ZIP-016 | 目录无密码 | 目录Path, 无password | 生成无密码ZIP |
| ZIP-017 | 目录有密码 | 目录Path, password="test" | 生成加密ZIP |
| ZIP-018 | 密码含特殊字符 | password="密码!@#" | 正常处理UTF-8 |
| ZIP-019 | 目标路径创建 | 不存在的target_dir | 自动创建目录 |
| ZIP-020 | ZIP内容正确 | 生成后解压验证 | 内容一致 |
| ZIP-021 | ZIP加密方法 | 加密ZIP | 使用WZ_AES加密 |
| ZIP-022 | 压缩级别效果 | compress_level不同 | ZIP内部compression_level正确 |
| ZIP-023 | 压缩失败清理 | 压缩过程中断 | 删除不完整ZIP |
| ZIP-024 | 路径格式-带密码 | 有密码 | 路径含"解压密码_xxx" |
| ZIP-025 | 路径格式-无密码 | 无密码 | 路径不含密码部分 |
| ZIP-026 | 路径格式-日期 | 无 | 正确格式YYYYMMDD |
| ZIP-027 | 清理不完整文件 | 写入失败 | 不完整文件被删除 |
| ZIP-028 | 不支持类型 | 符号链接 | ValueError |

#### 7.3 ZipService.unzip_item测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ZIP-029 | ZIP不存在 | 不存在路径 | FileNotFoundError |
| ZIP-030 | 默认目标目录 | target_dir=None | 使用ZipConfig.unzip_folder |
| ZIP-031 | 指定目标目录 | target_dir=/custom | 解压到指定目录 |
| ZIP-032 | 无密码ZIP | password=None | 正常解压 |
| ZIP-033 | 正确密码 | 正确password | 正常解压 |
| ZIP-034 | 错误密码 | 错误password | RuntimeError |
| ZIP-035 | 目标目录不存在 | 不存在target_dir | 自动创建 |
| ZIP-036 | 解压路径格式 | 标准路径格式 | 按预期路径解压 |
| ZIP-037 | 无日期路径 | 路径不含YYYYMMDD | 使用当前日期 |
| ZIP-038 | 解压内容正确 | 加密ZIP | 内容与压缩前一致 |
| ZIP-039 | 解压失败清理 | 解压出错 | 清理目标目录 |
| ZIP-040 | 多层嵌套目录 | ZIP含嵌套目录 | 保持结构 |
| ZIP-041 | 空ZIP | 空ZIP文件 | 创建空目录 |
| ZIP-042 | 大文件ZIP | 大ZIP文件 | 正常解压 |
| ZIP-043 | 目标已存在 | 解压到已有目录 | 正常覆盖/追加 |

---

### 8. verify_service.py - 验证服务

#### 8.1 VerifyResult测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| VERIFY-001 | 创建VerifyResult | is_valid=True | __bool__返回True |
| VERIFY-002 | 创建VerifyResult | is_valid=False | __bool__返回False |
| VERIFY-003 | 完整结果 | 所有字段 | 字段正确存储 |

#### 8.2 VerifyService测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| VERIFY-004 | 默认配置 | 无config | 使用默认配置 |
| VERIFY-005 | 自定义配置 | 自定义HashConfig | 配置生效 |

#### 8.3 verify_package测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| VERIFY-006 | 验证成功 | 正确ZIP, FileInfo | is_valid=True |
| VERIFY-007 | 验证成功 | 正确ZIP, FolderInfo | is_valid=True |
| VERIFY-008 | 验证失败-ZIP损坏 | 损坏ZIP | is_valid=False |
| VERIFY-009 | 验证失败-密码错误 | 错误密码 | is_valid=False |
| VERIFY-010 | 验证失败-Hash不匹配 | 修改后的文件 | is_valid=False |
| VERIFY-011 | 传入source_hashes | 提供已计算的hash | 跳过重新计算 |
| VERIFY-012 | 未传入source_hashes | 不提供hash | 重新计算 |
| VERIFY-013 | 解压目录清理成功 | 验证成功 | 清理解压目录 |
| VERIFY-014 | 解压目录清理失败 | 验证失败 | 清理解压目录 |
| VERIFY-015 | 解压目录不存在 | 清理时目录不存在 | 不报错 |
| VERIFY-016 | 解压的是文件 | ZIP含单文件 | 正确处理 |
| VERIFY-017 | 解压的是目录 | ZIP含目录 | 正确处理 |

#### 8.4 _compare_hashes测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| VERIFY-018 | 完全匹配 | 完全相同的两组hash | True |
| VERIFY-019 | 部分匹配 | 一个算法不匹配 | False |
| VERIFY-020 | 缺失算法 | 提取的hash缺少某算法 | False |
| VERIFY-021 | 多算法比较 | 3种算法 | 全部比较 |

#### 8.5 cleanup_extracted测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| VERIFY-022 | 清理目录 | 存在的目录 | 目录被删除 |
| VERIFY-023 | 清理文件 | 存在的文件 | 文件被删除 |
| VERIFY-024 | 清理不存在 | 不存在路径 | 不报错 |
| VERIFY-025 | 清理混合类型 | 符号链接等 | RuntimeError |

---

### 9. space_manager.py - 空间管理器

#### 9.1 SpaceInfo测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-001 | 创建SpaceInfo | 有效参数 | 对象正确创建 |
| SPACE-002 | 计算百分比 | used=50, total=100 | 50.0 |

#### 9.2 SpaceManager测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-003 | 默认配置 | 无config | 使用默认80GB |
| SPACE-004 | 自定义配置 | disk_limit=100 | 限制生效 |

#### 9.3 get_disk_space测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-005 | 有效路径 | 任意存在路径 | 返回SpaceInfo |
| SPACE-006 | 磁盘信息准确 | 无 | total>available, used>0 |
| SPACE-007 | 百分比计算 | 无 | used_percent在0-100 |
| SPACE-008 | Windows路径 | C:\路径 | 正确识别磁盘 |
| SPACE-009 | Linux路径 | /路径 | 正确识别 |

#### 9.4 calculate_required_space测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-010 | 文件大小 | FileInfo, size=100 | 返回约220 |
| SPACE-011 | 文件夹大小 | FolderInfo, size=1000 | 返回约2200 |
| SPACE-012 | 估算公式正确 | 无 | 1.1倍+原大小 |

#### 9.5 can_process测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-013 | 空间足够 | 空间充足 | True |
| SPACE-014 | 空间不足 | 空间不足 | False |
| SPACE-015 | 已预留空间 | 已有预留 | 正确计算可用空间 |
| SPACE-016 | 接近限制 | 已用空间接近限制 | False |

#### 9.6 check_initial_space测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-017 | 空间正常 | 空间<限制 | 返回True |
| SPACE-018 | 空间超限 | 空间>=限制 | ValueError |
| SPACE-019 | 错误信息详细 | 超限 | 包含已用和限制信息 |

#### 9.7 reserve_space测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-020 | 正常预留 | 空间足够 | 成功进入上下文 |
| SPACE-021 | 空间不足等待 | 空间不足 | 等待后进入或超时 |
| SPACE-022 | 退出释放 | 退出上下文 | 预留空间释放 |
| SPACE-023 | 异常释放 | 上下文内异常 | 预留空间释放 |

#### 9.8 _check_space_available测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-024 | 空间充足 | required < available | True |
| SPACE-025 | 空间不足 | required > available | False |
| SPACE-026 | 考虑已预留 | 已有预留 | 正确计算 |

#### 9.9 wait_for_space测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-027 | 立即获得 | 空间充足 | 立即返回True |
| SPACE-028 | 等待获得 | 等待后空间充足 | 返回True |
| SPACE-029 | 超时 | 始终空间不足 | TimeoutError |
| SPACE-030 | 自定义超时 | timeout=60 | 60秒后超时 |

#### 9.10 release_space测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| SPACE-031 | 释放预留 | 有预留空间 | 预留减少 |
| SPACE-032 | 释放超过当前 | 释放值>当前预留 | 保持为0 |
| SPACE-033 | 多次释放 | 多次调用 | 正确累计 |

---

### 10. database_service.py - 数据库服务

#### 10.1 DatabaseService测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DB-001 | 默认凭证 | 无env | 使用默认配置 |
| DB-002 | 自定义凭证 | 自定义Credentials | 使用自定义配置 |
| DB-003 | 默认池配置 | 无config | pool_size=5 |

#### 10.2 _create_engine测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DB-004 | 创建引擎 | 无 | 返回SQLAlchemy Engine |
| DB-005 | 重复创建 | 调用两次 | 返回同一引擎 |
| DB-006 | 引擎配置 | 无 | 配置正确应用 |

#### 10.3 _create_session_factory测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DB-007 | 创建工厂 | 无 | 返回sessionmaker |
| DB-008 | 重复创建 | 调用两次 | 返回同一工厂 |

#### 10.4 get_session测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DB-009 | 获取会话 | 无 | 返回Session |
| DB-010 | 正常提交 | 无异常 | 自动commit |
| DB-011 | 异常回滚 | 抛出异常 | 自动rollback |
| DB-012 | 关闭会话 | 退出上下文 | 会话关闭 |

#### 10.5 create_tables测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DB-013 | 创建所有表 | 数据库存在 | 所有表创建 |
| DB-014 | 表已存在 | 表已存在 | 不报错 |

#### 10.6 drop_tables测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DB-015 | 删除所有表 | 表存在 | 所有表删除 |
| DB-016 | 表不存在 | 无表 | 不报错 |

#### 10.7 check_connection测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DB-017 | 连接正常 | 数据库可访问 | True |
| DB-018 | 连接失败 | 数据库不可访问 | False |
| DB-019 | 异常处理 | 连接异常 | 返回False |

#### 10.8 close测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DB-020 | 关闭连接 | 引擎已创建 | 引擎.dispose() |
| DB-021 | 重复关闭 | 多次调用 | 不报错 |
| DB-022 | 关闭后创建 | 关闭后再次使用 | 重新创建引擎 |

---

### 11. queue_manager.py - 队列管理器

#### 11.1 UploadTask测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-001 | 创建任务 | 有效参数 | 对象正确创建 |
| QUEUE-002 | 默认值 | 无 | retry_count=0, max_retry=5, priority=0 |
| QUEUE-003 | 优先级比较-高>低 | task1(p=1), task2(p=0) | task1 < task2 = True |
| QUEUE-004 | 优先级比较-低<高 | task1(p=0), task2(p=1) | task1 < task2 = False |
| QUEUE-005 | 非法比较 | UploadTask, int | NotImplemented |

#### 11.2 UploadResult测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-006 | 成功结果 | success=True | 对象正确创建 |
| QUEUE-007 | 失败结果 | success=False, error | 对象正确创建 |

#### 11.3 QueueManager测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-008 | 默认配置 | 无 | 使用默认UploadConfig |
| QUEUE-009 | 自定义配置 | 自定义config | 配置生效 |
| QUEUE-010 | 回调初始化 | 无 | on_success=None, on_failed=None |

#### 11.4 add_task测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-011 | 添加单任务 | 单个UploadTask | 队列大小+1 |
| QUEUE-012 | 添加多任务 | 多个UploadTask | 队列大小正确 |

#### 11.5 add_tasks测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-013 | 批量添加 | 任务列表 | 所有任务入队 |

#### 11.6 start测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-014 | 启动队列 | 队列为空 | _running=True |
| QUEUE-015 | 重复启动 | 已启动 | 不重复创建线程 |
| QUEUE-016 | 线程启动 | 调用start | 后台线程运行 |

#### 11.7 stop测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-017 | 停止队列 | 队列运行中 | _running=False |
| QUEUE-018 | 发送停止标记 | 队列运行中 | 队列收到停止标记 |
| QUEUE-019 | 等待线程结束 | 线程运行中 | 线程join完成 |
| QUEUE-020 | 停止未启动 | 未启动就停止 | 不报错 |

#### 11.8 _process_queue测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-021 | 处理任务 | 有效任务 | 调用_process_task |
| QUEUE-022 | 遇到停止标记 | 收到_SENTINEL | 退出循环 |
| QUEUE-023 | 队列空 | timeout | 继续循环 |

#### 11.9 _process_task测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-024 | 上传成功 | 成功上传 | 返回success=True |
| QUEUE-025 | 上传失败 | 上传异常 | 返回success=False |
| QUEUE-026 | 回调触发成功 | 设置on_success | 回调被调用 |
| QUEUE-027 | 回调触发失败 | 设置on_failed | 回调被调用 |

#### 11.10 重试机制测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-028 | 失败重试 | 首次失败, retry<max | 任务重新入队 |
| QUEUE-029 | 超过重试次数 | 重试次>=max | 调用on_failed |
| QUEUE-030 | 异常重试 | 任务抛出异常 | 任务重新入队 |

#### 11.11 _update_db_status测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-031 | 更新成功 | 存在记录 | 状态更新 |
| QUEUE-032 | 更新路径 | 成功上传 | 路径保存 |
| QUEUE-033 | 无db_service | db_service=None | 静默返回 |
| QUEUE-034 | 记录不存在 | 无匹配记录 | 不报错 |
| QUEUE-035 | 数据库异常 | 查询异常 | 静默处理 |

#### 11.12 属性测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-036 | queue_size | 队列有元素 | 返回正数 |
| QUEUE-037 | queue_size | 队列空 | 返回0 |
| QUEUE-038 | is_running | 启动后 | True |
| QUEUE-039 | is_running | 停止后 | False |

#### 11.13 clear测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| QUEUE-040 | 清空队列 | 队列有元素 | 队列变空 |
| QUEUE-041 | 清空空队列 | 队列空 | 不报错 |

---

### 12. upload_service/utils.py - 上传工具函数

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| UTL-001 | 标准路径提取 | 标准格式路径 | 正确提取date和password |
| UTL-002 | 无密码路径 | 无"解压密码" | password=None |
| UTL-003 | 无日期路径 | 无8位数字日期 | date=None |
| UTL-004 | 多个日期取第一个 | 路径含多个日期 | 取第一个有效日期 |
| UTL-005 | 日期验证-有效 | 有效日期如20260115 | date='20260115' |
| UTL-006 | 日期验证-无效 | 无效日期如20261345 | 不识别为日期 |
| UTL-007 | 密码提取-解压密码_ | "解压密码_abc" | password='abc' |
| UTL-008 | 密码提取-密码- | "密码-xyz" | password='xyz' |
| UTL-009 | 密码含数字字母 | "密码_123abc" | password='123abc' |
| UTL-010 | 严格模式 | 同标准模式 | 结果一致 |
| UTL-011 | Windows路径 | 带反斜杠路径 | 正确解析 |
| UTL-012 | Linux路径 | 带正斜杠路径 | 正确解析 |
| UTL-013 | 空字符串 | "" | (None, None) |
| UTL-014 | None输入 | None | 异常或错误处理 |

---

### 13. dedupe_service.py - 去重服务

#### 13.1 DedupeResult测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-001 | 创建结果 | 三个列表 | 对象正确创建 |

#### 13.2 DedupeService测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-002 | 默认配置 | 无 | 使用HashConfig默认 |
| DEDUPE-003 | 主机名获取 | 无 | 调用get_hostname() |

#### 13.3 compare_and_dedupe测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-004 | 全新文件 | 全部新文件 | not_found_in_db包含全部 |
| DEDUPE-005 | 重复文件 | 全部已存在 | already_backup包含全部 |
| DEDUPE-006 | 混合结果 | 部分新部分重复 | 三个列表都有内容 |
| DEDUPE-007 | 跳过ManualReviewItem | 包含ManualReviewItem | 自动跳过 |
| DEDUPE-008 | FileInfo处理 | FileInfo列表 | 正确计算文件Hash |
| DEDUPE-009 | FolderInfo处理 | FolderInfo列表 | 正确计算文件夹Hash |
| DEDUPE-010 | 数据库保存 | 新文件 | 保存到source_files表 |
| DEDUPE-011 | 重复记录 | 重复文件 | 保存到duplicate_files表 |
| DEDUPE-012 | 路径更新 | 同Hash不同路径 | 更新file_path |
| DEDUPE-013 | 异常处理 | Hash计算异常 | 异常传播 |

#### 13.4 _save_source_file测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-014 | 新记录 | 不存在的hash | 创建新记录 |
| DEDUPE-015 | 存在记录 | 已存在的hash | 更新路径 |
| DEDUPE-016 | FileInfo大小 | FileInfo | 使用file_size |
| DEDUPE-017 | FolderInfo大小 | FolderInfo | 使用total_size |
| DEDUPE-018 | is_backup默认值 | 新记录 | is_backup=False |

#### 13.5 _record_duplicate测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-019 | 新重复记录 | 首次出现重复 | 创建新记录 |
| DEDUPE-020 | 已存在重复 | 同hash已有记录 | 更新duplicate_count |
| DEDUPE-021 | 同路径跳过 | 同一文件重复记录 | 跳过 |
| DEDUPE-022 | master_file_path | 存在existing_source | 使用existing_source路径 |
| DEDUPE-023 | 无master | 不存在existing_source | 使用当前路径 |

#### 13.6 _query_source_by_hashes测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-024 | 找到已备份 | is_backup=True | 返回记录 |
| DEDUPE-025 | 找到未备份 | is_backup=False | 返回None |
| DEDUPE-026 | 未找到 | 不存在的hash | 返回None |
| DEDUPE-027 | 主机名过滤 | 不同主机 | 返回None |

#### 13.7 _query_completed_package_by_hashes测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-028 | 找到已完成的 | status='completed' | 返回记录 |
| DEDUPE-029 | 未完成 | status='pending' | 返回None |
| DEDUPE-030 | 未找到 | 不存在的hash | 返回None |

#### 13.8 save_source_files测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-031 | 保存多个 | 多个FileInfo/FolderInfo | 全部保存 |
| DEDUPE-032 | 未调用session.commit | 函数内 | 不提交, 由调用方控制 |

#### 13.9 mark_as_backup测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| DEDUPE-033 | 标记成功 | 找到记录 | is_backup=True |
| DEDUPE-034 | 标记时间 | 成功标记 | backup_time被设置 |
| DEDUPE-035 | 记录不存在 | 不存在的hash | 无操作 |

---

### 14. models/ - 数据库模型

#### 14.1 Base测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| MODEL-001 | 基类声明 | 无 | DeclarativeBase正确 |

#### 14.2 SourceFile测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| MODEL-002 | 创建记录 | 有效参数 | 字段正确设置 |
| MODEL-003 | __repr__ | 无 | 返回格式字符串 |
| MODEL-004 | to_dict | 无 | 返回字典, 包含所有字段 |
| MODEL-005 | to_dict含时间 | backup_time设置 | ISO格式字符串 |
| MODEL-006 | 字段约束 | nullable=False | 不能为空 |
| MODEL-007 | 索引检查 | 无 | hostname, md5, sha1, sha256有索引 |

#### 14.3 BackupPackage测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| MODEL-008 | 创建记录 | 有效参数 | 字段正确设置 |
| MODEL-009 | __repr__ | 无 | 返回格式字符串 |
| MODEL-010 | to_dict | 无 | 返回字典 |
| MODEL-011 | 外键关联 | source_file_id设置 | 可关联SourceFile |
| MODEL-012 | 默认status | 无 | status='pending' |
| MODEL-013 | 默认is_source_archive | 无 | False |

#### 14.4 DuplicateFile测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| MODEL-014 | 创建记录 | 有效参数 | 字段正确设置 |
| MODEL-015 | __repr__ | 无 | 返回格式字符串 |
| MODEL-016 | to_dict | 无 | 返回字典 |
| MODEL-017 | 默认duplicate_type | 无 | 'exact' |
| MODEL-018 | 默认duplicate_count | 无 | 1 |
| MODEL-019 | 外键 | master_source_file_id | 可关联SourceFile |

#### 14.5 ManualReviewItem测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| MODEL-020 | 创建记录 | 有效参数 | 字段正确设置 |
| MODEL-021 | __repr__ | 无 | 返回格式字符串 |
| MODEL-022 | to_dict | 无 | 返回字典 |
| MODEL-023 | 默认status | 无 | 'pending' |

#### 14.6 OperationLog测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| MODEL-024 | 创建记录 | 有效参数 | 字段正确设置 |
| MODEL-025 | __repr__ | 无 | 返回格式字符串 |
| MODEL-026 | to_dict | 无 | 返回字典 |
| MODEL-027 | 默认status | 无 | 必填, 不能为空 |

---

### 15. orchestrator.py - 主协调器（集成测试为主）

#### 15.1 BackupProgress测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-001 | 创建进度 | 无 | 默认值正确 |
| ORCH-002 | 更新phase | phase='scanning' | 更新成功 |

#### 15.2 OrchestratorConfig测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-003 | 创建配置 | config, db_service | 对象正确创建 |

#### 15.3 MainOrchestrator测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-004 | 初始化 | 有效Config | 所有服务初始化 |
| ORCH-005 | 服务组件 | 无 | classify/dedupe/verify/space/queue服务存在 |
| ORCH-006 | 数据库服务 | 无 | DatabaseService初始化 |
| ORCH-007 | 进度初始化 | 无 | BackupProgress使用默认值 |

#### 15.4 _get_source_paths测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-008 | paths存在且有效 | paths=[存在路径] | 返回paths列表 |
| ORCH-009 | paths为空path存在 | path=存在路径 | 返回[path] |
| ORCH-010 | 都不存在 | paths空, path空 | 返回空列表 |
| ORCH-011 | 过滤不存在 | paths含不存在路径 | 过滤掉 |

#### 15.5 _scan_source_folder测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-012 | 扫描并分类 | 有效目录 | 调用classify_service |
| ORCH-013 | 统计结果 | 无 | 正确统计normal/manual数量 |

#### 15.6 _process_single_item测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-014 | 重复文件-已备份 | is_duplicate=True | 调用_cleanup_duplicate |
| ORCH-015 | 已压缩文件 | FileInfo且is_archive | 直接上传 |
| ORCH-016 | 普通文件 | 非压缩 | 调用_compress_verify_upload |
| ORCH-017 | 处理异常 | 任意异常 | failed_items+1 |

#### 15.7 _check_duplicate测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-018 | 找到重复 | hash存在于DB | 返回(True, record) |
| ORCH-019 | 未找到重复 | hash不存在于DB | 返回(False, None) |
| ORCH-020 | 保存源文件 | 无 | 调用_save_source_file |

#### 15.8 _calculate_hashes测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-021 | FileInfo | FileInfo | 调用calculate_file_hash |
| ORCH-022 | FolderInfo | FolderInfo | 调用calculate_folder_hash |
| ORCH-023 | 使用配置算法 | 无 | 使用config.hash配置 |

#### 15.9 _save_source_file测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-024 | 新记录 | 不存在hash | 创建新SourceFile |
| ORCH-025 | 存在记录 | 存在hash | 更新路径 |
| ORCH-026 | 正确hash值 | 无 | md5/sha1/sha256都保存 |

#### 15.10 _compress_verify_upload测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-027 | 完整流程 | 正常项目 | 压缩→验证→上传 |
| ORCH-028 | 验证失败重试 | 验证失败 | 重新压缩 |
| ORCH-029 | 预留空间 | 无 | 调用reserve_space |
| ORCH-030 | 保存包信息 | 成功压缩 | 调用_save_package_info |

#### 15.11 _save_package_info测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-031 | 创建BackupPackage | 有效参数 | 创建记录 |
| ORCH-032 | ZIP hash计算 | 无 | 计算ZIP的hash |
| ORCH-033 | 关联SourceFile | 无 | 设置source_file_id |
| ORCH-034 | 密码设置 | 非源压缩文件 | 使用默认密码 |
| ORCH-035 | 记录已存在 | 同package_path | 跳过创建 |

#### 15.12 _save_manual_review_items测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-036 | 保存新项 | 有效ManualReviewItem | 创建记录 |
| ORCH-037 | 更新已存在 | 已存在的路径 | 更新状态为pending |
| ORCH-038 | 无需保存 | 无ManualReviewItem | 不操作 |

#### 15.13 _on_upload_success测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-039 | 清理ZIP | 非源压缩文件 | 删除ZIP |
| ORCH-040 | 保留源压缩文件 | 源压缩文件 | 不删除 |
| ORCH-041 | 清理源文件 | 成功上传 | 删除源文件/文件夹 |
| ORCH-042 | 标记已备份 | 成功上传 | is_backup=True, 设置backup_time |
| ORCH-043 | 异常清理 | 删除失败 | 记录日志不抛异常 |

#### 15.14 _on_upload_failed测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-044 | 记录失败 | 上传失败 | 记录日志 |
| ORCH-045 | 计数器增加 | 失败 | failed_items+1 |

#### 15.15 _check_manual_review_items测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-046 | 无待处理项 | 无pending | 不发送邮件 |
| ORCH-047 | 有待处理项 | 有pending | 调用发送邮件 |

#### 15.16 _send_manual_review_notification测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-048 | 未配置邮件 | 无SMTP配置 | 跳过发送 |
| ORCH-049 | 构建邮件内容 | 待处理项列表 | HTML格式正确 |
| ORCH-050 | 发送成功 | 配置正确 | 发送成功 |
| ORCH-051 | 发送失败 | SMTP错误 | 记录日志不抛异常 |

#### 15.17 run完整流程测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-052 | 无源路径 | source_paths为空 | 提前返回 |
| ORCH-053 | 启动上传队列 | 无 | 调用_start_uploader |
| ORCH-054 | 等待上传完成 | 无 | 调用_wait_for_uploads |
| ORCH-055 | 错误处理 | 任意阶段异常 | 更新进度为failed, 抛异常 |
| ORCH-056 | 完成状态 | 全部成功 | 更新进度为completed |

#### 15.18 其他方法测试

| 测试用例ID | 测试场景 | 输入 | 预期结果 |
|-----------|---------|------|---------|
| ORCH-057 | stop | 无 | 停止队列管理器 |
| ORCH-058 | progress属性 | 无 | 返回当前进度 |
| ORCH-059 | _log | 消息 | 打印并可能调用回调 |
| ORCH-060 | _update_progress | 进度信息 | 更新_progress对象 |

---

## 集成测试场景

| 测试用例ID | 测试场景 | 说明 |
|-----------|---------|------|
| INT-001 | 完整备份流程 | 扫描→分类→去重→压缩→验证→上传 |
| INT-002 | 大文件处理 | >500MB文件的Hash计算和ZIP处理 |
| INT-003 | 并发上传 | 多任务队列处理 |
| INT-004 | 数据库事务 | 回滚和提交正确处理 |
| INT-005 | 网络异常 | 上传失败和重试 |
| INT-006 | 磁盘空间不足 | SpaceManager正确处理 |
| INT-007 | ZIP加密上传 | 完整加密ZIP流程 |
| INT-008 | 重复文件去重 | Hash比对和清理 |
| INT-009 | 配置加载 | TOML和.env正确加载 |
| INT-010 | 回调机制 | on_progress/on_log回调 |

---

## Mock策略

### 需要Mock的外部依赖
1. **数据库**: 使用SQLite内存数据库或SQLAlchemy mock
2. **百度API**: 使用requests mock或responses库
3. **文件系统**: 使用tempfile和unittest.mock
4. **网络请求**: 使用responses库或httpx-mock
5. **SMTP**: 使用smtplib mock

### Mock示例
```python
# 数据库Mock示例
@pytest.fixture
def mock_session():
    session = MagicMock()
    session.query.return_value.filter.return_value.first.return_value = None
    return session

# 文件系统Mock示例
with patch('pathlib.Path.exists', return_value=True):
    with patch('pathlib.Path.is_file', return_value=True):
        # 测试代码
```

---

## 测试数据准备

### 临时文件/目录
- 使用`tempfile`模块创建临时测试目录
- 使用`@pytest.fixture`管理测试数据生命周期

### 测试数据文件
- 小文件: 1KB - 10KB
- 中文件: 1MB - 10MB
- 大文件: >500MB (可选，耗时测试)
- 特殊名称文件: 含空格、中文、特殊字符
- 压缩文件: ZIP、7z、rar等

---

## 测试执行顺序

1. **单元测试** (每个模块独立)
2. **集成测试** (模块间交互)
3. **端到端测试** (完整流程)

---

## 覆盖率目标

| 类型 | 目标覆盖率 |
|------|-----------|
| 行覆盖率 | 100% |
| 分支覆盖率 | 100% |
| 函数覆盖率 | 100% |
| 条件覆盖率 | 100% |

---

## 附录：测试用例统计

| 模块 | 用例数量 |
|------|---------|
| config.py | 47 |
| hash_service/core.py | 7 |
| hash_service/file_hash.py | 21 |
| hash_service/folder_hash.py | 33 |
| hash_service/__init__.py | 4 |
| classify_service.py | 42 |
| zip_service.py | 43 |
| verify_service.py | 25 |
| space_manager.py | 33 |
| database_service.py | 22 |
| queue_manager.py | 41 |
| upload_service/utils.py | 14 |
| dedupe_service.py | 35 |
| models/ | 27 |
| orchestrator.py | 60 |
| **合计** | **454** |

---

*文档生成时间: 2026-01-20*
*版本: 1.0*
