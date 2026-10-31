"""audiobook-length-estimator: size an audiobook before anyone hits record.

Pure standard library, offline. Estimate finished hours per chapter and for
the whole book from word counts or manuscript files, model narrator pace
scenarios, map runtimes to ACX-style retail-length bins in plain words, and
run per-finished-hour budget math comparing DIY narration against hiring.

Copyright (c) 2026 Asdale Dynamics, LLC. MIT License.
"""

from .estimator import (
    DEFAULT_WPH,
    PACE_PRESETS,
    acx_bins,
    bin_for_hours,
    budget_comparison,
    break_even_self_value,
    pace_scenarios,
    runtime_str,
    words_to_hours,
)
from .manuscript import Chapter, build_chapters, count_words

__all__ = [
    "DEFAULT_WPH",
    "PACE_PRESETS",
    "Chapter",
    "acx_bins",
    "bin_for_hours",
    "break_even_self_value",
    "budget_comparison",
    "build_chapters",
    "count_words",
    "pace_scenarios",
    "runtime_str",
    "words_to_hours",
]

__version__ = "0.1.0"
