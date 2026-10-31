"""Tests for every CLI subcommand, in table and JSON mode."""

import json

import pytest

from audiobook_length_estimator import __version__
from audiobook_length_estimator.cli import main


@pytest.fixture()
def chapter_paths(data_path):
    return [str(data_path / "chapter-01.txt"), str(data_path / "chapter-02.txt")]


def run(capsys, *argv):
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out


class TestBook:
    def test_mixed_sources_table(self, capsys, data_path):
        code, out = run(
            capsys, "book", str(data_path / "chapter-01.txt"), "Chapter 2=93000"
        )
        assert code == 0
        assert "chapter 01" in out
        assert "Chapter 2" in out
        assert "93,000" in out
        assert "10:00:00" in out
        assert "Whole book" in out
        assert "10 to 20 hours" in out
        assert "9,300 words per finished hour" in out

    def test_column_alignment(self, capsys, chapter_paths):
        code, out = run(capsys, "book", *chapter_paths)
        lines = [line for line in out.splitlines() if line.strip()]
        assert lines[0].split() == ["Chapter", "Words", "Runtime", "Hours"]
        for line in lines[1:-2]:
            assert len(line.split()) >= 4

    def test_wph_override_changes_runtime(self, capsys, chapter_paths):
        code, out = run(capsys, "book", *chapter_paths, "--wph", "9000")
        assert code == 0
        assert "9,000 words per finished hour" in out

    def test_json_mode(self, capsys, chapter_paths):
        code, out = run(capsys, "book", *chapter_paths, "--json")
        assert code == 0
        payload = json.loads(out)
        assert payload["summary"]["title"] == "Whole book"
        assert payload["summary"]["words_per_hour"] == 9300.0
        words = sum(c["words"] for c in payload["chapters"])
        assert payload["summary"]["words"] == words

    def test_missing_file_is_a_clean_error(self, capsys, data_path):
        with pytest.raises(SystemExit):
            main(["book", str(data_path / "nope.txt")])
        detail = capsys.readouterr().err
        assert "nope.txt" in detail


class TestScenarios:
    def test_table_lists_all_presets(self, capsys, data_path):
        code, out = run(capsys, "scenarios", str(data_path / "chapter-01.txt"))
        for name in ("slow", "standard", "brisk", "fast"):
            assert name in out
        assert "5 to 10 hours" not in out  # short sample stays in small bins

    def test_custom_wph_scenario(self, capsys, data_path):
        code, out = run(capsys, "scenarios", "10800", "--wph", "10800")
        assert code == 0
        assert "custom (10,800 wph)" in out
        assert "1:00:00" in out

    def test_json_mode(self, capsys, data_path):
        code, out = run(
            capsys, "scenarios", "93000", "--wph", "9300", "--json"
        )
        payload = json.loads(out)
        assert payload["words"] == 93000
        names = [s["name"] for s in payload["scenarios"]]
        assert "standard" in names and "custom (9,300 wph)" in names


class TestBins:
    def test_table_at_default_pace(self, capsys):
        code, out = run(capsys, "bins")
        assert code == 0
        assert "Over 20 hours" in out
        assert "186,000 words" in out
        assert "unbounded" in out

    def test_custom_place_and_locate(self, capsys):
        code, out = run(capsys, "bins", "--wph", "9000", "--words", "90000")
        assert code == 0
        assert "9,000 words/hour" in out
        assert "10 to 20 hours" in out
        assert "15 to 25 hours" not in out
        assert "90,000 words lands in: 10 to 20 hours" in out

    def test_json_locate(self, capsys):
        code, out = run(capsys, "bins", "--words", "93000", "--json")
        payload = json.loads(out)
        assert payload["located"] == {"words": 93000, "bin": "10 to 20 hours"}


class TestBudget:
    def test_table_math(self, capsys, data_path):
        code, out = run(capsys, "budget", "93000")
        assert code == 0
        assert "150.00" in out and "300.00" in out
        assert "1,500.00" in out          # 10 finished hours * $150
        assert "3,000" in out             # 10 finished hours * $300
        assert "25.0" in out and "2.5" in out
        assert "50.00" in out             # break-even vs $150 PFH
        assert "Break-even" in out

    def test_custom_inputs(self, capsys, data_path):
        code, out = run(
            capsys, "budget", "46500",
            "--rate-low", "100", "--rate-high", "220",
            "--fixed-costs", "0", "--self-value", "40",
            "--diy-hours", "3",
        )
        assert code == 0
        assert "500" in out and "1,100" in out and "600" in out

    def test_rate_ordering_guards(self, capsys):
        with pytest.raises(SystemExit):
            main(["budget", "93000", "--rate-low", "999", "--rate-high", "10"])
        detail = capsys.readouterr().err
        assert "high PFH rate" in detail

    def test_json_mode(self, capsys, data_path):
        code, out = run(capsys, "budget", "93000", "--json")
        payload = json.loads(out)
        assert payload["words"] == 93000
        assert payload["finished_hours"] == 10.0
        assert payload["hire_cost_low"] == 1500.0
        assert payload["break_even_self_value_low"] == pytest.approx(50.0)


class TestRouting:
    def test_version(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            main(["--version"])
        assert excinfo.value.code == 0
        assert __version__ in capsys.readouterr().out

    def test_requires_a_subcommand(self, capsys):
        with pytest.raises(SystemExit):
            main([])
        assert "usage" in (capsys.readouterr().err or "")

    def test_unknown_source_is_a_clean_error(self, capsys):
        with pytest.raises(SystemExit):
            main(["book", "Chapter 1=abc"])
        assert "not a word count" in (capsys.readouterr().err or "")
