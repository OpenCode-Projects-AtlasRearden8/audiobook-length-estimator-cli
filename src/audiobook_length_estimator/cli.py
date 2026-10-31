"""Command-line interface for the audiobook-length-estimator."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import List, Optional

from . import __version__
from .estimator import (
    DEFAULT_WPH,
    PACE_PRESETS,
    acx_bins,
    bin_for_hours,
    budget_comparison,
    pace_scenarios,
    runtime_str,
    words_to_hours,
)
from .manuscript import build_chapters, sum_words


def _add_wph_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--wph",
        type=float,
        default=DEFAULT_WPH,
        metavar="WORDS",
        help=(
            "narrator speed in words per finished hour (default: "
            f"{DEFAULT_WPH:,.0f}, i.e. about 155 spoken words/min)"
        ),
    )


def _add_sources_arg(parser: argparse.ArgumentParser, help_text: str) -> None:
    parser.add_argument(
        "sources",
        nargs="+",
        metavar="SOURCE",
        help=help_text,
    )


def _add_json_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable JSON instead of a table",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audiobook-estimator",
        description=(
            "Size an audiobook before anyone hits record: finished hours per "
            "chapter and for the whole book, pace scenarios, ACX-style "
            "retail-length bins in plain words, and DIY-vs-hiring budget math."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    book = sub.add_parser(
        "book",
        help="estimate finished hours per chapter and for the whole book",
        description=(
            "Estimate finished-book runtimes from manuscripts or inline word "
            "counts. Supply chapter files and/or word-count tokens such as "
            "'Chapter 1=5400'."
        ),
    )
    _add_sources_arg(
        book,
        help_text=(
            "manuscript files (.txt/.md/...) or word-count tokens like "
            "'Chapter 1=5400' or '5400'"
        ),
    )
    _add_wph_arg(book)
    _add_json_arg(book)

    scenarios = sub.add_parser(
        "scenarios",
        help="compare narrator pace scenarios for the whole manuscript",
        description=(
            "Model the same manuscript at slow/standard/brisk/fast narrator "
            "paces (plus an optional custom words-per-hour) and see how the "
            "finished runtime and retail bin shift."
        ),
    )
    _add_sources_arg(
        scenarios,
        help_text=(
            "manuscript files or word-count tokens; multiple sources are merged"
        ),
    )
    scenarios.add_argument(
        "--wph",
        type=float,
        default=None,
        metavar="WORDS",
        help=(
            "add one custom-pace scenario in words per finished hour "
            f"(presets span 9000-9900; standard {DEFAULT_WPH:,.0f})"
        ),
    )
    _add_json_arg(scenarios)

    bins = sub.add_parser(
        "bins",
        help="show ACX-style retail-length bins in hours and plain words",
        description=(
            "Print the ACX-style retail-length tiers with their hour and "
            "plain-word boundaries at your narrator's pace, so you can talk "
            "about book length in words rather than studio hours."
        ),
    )
    _add_wph_arg(bins)
    bins.add_argument(
        "--words",
        type=int,
        default=None,
        metavar="WORDS",
        help="optionally identify which bin a word count falls into",
    )
    _add_json_arg(bins)

    budget = sub.add_parser(
        "budget",
        help="per-finished-hour budget math: DIY versus hiring",
        description=(
            "Compare hiring a narrator (per-finished-hour rate) against DIY "
            "production (gear, software, and the value of your own time), "
            "including the break-even value of your hours."
        ),
    )
    _add_sources_arg(
        budget,
        help_text=(
            "manuscript files or word-count tokens; multiple sources are merged"
        ),
    )
    _add_wph_arg(budget)
    budget.add_argument(
        "--rate-low",
        type=float,
        default=150.0,
        metavar="USD",
        help="low-end quoted rate per finished hour (default: 150)",
    )
    budget.add_argument(
        "--rate-high",
        type=float,
        default=300.0,
        metavar="USD",
        help="high-end quoted rate per finished hour (default: 300)",
    )
    budget.add_argument(
        "--fixed-costs",
        type=float,
        default=250.0,
        metavar="USD",
        help=(
            "one-time DIY spend: microphone, interface, software, mastering "
            "(default: 250)"
        ),
    )
    budget.add_argument(
        "--self-value",
        type=float,
        default=25.0,
        metavar="USD",
        help="what an hour of your own time is worth to you (default: 25)",
    )
    budget.add_argument(
        "--diy-hours",
        type=float,
        default=2.5,
        metavar="MULT",
        help=(
            "DIY wall-clock hours per finished hour for retakes, proofing, "
            "editing, mastering (default: 2.5)"
        ),
    )
    _add_json_arg(budget)

    return parser


def cmd_book(args: argparse.Namespace) -> int:
    chapters = build_chapters(args.sources)
    rows = []
    for chapter in chapters:
        hours = words_to_hours(chapter.words, args.wph)
        rows.append(
            {
                "title": chapter.title,
                "words": chapter.words,
                "hours": round(hours, 2),
                "runtime": runtime_str(hours),
            }
        )
    total_words = sum(ch.words for ch in chapters)
    total_hours = words_to_hours(total_words, args.wph)
    total_bin = bin_for_hours(total_hours, args.wph)
    summary = {
        "title": "Whole book",
        "words": total_words,
        "hours": round(total_hours, 2),
        "runtime": runtime_str(total_hours),
        "bin": total_bin.label,
        "words_per_hour": args.wph,
    }
    if args.json:
        print(json.dumps({"chapters": rows, "summary": summary}, indent=2))
        return 0

    width = max(len(row["title"]) for row in rows) if rows else 10
    width = max(width, len("Whole book"))
    print(f"{'Chapter':<{width}}  {'Words':>10}  {'Runtime':>9}  {'Hours':>7}")
    print(f"{'-' * width}  {'-' * 10}  {'-' * 9}  {'-' * 7}")
    for row in rows:
        print(
            f"{row['title']:<{width}}  {row['words']:>10,}  "
            f"{row['runtime']:>9}  {row['hours']:>7.2f}"
        )
    print(f"{'-' * width}  {'-' * 10}  {'-' * 9}  {'-' * 7}")
    print(
        f"{summary['title']:<{width}}  {summary['words']:>10,}  "
        f"{summary['runtime']:>9}  {summary['hours']:>7.2f}"
    )
    print(
        f"\nAt {args.wph:,.0f} words per finished hour: "
        f"{summary['runtime']} total, '{total_bin.label}' retail bin "
        f"({total_bin.min_words_display} to {total_bin.max_words_display})."
    )
    return 0


def cmd_scenarios(args: argparse.Namespace) -> int:
    chapters = build_chapters(args.sources)
    words = sum_words(chapters)
    scenarios = pace_scenarios(words, PACE_PRESETS, args.wph)
    payload = [
        {
            "name": s.name,
            "words_per_minute": round(s.words_per_minute, 1),
            "words_per_hour": s.words_per_hour,
            "hours": round(s.hours, 2),
            "runtime": s.runtime,
            "bin": s.bin_label,
        }
        for s in scenarios
    ]
    if args.json:
        print(json.dumps({"words": words, "scenarios": payload}, indent=2))
        return 0

    print(f"Manuscript: {words:,} words\n")
    print(
        f"{'Scenario':<24} {'Words/min':>9}  {'Words/hour':>10}  "
        f"{'Runtime':>9}  {'Hours':>7}  Retail bin"
    )
    print(f"{'-' * 24}  {'-' * 9}  {'-' * 10}  {'-' * 9}  {'-' * 7}  {'-' * 13}")
    for s in payload:
        print(
            f"{s['name']:<24} {s['words_per_minute']:>9,.1f}  "
            f"{s['words_per_hour']:>10,.0f}  {s['runtime']:>9}  "
            f"{s['hours']:>7.2f}  {s['bin']}"
        )
    return 0


def cmd_bins(args: argparse.Namespace) -> int:
    bins = acx_bins(args.wph)
    located = None
    if args.words is not None:
        hours = words_to_hours(args.words, args.wph)
        located = bin_for_hours(hours, args.wph)
    payload = [
        {"bin": b.label, "max_hours": b.max_hours, "min_words": b.min_words,
         "max_words": b.max_words, "display": f"{b.min_words_display} to {b.max_words_display}"}
        for b in bins
    ]
    if args.json:
        out = {"words_per_hour": args.wph, "bins": payload}
        if located is not None:
            out["located"] = {"words": args.words, "bin": located.label}
        print(json.dumps(out, indent=2))
        return 0

    print(f"ACX-style retail-length bins at {args.wph:,.0f} words/hour:\n")
    print(f"{'Retail bin':<19} {'Bound in plain words':>42}")
    print(f"{'-' * 19}  {'-' * 42}")
    for entry in payload:
        print(f"{entry['bin']:<19} {entry['display']:>42}")
    if located is not None:
        print(
            f"\n{args.words:,} words lands in: {located.label} "
            f"({located.min_words_display} to {located.max_words_display})."
        )
    return 0


def cmd_budget(args: argparse.Namespace) -> int:
    chapters = build_chapters(args.sources)
    words = sum_words(chapters)
    report = budget_comparison(
        words=words,
        wph=args.wph,
        hire_rate_low=args.rate_low,
        hire_rate_high=args.rate_high,
        fixed_costs=args.fixed_costs,
        self_value_per_hour=args.self_value,
        diy_hours_per_finished_hour=args.diy_hours,
    )
    payload = asdict(report)
    if args.json:
        print(json.dumps({"words": words, **payload}, indent=2))
        return 0

    print(f"Manuscript: {words:,} words  |  {report.finished_hours:.2f} finished "
          f"hours ({runtime_str(report.finished_hours)}) at "
          f"{args.wph:,.0f} words/hour\n")
    print("Hiring a narrator (per finished hour):")
    print(f"  PFH rate range      ${report.hire_rate_low:>8,.2f} - "
          f"${report.hire_rate_high:,.2f}")
    print(f"  Total hire cost     ${report.hire_cost_low:>8,.2f} - "
          f"${report.hire_cost_high:,.2f}")
    print("\nDIY production (your voice, your hours):")
    print(f"  Fixed gear/software ${report.fixed_costs:>8,.2f}")
    print(f"  Your wall hours     {report.diy_hours_estimate:>8,.1f} "
          f"({report.diy_hours_per_finished_hour:.1f} hours per finished hour)")
    print(f"  Your time value     ${report.self_value_per_hour:>8,.2f} per hour")
    print(f"  Total DIY cost      ${report.diy_cost_estimate:>8,.2f} "
          f"(≈ ${report.diy_cost_per_finished_hour:,.2f} per finished hour)")
    print("\nBreak-even value of your own time:")
    print(f"  vs low PFH rate     ${report.break_even_self_value_low:>8,.2f} per hour")
    print(f"  vs high PFH rate    ${report.break_even_self_value_high:>8,.2f} per hour")
    if report.diy_cost_estimate < report.hire_cost_low:
        verdict = (f"DIY estimates cheaper than hiring at these inputs, but only "
                   f"if your time is worth less than "
                   f"${report.break_even_self_value_low:,.2f}/hour.")
    elif report.diy_cost_estimate > report.hire_cost_high:
        verdict = ("Hiring estimates cheaper than DIY at these inputs, and DIY "
                   "costs you real studio hours instead of money up front.")
    else:
        verdict = ("DIY falls between the hiring quotes at these inputs; shop "
                   "quotes and decide how much your time is worth.")
    print(f"\nBottom line: {verdict}")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "book": cmd_book,
        "scenarios": cmd_scenarios,
        "bins": cmd_bins,
        "budget": cmd_budget,
    }
    try:
        return handlers[args.command](args)
    except (ValueError, FileNotFoundError, OSError) as exc:
        parser.error(str(exc))
    return 1
