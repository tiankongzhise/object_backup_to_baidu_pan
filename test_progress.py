#!/usr/bin/env python
"""测试进度报告和执行脚本"""
import subprocess
import sys
import time
from pathlib import Path

# 测试文件列表
TEST_FILES = [
    ("test_config.py", "配置模块测试"),
    ("test_models.py", "数据模型测试"),
    ("test_classify_service.py", "分类服务测试"),
    ("test_upload_service_utils.py", "上传工具测试"),
    ("test_hash_service.py", "哈希服务测试"),
    ("test_zip_service.py", "ZIP服务测试"),
    ("test_verify_service.py", "验证服务测试"),
    ("test_space_manager.py", "空间管理测试"),
    ("test_database_service.py", "数据库服务测试"),
    ("test_queue_manager.py", "队列管理测试"),
    ("test_dedupe_service.py", "去重服务测试"),
    ("test_orchestrator.py", "协调器测试"),
]

def run_test_with_timeout(test_file: str, timeout: int = 60) -> dict:
    """运行单个测试文件，返回结果"""
    cmd = ["uv", "run", "pytest", f"tests/{test_file}", "-v", "--tb=short"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout + result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "TIMEOUT",
            "returncode": -1
        }

def parse_test_results(output: str) -> dict:
    """解析测试输出"""
    result = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "error": 0,
        "coverage": 0.0
    }

    # 解析测试数量
    import re

    # 查找passed, failed, error数量
    passed_match = re.search(r'(\d+) passed', output)
    failed_match = re.search(r'(\d+) failed', output)
    error_match = re.search(r'(\d+) error', output)
    total_match = re.search(r'(\d+) passed.*(\d+) failed', output)

    if passed_match:
        result["passed"] = int(passed_match.group(1))
    if failed_match:
        result["failed"] = int(failed_match.group(1))
    if error_match:
        result["error"] = int(error_match.group(1))

    # 尝试解析覆盖率
    coverage_match = re.search(r'Total.*?(\d+%)', output)
    if coverage_match:
        result["coverage"] = float(coverage_match.group(1).replace('%', ''))

    result["total"] = result["passed"] + result["failed"] + result["error"]
    return result

def main():
    """主函数"""
    print("=" * 80)
    print("测试进度报告")
    print("=" * 80)
    print(f"测试文件总数: {len(TEST_FILES)}")
    print("-" * 80)

    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    all_results = []

    for i, (test_file, description) in enumerate(TEST_FILES, 1):
        print(f"\n[{i}/{len(TEST_FILES)}] 正在运行: {test_file} - {description}")

        result = run_test_with_timeout(test_file, timeout=120)
        test_result = parse_test_results(result["output"])
        test_result["file"] = test_file
        test_result["description"] = description

        if result["output"] == "TIMEOUT":
            print(f"  ⚠️  超时")
            test_result["status"] = "TIMEOUT"
        elif test_result["total"] > 0:
            status = "✓ 通过" if test_result["failed"] == 0 and test_result["error"] == 0 else "✗ 失败"
            print(f"  {status} - 共{test_result['total']}个，通过{test_result['passed']}个，失败{test_result['failed']}个")
            test_result["status"] = "PASS" if test_result["failed"] == 0 else "FAIL"
        else:
            print(f"  ⚠️  无测试结果")
            test_result["status"] = "UNKNOWN"

        total_tests += test_result["total"]
        total_passed += test_result["passed"]
        total_failed += test_result["failed"]
        total_errors += test_result["error"]
        all_results.append(test_result)

    # 汇总报告
    print("\n" + "=" * 80)
    print("测试汇总报告")
    print("=" * 80)
    print(f"测试文件总数: {len(TEST_FILES)}")
    print(f"测试用例总数: {total_tests}")
    print(f"通过: {total_passed}")
    print(f"失败: {total_failed}")
    print(f"错误: {total_errors}")
    print(f"成功率: {(total_passed / total_tests * 100) if total_tests > 0 else 0:.1f}%")
    print("=" * 80)

    # 详细结果表
    print("\n详细结果:")
    print("-" * 80)
    print(f"{'文件':<30} {'状态':<10} {'总数':<8} {'通过':<8} {'失败':<8}")
    print("-" * 80)
    for r in all_results:
        status_icon = "✓" if r["status"] == "PASS" else "✗" if r["status"] == "FAIL" else "⚠"
        print(f"{r['file']:<30} {status_icon} {r['status']:<10} {r['total']:<8} {r['passed']:<8} {r['failed']:<8}")
    print("-" * 80)

    return all_results

if __name__ == "__main__":
    main()
