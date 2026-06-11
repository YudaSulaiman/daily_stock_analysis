from pathlib import Path

from scripts.enforce_english_artifacts import (
    PLACEHOLDER,
    enforce_files,
    has_cjk_text,
    sanitize_text,
)


def test_sanitize_text_redacts_cjk_and_preserves_english() -> None:
    sanitized = sanitize_text("DeepSeek 输出中文：大盘复盘, test")

    assert "DeepSeek" in sanitized
    assert "test" in sanitized
    assert PLACEHOLDER in sanitized
    assert not has_cjk_text(sanitized)


def test_enforce_files_updates_text_files(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    logs_dir = tmp_path / "logs"
    reports_dir.mkdir()
    logs_dir.mkdir()
    report = reports_dir / "sample.md"
    log = logs_dir / "sample.log"
    report.write_text("Report 中文 大盘复盘\n", encoding="utf-8")
    log.write_text("Log テスト 테스트\n", encoding="utf-8")

    checked, changed = enforce_files([str(reports_dir), str(logs_dir)])

    assert (checked, changed) == (2, 2)
    assert PLACEHOLDER in report.read_text(encoding="utf-8")
    assert PLACEHOLDER in log.read_text(encoding="utf-8")
    assert not has_cjk_text(report.read_text(encoding="utf-8"))
    assert not has_cjk_text(log.read_text(encoding="utf-8"))


def test_enforce_files_skips_binary_files(tmp_path: Path) -> None:
    binary = tmp_path / "blob.bin"
    binary.write_bytes(b"\0\x01\x02")

    checked, changed = enforce_files([str(tmp_path)])

    assert (checked, changed) == (0, 0)
