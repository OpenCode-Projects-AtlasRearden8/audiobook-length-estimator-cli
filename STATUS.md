# STATUS — audiobook-length-estimator

**Date:** 2026-10-31
**Owner:** Asdale Dynamics, LLC (Dylan Asdale)
**Status:** v0.1.0 — working, tested, committed locally

## What was built

A pure-stdlib Python CLI that sizes an audiobook before recording starts:

- `audiobook-estimator book <sources>` — per-chapter and whole-book finished-hour
  estimates from manuscript files (`.txt`, `.md`, `.markdown`, `.rst`, `.rtf`)
  and/or inline word-count tokens (`"Chapter 1=5400"`, `5400`), at an adjustable
  words-per-finished-hour pace (`--wph`, default 9,300 ≈ 155 spoken words/min).
- `audiobook-estimator scenarios <sources> [--wph N]` — narrator pace scenarios
  (slow 150 / standard 155 / brisk 160 / fast 165 wpm, plus one custom pace),
  showing how runtime and retail bin shift.
- `audiobook-estimator bins [--wph N] [--words W]` — ACX-style retail-length
  bins ("1 to 3 hours", "5 to 10 hours", …) with boundaries expressed in plain
  words, plus "which bin does this word count land in".
- `audiobook-estimator budget <sources>` — per-finished-hour (PFH) budget math:
  hiring cost range ("--rate-low/--rate-high") versus DIY (fixed gear/software +
  your time at "--self-value" over "--diy-hours" per finished hour), DIY cost
  per finished hour, break-even value of your own time, and a plain-English
  verdict.

Every subcommand supports `--json` for machine-readable output. Errors are
clean argparse messages with exit code 2.

Structure: `src/audiobook_length_estimator/` (`estimator.py` math,
`manuscript.py` sources/word counting, `cli.py` argparse UI, `__main__.py`)
wrapped in `pyproject.toml` with the `audiobook-estimator` console script.
Ships with `tests/` (58 tests) including two original sample manuscripts under
`tests/data/`. Package init, LICENSE, README credited per company style.

## How to run it

```bash
python -m venv .venv
.venv/bin/pip install '.[dev]'
.venv/bin/audiobook-estimator book chapter01.txt "Author note=1800"
.venv/bin/audiobook-estimator scenarios manuscript.txt
.venv/bin/audiobook-estimator bins --words 92000
.venv/bin/audiobook-estimator budget manuscript.txt --rate-low 150 --rate-high 300
.venv/bin/python -m pytest
```

(Plain `pip install .` works outside the externally-managed-Python case; the
venv path above is what was verified in this environment.)

## Verification results

- `python -m pytest` — **58 passed**, 0 failed.
- Smoke-tested all four subcommands in table and JSON modes, plus `--version`
  and error paths (missing file, bad token, inverted rate range → clean
  argparse errors, non-zero exit).
- `py_compile` clean on all source and test files.
- Hand-checked facts: 93,000 words → 10:00:00 at 9,300 WPH; bins at 9,300 WPH
  are 0–9,300 / 9,301–27,900 / 27,901–46,500 / 46,501–93,000 / 93,001–186,000 /
  186,001+ words; break-even math reconciles exactly with DIY = hire cost.

## Known gaps

- Estimates model narration pace only; they do not account for retail
  distance differences per retailer (bins are ACX-style tiers, not an ACX
  guarantee).
- DIY overhead uses a single flat multiplier (default 2.5 hours per finished
  hour); real projects vary with experience, retake rate, and mastering depth.
- Word counting is whitespace-based: directories of PDFs, OCR noise, tables,
  or front matter are not specially parsed.
- No `books.json`/project-file persistence, no export beyond `--json`.
- No localization/currency formatting beyond USD defaults ("$" prefix).
