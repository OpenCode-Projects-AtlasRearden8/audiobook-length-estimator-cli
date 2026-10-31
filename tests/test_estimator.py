"""Tests for the core estimation math."""

import pytest

from audiobook_length_estimator.estimator import (
    DEFAULT_WPH,
    acx_bins,
    bin_for_hours,
    break_even_self_value,
    budget_comparison,
    pace_scenarios,
    runtime_str,
    words_to_hours,
)
from audiobook_length_estimator.manuscript import Chapter, sum_words


class TestWordsToHours:
    def test_book_at_standard_pace(self):
        assert words_to_hours(93000, 9300) == pytest.approx(10.0)

    def test_default_wph_used_when_omitted(self):
        assert words_to_hours(46500) == pytest.approx(5.0)

    def test_zero_words_is_zero_hours(self):
        assert words_to_hours(0, 12500) == 0.0

    def test_rejects_nonpositive_wph(self):
        with pytest.raises(ValueError):
            words_to_hours(100, 0)
        with pytest.raises(ValueError):
            words_to_hours(100, -100)


class TestRuntimeStr:
    def test_whole_hours(self):
        assert runtime_str(2.0) == "2:00:00"

    def test_fractional_hours(self):
        assert runtime_str(1.5) == "1:30:00"

    def test_seconds_rounded(self):
        # 1/3 of a second above 10 seconds rounds down.
        assert runtime_str(0.0 + 10.0001 / 3600) == "0:00:10"

    def test_very_short_runtime(self):
        assert runtime_str(0.0) == "0:00:00"

    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            runtime_str(-0.5)


class TestBins:
    def test_six_tiers(self):
        bins = acx_bins()
        assert [b.label for b in bins] == [
            "Under 1 hour",
            "1 to 3 hours",
            "3 to 5 hours",
            "5 to 10 hours",
            "10 to 20 hours",
            "Over 20 hours",
        ]

    def test_word_boundaries_at_standard_pace(self):
        bins = acx_bins(9300)
        by_label = {b.label: b for b in bins}
        assert by_label["Under 1 hour"].min_words == 0
        assert by_label["Under 1 hour"].max_words == 9300
        assert by_label["1 to 3 hours"].min_words == 9301
        assert by_label["1 to 3 hours"].max_words == 27900
        assert by_label["3 to 5 hours"].max_words == 46500
        assert by_label["5 to 10 hours"].max_words == 93000
        assert by_label["10 to 20 hours"].max_words == 186000
        over = by_label["Over 20 hours"]
        assert over.min_words == 186001
        assert over.max_words is None

    def test_boundaries_scale_with_pace(self):
        by_label = {b.label: b for b in acx_bins(9000)}
        assert by_label["3 to 5 hours"].max_words == 45000

    def test_bin_for_hours_matches_word_count_location(self):
        words = 90000
        hours = words_to_hours(words, 9300)
        assert bin_for_hours(hours, 9300).label == "5 to 10 hours"

    def test_bin_edge_cases(self):
        assert bin_for_hours(0, 9300).label == "Under 1 hour"
        assert bin_for_hours(0.9999, 9300).label == "Under 1 hour"
        assert bin_for_hours(1.0, 9300).label == "1 to 3 hours"
        assert bin_for_hours(100, 9300).label == "Over 20 hours"

    def test_boundary_word_count_lands_in_upper_bin(self):
        # A word count sits in a bin only via runtime, so an exact boundary
        # count's runtime crosses into the next bin.
        hours = words_to_hours(9301, 9300)
        assert bin_for_hours(hours, 9300).label == "1 to 3 hours"

    def test_bins_reject_bad_wph(self):
        with pytest.raises(ValueError):
            acx_bins(-1)


class TestBreakEven:
    def test_matches_hand_computed_value(self):
        # rate 200 PFH, 10 finished hours, zero fixed costs, 2.5x DIY factor:
        # DIY hours = 25; your time must be worth 2000 / 25 = 80/hour.
        assert break_even_self_value(10, 200) == pytest.approx(80.0)

    def test_fixed_costs_lower_the_break_even(self):
        # 2000 - 500 fixed = 1500 to pay yourself over 25 DIY hours.
        assert break_even_self_value(10, 200, fixed_costs=500) == pytest.approx(60.0)

    def test_requires_finished_hours(self):
        with pytest.raises(ValueError):
            break_even_self_value(0, 200)
        with pytest.raises(ValueError):
            break_even_self_value(10, 200, diy_hours_per_finished_hour=0)


class TestPaceScenarios:
    def test_default_presets(self):
        scenarios = pace_scenarios(93000)
        assert [s.name for s in scenarios] == ["slow", "standard", "brisk", "fast"]
        standard = scenarios[1]
        assert standard.words_per_hour == pytest.approx(DEFAULT_WPH)
        assert standard.hours == pytest.approx(10.0)
        assert standard.runtime == "10:00:00"
        assert standard.bin_label == "10 to 20 hours"

    def test_custom_pace_scenario_appended(self):
        scenarios = pace_scenarios(90000, wph=10000)
        assert scenarios[-1].name == "custom (10,000 wph)"
        assert scenarios[-1].hours == pytest.approx(9.0)
        assert scenarios[-1].bin_label == "5 to 10 hours"

    def test_slower_pace_yields_longer_runtime(self):
        scenarios = pace_scenarios(46500)
        assert scenarios[0].hours > scenarios[-1].hours
        assert scenarios[0].bin_label == "5 to 10 hours"
        assert scenarios[-1].bin_label == "3 to 5 hours"

    def test_custom_wph_rejected(self):
        with pytest.raises(ValueError):
            pace_scenarios(1000, wph=0)


class TestBudgetComparison:
    def test_hire_costs_equal_rate_times_finished_hours(self):
        report = budget_comparison(words=93000)  # 10 finished hours
        assert report.finished_hours == pytest.approx(10.0)
        assert report.hire_cost_low == pytest.approx(10 * report.hire_rate_low)
        assert report.hire_cost_high == pytest.approx(10 * report.hire_rate_high)

    def test_diy_cost_is_fixed_plus_time_value(self):
        report = budget_comparison(
            words=93000,
            fixed_costs=250,
            self_value_per_hour=25,
            diy_hours_per_finished_hour=2.5,
        )
        assert report.diy_hours_estimate == pytest.approx(25.0)
        assert report.diy_cost_estimate == pytest.approx(250 + 25 * 25)
        assert report.diy_cost_per_finished_hour == pytest.approx(87.5)

    def test_break_evens_make_diy_match_hiring(self):
        report = budget_comparison(words=93000)
        at_low = budget_comparison(
            words=93000, self_value_per_hour=report.break_even_self_value_low
        )
        at_high = budget_comparison(
            words=93000, self_value_per_hour=report.break_even_self_value_high
        )
        assert at_low.diy_cost_estimate == pytest.approx(
            report.hire_cost_low, rel=1e-9
        )
        assert at_high.diy_cost_estimate == pytest.approx(
            report.hire_cost_high, rel=1e-9
        )

    def test_ordering_guards(self):
        with pytest.raises(ValueError):
            budget_comparison(words=93000, hire_rate_high=100, hire_rate_low=200)
        with pytest.raises(ValueError):
            budget_comparison(words=0)


def test_sum_words():
    chapters = [Chapter("a", 100), Chapter("b", 250)]
    assert sum_words(chapters) == 350
