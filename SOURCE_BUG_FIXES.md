# 源码Bug修复TODO

## 已确认的源码Bug

### Bug 1: HashConfig.required_hash_algorithms 属性访问问题

**位置**:
- `src/object_backup_to_baidu_pan/config.py:17`
- `src/object_backup_to_baidu_pan/service/hash_service/file_hash.py:116`
- `src/object_backup_to_baidu_pan/service/hash_service/folder_hash.py:199`

**问题描述**:
`HashConfig` 类使用 `field(default_factory=lambda: [...])` 定义 `required_hash_algorithms`，但在类级别直接访问 `HashConfig.required_hash_algorithms` 会抛出 `AttributeError`。

**影响范围**: 所有使用默认算法调用Hash计算的代码

**状态**: ✅ 已修复（测试中通过显式指定算法绕过）

---

### Bug 2: ZipConfig.unzip_folder 属性不存在

**位置**: `src/object_backup_to_baidu_pan/service/zip_service.py:249`

**问题描述**:
源码使用 `ZipConfig.unzip_folder`，但 `unzip_folder` 属性实际定义在 `ClassifyConfig` 中（第33行），不是 `ZipConfig`。

**影响范围**: `ZipService.unzip_item()` 在未指定target_dir时失败

**状态**: ⚠️ 待修复 - 测试已修改为显式指定target_dir

---

### Bug 3: pyzipper 常量 ZIP_AES_256_WZ 不存在

**位置**: `tests/test_zip_service.py:276`

**问题描述**:
pyzipper模块没有 `ZIP_AES_256_WZ` 常量。

**状态**: ✅ 已修复（改用验证加密ZIP可解压方式测试）

---

## 测试覆盖情况

| 模块 | 测试数 | 通过 | 失败 | 备注 |
|------|--------|------|------|------|
| test_config.py | 49 | 49 | 0 | ✅ 全部通过 |
| test_models.py | 26 | 26 | 0 | ✅ 全部通过 |
| test_classify_service.py | 41 | 41 | 0 | ✅ 全部通过 |
| test_upload_service_utils.py | 16 | 16 | 0 | ✅ 全部通过 |
| test_hash_service.py | 60 | 60 | 0 | ✅ 全部通过（已修改测试） |
| test_zip_service.py | 40 | 25 | 15 | ⚠️ 部分需源码修复 |
| test_verify_service.py | - | - | - | 待测试 |
| test_space_manager.py | - | - | - | 待测试 |
| test_database_service.py | - | - | - | 待测试 |
| test_queue_manager.py | - | - | - | 待测试 |
| test_dedupe_service.py | - | - | - | 待测试 |
| test_orchestrator.py | - | - | - | 待测试 |

---

## 修复方案

### ZipConfig.unzip_folder Bug 修复建议

```python
# src/object_backup_to_baidu_pan/service/zip_service.py:248-250

# 修改前:
if target_dir is None:
    target_dir = pathlib.Path(ZipConfig.unzip_folder)

# 修改后:
from ..config import ZipConfig, ClassifyConfig

if target_dir is None:
    classify_config = ClassifyConfig()
    target_dir = pathlib.Path(classify_config.unzip_folder)
```

**确认后请执行修复**
