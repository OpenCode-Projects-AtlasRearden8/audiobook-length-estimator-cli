"""Manuscript handling: word counting, inline tokens, and file parsing."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

WORD_FILE_SUFFIXES = (".txt", ".md", ".markdown", ".rst", ".rtf")


@dataclass
class Chapter:
    """One chapter entry: a title and its word count."""

    title: str
    words: int

    @property
    def is_file(self) -> bool:
        return False


@dataclass
class FileChapter(Chapter):
    """A chapter loaded from a manuscript file."""

    path: str

    @property
    def is_file(self) -> bool:
        return True


def count_words(text: str) -> int:
    """Count words in a manuscript using whitespace separation."""
    return len(text.split())


def title_from_stem(stem: str) -> str:
    """Turn a filename stem into a readable chapter title."""
    title = re.sub(r"[-_]+", " ", stem).strip()
    return title if title else "untitled"


def chapter_from_file(path: Path) -> FileChapter:
    """Read a manuscript file and count its words."""
    text = path.read_text(encoding="utf-8", errors="replace")
    return FileChapter(
        title=title_from_stem(path.stem), words=count_words(text), path=str(path)
    )


def chapter_from_token(token: str) -> Chapter:
    """Parse an inline word-count source.

    Formats: ``Title=1234`` or simply ``1234`` (auto-titled as Chapter N).
    """
    if token.count("=") > 1:
        raise ValueError(f"invalid source {token!r}: expected at most one '='")
    if "=" in token:
        title, _, words_part = token.partition("=")
        title = title.strip()
        if not title:
            raise ValueError(f"invalid source {token!r}: empty title before '='")
        return Chapter(title=title, words=_words_number(words_part, token))
    return Chapter(title="", words=_words_number(token, token))


def _words_number(text: str, token: str) -> int:
    text = text.strip().replace(",", "")
    try:
        words = int(text)
    except ValueError as exc:
        raise ValueError(
            f"invalid source {token!r}: {text!r} is not a word count"
        ) from exc
    if words < 0:
        raise ValueError(f"invalid source {token!r}: word counts cannot be negative")
    if words == 0:
        raise ValueError(f"invalid source {token!r}: word count must be positive")
    return words


def build_chapters(sources: List[str]) -> List[Chapter]:
    """Resolve CLI sources in order: files on disk, else inline word counts."""
    chapters: List[Chapter] = []
    auto_title_index = 1
    for source in sources:
        if os.path.exists(source):
            path = Path(source)
            if not path.is_file():
                raise ValueError(f"{source!r} is a directory, not a manuscript file")
            chapters.append(chapter_from_file(path))
            continue
        if os.path.splitext(source)[1].lower() in WORD_FILE_SUFFIXES:
            raise FileNotFoundError(
                f"manuscript file {source!r} not found (it looks like a word-count "
                "file, but no such file exists)"
            )
        chapter = chapter_from_token(source)
        if not chapter.title:
            chapter.title = f"Source {auto_title_index}"
        chapters.append(chapter)
        auto_title_index += 1
    return chapters


def sum_words(chapters: Iterable[Chapter]) -> int:
    """Total word count across chapters."""
    return sum(chapter.words for chapter in chapters)
