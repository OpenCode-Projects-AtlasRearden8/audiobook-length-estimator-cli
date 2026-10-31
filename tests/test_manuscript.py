"""Tests for manuscript parsing and source resolution."""

import pytest

from audiobook_length_estimator.manuscript import (
    build_chapters,
    chapter_from_file,
    chapter_from_token,
    count_words,
    title_from_stem,
)


class TestCountWords:
    def test_whitespace_counting(self):
        assert count_words("one two   three\n\tfour") == 4

    def test_empty_text(self):
        assert count_words("") == 0
        assert count_words("   \n  ") == 0


class TestTitles:
    def test_underscores_and_dashes_become_spaces(self):
        assert title_from_stem("chapter-02_the_port") == "chapter 02 the port"
        assert title_from_stem("epilogue") == "epilogue"
        assert title_from_stem("") == "untitled"


class TestTokens:
    def test_inline_count_with_title(self):
        chapter = chapter_from_token("Chapter 1=5,400")
        assert chapter.title == "Chapter 1"
        assert chapter.words == 5400

    def test_bare_count_is_autotitled(self):
        chapter = chapter_from_token("9200")
        assert chapter.title == ""
        assert chapter.words == 9200

    def test_rejects_bad_tokens(self):
        with pytest.raises(ValueError):
            chapter_from_token("Chapter 1=zero")
        with pytest.raises(ValueError):
            chapter_from_token("12=3=4")
        with pytest.raises(ValueError):
            chapter_from_token("=-12")
        with pytest.raises(ValueError):
            chapter_from_token("")
        with pytest.raises(ValueError):
            chapter_from_token("abc")
        with pytest.raises(ValueError):
            chapter_from_token("Title=0")


class TestFiles:
    def test_counts_real_file(self, data_path):
        chapter = chapter_from_file(data_path / "chapter-01.txt")
        assert chapter.title == "chapter 01"
        assert chapter.words > 0
        assert chapter.path.endswith("chapter-01.txt")

    def test_counts_are_stable_across_reads(self, data_path):
        first = chapter_from_file(data_path / "chapter-01.txt")
        second = chapter_from_file(data_path / "chapter-02.txt")
        assert first.words == chapter_from_file(data_path / "chapter-01.txt").words
        assert second.words == chapter_from_file(data_path / "chapter-02.txt").words
        assert first.words > 400
        assert second.words > 400


class TestBuildChapters:
    def test_mixed_sources_in_order(self, data_path):
        chapters = build_chapters(
            [str(data_path / "chapter-01.txt"), "Interlude=500", "900"]
        )
        assert [(ch.title, ch.words) for ch in chapters[:2]] == [
            ("chapter 01", chapters[0].words),
            ("Interlude", 500),
        ]
        assert chapters[2].title == "Source 2"
        assert chapters[2].words == 900
        assert chapters[0].is_file
        assert not chapters[1].is_file

    def test_missing_word_file_raises_friendly_error(self):
        with pytest.raises(FileNotFoundError, match="missing-book.txt"):
            build_chapters(["missing-book.txt"])

    def test_directory_is_rejected(self, data_path):
        with pytest.raises(ValueError, match="directory"):
            build_chapters([str(data_path)])

    def test_empty_source_list_gives_no_chapters(self):
        assert build_chapters([]) == []
