"""Core estimation math: words -> finished hours, runtime strings, bins, budget."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

#: ACX-typical narration pace: 155 words per minute * 60 = 9,300 words/hour.
DEFAULT_WPH = 9300

#: Named narrator pace scenarios, in words spoken per minute.
PACE_PRESETS: Sequence[tuple] = (
    ("slow", 150),
    ("standard", 155),
    ("brisk", 160),
    ("fast", 165),
)


def words_to_hours(words: int, wph: float = DEFAULT_WPH) -> float:
    """Convert a word count to finished-book hours at ``wph`` words per hour."""
    if wph <= 0:
        raise ValueError("words per hour must be positive")
    return words / wph


def runtime_str(hours: float) -> str:
    """Format hours as a human-friendly ``h:mm:ss`` runtime string."""
    if hours < 0 or math.isnan(hours):
        raise ValueError("hours must be a non-negative number")
    total = round(hours * 3600)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def format_int(n: float) -> str:
    """Format a number with thousands separators (e.g. 9300 -> '9,300')."""
    return f"{n:,.0f}"


# ---------------------------------------------------------------------------
# ACX-style retail-length bins
# ---------------------------------------------------------------------------

#: ACX royalty pace tiers, as (upper bound in hours, plain-language label).
BIN_TIERS: Sequence[tuple] = (
    (1.0, "Under 1 hour"),
    (3.0, "1 to 3 hours"),
    (5.0, "3 to 5 hours"),
    (10.0, "5 to 10 hours"),
    (20.0, "10 to 20 hours"),
    (math.inf, "Over 20 hours"),
)


@dataclass(frozen=True)
class LengthBin:
    """One retail-length bin, expressed in hours and in plain words."""

    label: str
    max_hours: Optional[float]  # None means "no upper bound"
    min_words: int
    max_words: Optional[int]  # None means "no upper bound"
    min_words_display: str
    max_words_display: str


def _words_display(words: Optional[int]) -> str:
    return "unbounded" if words is None else f"{format_int(words)} words"


def acx_bins(wph: float = DEFAULT_WPH) -> List[LengthBin]:
    """Return ACX-style bins with hour and plain-word boundaries at ``wph``."""
    if wph <= 0:
        raise ValueError("words per hour must be positive")
    bins: List[LengthBin] = []
    previous_max_words = 0
    for max_hours, label in BIN_TIERS:
        min_words = previous_max_words if previous_max_words == 0 else previous_max_words + 1
        if max_hours == math.inf:
            bins.append(
                LengthBin(label, None, min_words, None,
                          _words_display(min_words), _words_display(None))
            )
        else:
            max_words = math.ceil(max_hours * wph)
            bins.append(
                LengthBin(label, max_hours, min_words, max_words,
                          _words_display(min_words), _words_display(max_words))
            )
            previous_max_words = max_words
    return bins


def bin_for_hours(hours: float, wph: float = DEFAULT_WPH) -> LengthBin:
    """Return the bin a finished runtime of ``hours`` falls into."""
    if hours < 0:
        raise ValueError("hours must be non-negative")
    for bin_ in acx_bins(wph):
        if bin_.max_hours is None or hours < bin_.max_hours:
            return bin_
    raise AssertionError("unreachable: unbounded bin terminates the search")


# ---------------------------------------------------------------------------
# Narrator pace scenarios
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PaceScenario:
    """Finished-length estimate under one narrator pace."""

    name: str
    words_per_minute: int
    words_per_hour: float
    hours: float
    runtime: str
    bin_label: str


def pace_scenarios(
    words: int,
    presets: Sequence[tuple] = PACE_PRESETS,
    wph: Optional[float] = None,
) -> List[PaceScenario]:
    """Model the same manuscript across narrator pace scenarios.

    If ``wph`` is given, an additional ``custom`` scenario is appended so you
    can compare the presets against one exact pace you care about.
    """
    if wph is not None and wph <= 0:
        raise ValueError("words per hour must be positive")
    scenarios: List[PaceScenario] = []
    for name, wpm in presets:
        scenarios.append(_make_scenario(name, float(wpm) * 60.0, words))
    if wph is not None:
        scenarios.append(
            _make_scenario(f"custom ({format_int(wph)} wph)", wph, words)
        )
    return scenarios


def _make_scenario(name: str, wph: float, words: int) -> "PaceScenario":
    hours = words_to_hours(words, wph)
    return PaceScenario(
        name=name,
        words_per_minute=wph / 60.0,
        words_per_hour=wph,
        hours=hours,
        runtime=runtime_str(hours),
        bin_label=bin_for_hours(hours).label,
    )


# ---------------------------------------------------------------------------
# Per-finished-hour budget math
# ---------------------------------------------------------------------------

#: DIY overhead: retakes, pickup lines, proofing, editing, mastering, upload QA.
DEFAULT_DIY_HOURS_PER_FINISHED_HOUR = 2.5


@dataclass(frozen=True)
class BudgetReport:
    """Cost comparison between hiring a narrator and DIY production."""

    finished_hours: float
    hire_rate_low: float
    hire_rate_high: float
    hire_cost_low: float
    hire_cost_high: float
    fixed_costs: float
    self_value_per_hour: float
    diy_hours_per_finished_hour: float
    diy_hours_estimate: float
    diy_cost_estimate: float
    diy_cost_per_finished_hour: float
    break_even_self_value_low: float
    break_even_self_value_high: float


def break_even_self_value(
    finished_hours: float,
    hire_rate: float,
    fixed_costs: float = 0.0,
    diy_hours_per_finished_hour: float = DEFAULT_DIY_HOURS_PER_FINISHED_HOUR,
) -> float:
    """Hourly value of your own time at which DIY exactly matches a hire at
    ``hire_rate`` per finished hour."""
    if finished_hours <= 0:
        raise ValueError("finished hours must be positive")
    if diy_hours_per_finished_hour <= 0:
        raise ValueError("diy hours per finished hour must be positive")
    total_diy_hours = diy_hours_per_finished_hour * finished_hours
    return (hire_rate * finished_hours - fixed_costs) / total_diy_hours


def budget_comparison(
    words: int,
    wph: float = DEFAULT_WPH,
    hire_rate_low: float = 150.0,
    hire_rate_high: float = 300.0,
    fixed_costs: float = 250.0,
    self_value_per_hour: float = 25.0,
    diy_hours_per_finished_hour: float = DEFAULT_DIY_HOURS_PER_FINISHED_HOUR,
) -> BudgetReport:
    """Compare hiring (PFH rate) versus DIY (gear + your time) for a project."""
    if hire_rate_high < hire_rate_low:
        raise ValueError("high PFH rate must not be lower than the low rate")
    if wph <= 0:
        raise ValueError("words per hour must be positive")
    hours = words_to_hours(words, wph)
    if hours <= 0:
        raise ValueError("the manuscript must contain at least one word")
    diy_hours = diy_hours_per_finished_hour * hours
    diy_cost = fixed_costs + self_value_per_hour * diy_hours
    return BudgetReport(
        finished_hours=hours,
        hire_rate_low=hire_rate_low,
        hire_rate_high=hire_rate_high,
        hire_cost_low=hire_rate_low * hours,
        hire_cost_high=hire_rate_high * hours,
        fixed_costs=fixed_costs,
        self_value_per_hour=self_value_per_hour,
        diy_hours_per_finished_hour=diy_hours_per_finished_hour,
        diy_hours_estimate=diy_hours,
        diy_cost_estimate=diy_cost,
        diy_cost_per_finished_hour=diy_cost / hours,
        break_even_self_value_low=break_even_self_value(
            hours, hire_rate_low, fixed_costs, diy_hours_per_finished_hour
        ),
        break_even_self_value_high=break_even_self_value(
            hours, hire_rate_high, fixed_costs, diy_hours_per_finished_hour
        ),
    )
