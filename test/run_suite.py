from __future__ import annotations

from datetime import datetime
import io
from pathlib import Path
import platform
import sys
import unittest


REPORT_PATH = Path(__file__).resolve().parent.parent / "docs" / "测试文档-time.md"


def build_markdown_report(result: unittest.TestResult, raw_output: str) -> str:
    """把测试执行结果转换为 Markdown 报告。"""

    failure_count = len(result.failures)
    error_count = len(result.errors)
    skipped_count = len(result.skipped)
    passed_count = result.testsRun - failure_count - error_count - skipped_count

    lines = [
        "# 测试文档",
        "",
        f"- 生成时间: {datetime.now().isoformat()}",
        f"- Python: {platform.python_version()}",
        f"- 平台: {platform.platform()}",
        f"- 执行用例总数: {result.testsRun}",
        f"- 通过: {passed_count}",
        f"- 失败: {failure_count}",
        f"- 错误: {error_count}",
        f"- 跳过: {skipped_count}",
        "",
        "## 执行摘要",
        "",
        "```text",
        raw_output.rstrip(),
        "```",
        "",
    ]

    if not result.failures and not result.errors:
        lines.extend(
            [
                "## 错误记录",
                "",
                "本轮未发现失败或执行错误。",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(["## 错误记录", ""])
    for test_case, traceback_text in result.failures:
        lines.extend(
            [
                f"### 失败: {test_case.id()}",
                "",
                "```text",
                traceback_text.rstrip(),
                "```",
                "",
            ]
        )

    for test_case, traceback_text in result.errors:
        lines.extend(
            [
                f"### 错误: {test_case.id()}",
                "",
                "```text",
                traceback_text.rstrip(),
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def main() -> int:
    """运行测试并同步产出 Markdown 报告。"""

    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), pattern="test_*.py")
    buffer = io.StringIO()
    runner = unittest.TextTestRunner(stream=buffer, verbosity=2)
    result = runner.run(suite)

    raw_output = buffer.getvalue()
    sys.stdout.write(raw_output)
    REPORT_PATH.write_text(build_markdown_report(result, raw_output), encoding="utf-8")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
