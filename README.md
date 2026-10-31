# audiobook-length-estimator

Size an audiobook **before anyone hits record**. Feed it chapter word counts or
manuscript text files and it estimates finished hours per chapter and for the
whole book at an adjustable words-per-hour pace, models narrator pace
scenarios, maps runtimes to ACX-style retail-length bins **in plain words**, and
runs per-finished-hour budget math comparing DIY narration against hiring a
narrator.

Pure Python standard library, fully offline, no accounts, no secrets.
Complements the [audiobook-recording-handbook](https://github.com/dylanasdale/audiobook-recording-handbook).

Like everything from [Asdale Dynamics, LLC](https://dylanasdale.github.io), it
explains the numbers like a friend would: plain English, step by step, never
condescending.

## Install

```bash
python -m pip install .
```

That gives you the `audiobook-estimator` command. You can also run it straight
from the source tree with `python -m audiobook_length_estimator`.

## How the numbers work

- **Words per finished hour (WPH):** ACX-typical narration runs about
  **155 spoken words per minute ≈ 9,300 words/hour**. Slower, warmer reads land
  near 9,000; brisk narrators push past 9,900.
- **Retail-length bins:** ACX sells audiobooks in runtime tiers (“1 to 3
  hours”, “5 to 10 hours”, …). This tool converts those hour boundaries into
  **plain word counts** so you can talk about length before recording starts.
- **DIY vs hiring:** hiring is priced per finished hour (PFH). DIY costs are
  mostly *your* hours — retakes, proofing, editing, mastering — plus some
  one-time gear/software spend. The tool computes both and shows the
  break-even value of your own time.

## Usage

### Estimate the whole book, chapter by chapter

```bash
audiobook-estimator book chapter01.txt chapter02.txt "Author note=1800"
```

Each source becomes a chapter row: either a manuscript file (`.txt`, `.md`,
`.markdown`, `.rst`, `.rtf`) or an inline word-count token
(`"Title=5400"` or bare `5400`).

Sample output:

```
Chapter             Words    Runtime   Hours
chapter-01         21,400    2:18:04    2.30
chapter-02         18,900    2:01:56    2.03
Author note         1,800    0:11:37    0.19
-----------------------------------------------------
Whole book         42,100    4:31:37    4.53

At 9,300 words per finished hour: 4:31:37 total, '3 to 5 hours' retail bin (46,500 words to 93,000 words).
```

Adjust the pace with `--wph` (words per finished hour), and get JSON with
`--json`:

```bash
audiobook-estimator book manuscript.txt --wph 9000 --json
```

### Model narrator pace scenarios

```bash
audiobook-estimator scenarios manuscript.txt
audiobook-estimator scenarios manuscript.txt --wph 9600
```

Compares slow (150 wpm), standard (155), brisk (160), and fast (165) narrator
paces side by side, showing how runtime and retail bin shift — plus your custom
pace if you pass `--wph`.

### Retail-length bins in plain words

```bash
audiobook-estimator bins                     # table at the standard pace
audiobook-estimator bins --wph 9000          # at a custom pace
audiobook-estimator bins --words 92000       # which bin does 92,000 words land in?
```

Example (`--words 92000` at 9,300 words/hour):

```
92,000 words lands in: 5 to 10 hours (46,500 words to 93,000 words).
```

### DIY versus hiring: per-finished-hour budget math

```bash
audiobook-estimator budget manuscript.txt \
  --rate-low 150 --rate-high 300 \
  --fixed-costs 250 --self-value 25 --diy-hours 2.5
```

- `--rate-low` / `--rate-high`: the per-finished-hour (PFH) rates you're
  quoted.
- `--fixed-costs`: one-time DIY spend — mic, interface, software, mastering.
- `--self-value`: what an hour of your own time is worth to you.
- `--diy-hours`: DIY wall-clock hours per finished hour (retakes, proofing,
  editing, mastering, upload QA; default 2.5).

The report shows total hire cost, total DIY cost (with a per-finished-hour
equivalent), and the **break-even value of your own time** — below it, DIY
pencils out; above it, hiring pays for itself.

## Tests

```bash
python -m pip install .[dev]
python -m pytest
```

The suite ships with small original sample manuscripts and covers the math
(hours, runtimes, bins, break-evens), source parsing (files and inline tokens),
every CLI subcommand (table and JSON output), and error cases.

## Design notes

- **Local-first and private:** everything runs on your machine; no network
  calls, no telemetry, no personal data.
- **Estimates are estimates:** production realities (retakes, music, scripting
  pronunciation notes) change runtimes. Use the numbers for planning, not
  contracts.
- **Default assumptions:** 9,300 WPH standard pace, 2.5 DIY hours per finished
  hour, and `StdOut` tables you can pipe anywhere.

## Author

Built by [Dylan Asdale](https://dylanasdale.github.io) and published by
**Asdale Dynamics, LLC** — beginner-friendly AI education, author tools, and
practical software. MIT licensed; see [LICENSE](LICENSE).
