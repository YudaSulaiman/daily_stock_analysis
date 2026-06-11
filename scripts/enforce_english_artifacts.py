#!/usr/bin/env python3
"""Redact CJK text from scheduler output and uploaded artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
from typing import Iterable, Sequence


PLACEHOLDER = "[non-English text removed]"

CJK_TEXT_RE = re.compile(
    "["
    "\u3400-\u4DBF"
    "\u4E00-\u9FFF"
    "\uF900-\uFAFF"
    "\U00020000-\U0002A6DF"
    "\U0002A700-\U0002B73F"
    "\U0002B740-\U0002B81F"
    "\U0002B820-\U0002CEAF"
    "\U0002CEB0-\U0002EBEF"
    "\U00030000-\U0003134F"
    "\u3040-\u30FF"
    "\uAC00-\uD7AF"
    "]+"
)

FULLWIDTH_RANGE_RE = re.compile("[\u3000-\u303F\uFF00-\uFFEF]")

CJK_PUNCTUATION_TRANS = str.maketrans(
    {
        "\u3000": " ",
        "\u3001": ",",
        "\u3002": ".",
        "\u3008": "<",
        "\u3009": ">",
        "\u300A": "<",
        "\u300B": ">",
        "\u3010": "[",
        "\u3011": "]",
        "\uFF01": "!",
        "\uFF08": "(",
        "\uFF09": ")",
        "\uFF0C": ",",
        "\uFF0E": ".",
        "\uFF1A": ":",
        "\uFF1B": ";",
        "\uFF1F": "?",
    }
)


def sanitize_text(text: str) -> str:
    """Replace CJK text and fullwidth punctuation with English-safe output."""
    text = text.translate(CJK_PUNCTUATION_TRANS)
    text = CJK_TEXT_RE.sub(PLACEHOLDER, text)
    text = FULLWIDTH_RANGE_RE.sub(" ", text)
    text = re.sub(
        r"(?:\s*" + re.escape(PLACEHOLDER) + r"\s*){2,}",
        f" {PLACEHOLDER} ",
        text,
    )
    return re.sub(r"[ \t]{2,}", " ", text)


def has_cjk_text(text: str) -> bool:
    """Return whether the text still contains blocked CJK content."""
    return bool(CJK_TEXT_RE.search(text) or FULLWIDTH_RANGE_RE.search(text))


def _iter_text_files(roots: Iterable[Path]) -> Iterable[Path]:
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            yield root
            continue
        for path in root.rglob("*"):
            if path.is_file():
                yield path


def _read_text(path: Path) -> str | None:
    raw = path.read_bytes()
    if b"\0" in raw[:4096]:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def enforce_files(paths: Sequence[str]) -> tuple[int, int]:
    """Sanitize text files under paths and return (checked, changed)."""
    checked = 0
    changed = 0
    for path in _iter_text_files(Path(p) for p in paths):
        text = _read_text(path)
        if text is None:
            continue
        checked += 1
        sanitized = sanitize_text(text)
        if has_cjk_text(sanitized):
            raise RuntimeError(f"English artifact enforcement failed for {path}")
        if sanitized != text:
            path.write_text(sanitized, encoding="utf-8")
            changed += 1
    return checked, changed


def stream_filter() -> int:
    for line in sys.stdin:
        sys.stdout.write(sanitize_text(line))
        sys.stdout.flush()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Redact CJK text from scheduler logs and artifact files.",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="read stdin, write sanitized stdout, and exit",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["reports", "logs"],
        help="files or directories to sanitize before artifact upload",
    )
    args = parser.parse_args(argv)

    if args.stream:
        return stream_filter()

    checked, changed = enforce_files(args.paths)
    print(
        f"English artifact enforcement checked {checked} file(s), "
        f"updated {changed} file(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
