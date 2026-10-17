# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Delegated (confirmed 17 Oct 2026): FastAPI backend that runs/serves the existing Python pipeline outputs (the JSON and CSV files written by `src/oppreport.py` and `src/report/*.py`), plus a Vite + React frontend with hand-built SVG charts. Frontend and backend are connected, not two separate deliverables. Runs locally only (owner's Windows PC, Python 3.13, `python -X utf8`), started with one command. Not deployed online: StatsBomb Open Data is under a non-commercial licence and raw data stays local.

Why this choice: the pipeline is already Python and writes JSON per team, so an API over those files reuses it unchanged; React + custom SVG gives full control over the visualisation, which a Streamlit/Dash look would not.

The existing static HTML sheets (`report_`, `prep_`, `restarts_`, `setpieces_`, `transitions_`, `review_`) remain as printable outputs of the pipeline.

## Users

Primary: a club video/match analyst preparing the next match against an opponent. They read fast, want the main facts first, filter sequences into clip lists for their video tool (Sportscode/Nacsport), and print a page for staff.

Secondary: the thesis professor (Prof. Pichler) and examiners, who see the prototype through the analyst's eyes during the presentation (21 Oct 2026) and evaluate whether it is honest about what the method can and cannot show.

## Product Purpose

Automated opposition report from event data: given a team's matches, describe how it builds up (sequence families B1.., A1..), how it restarts (goal kicks, keeper, throw-ins), its set pieces (corners, free kicks) and transitions (losses, recoveries, counter-press), with intervals, reference-team ranks, and "how much can you trust this" warnings. Every number links back to the individual sequences so the analyst can check them on video.

Success: an analyst can go from "next opponent" to the key facts, the supporting clips and an export for the video tool, and understands at each step how reliable the number is. Part of a master's thesis ("Automated Football Opposition Report", UNICAL / FH OÖ Hagenberg).

## Positioning

A report that states its own uncertainty. Every figure comes with an interval, a per-match variation, a rank against reference teams or a sample-size warning, and the method's negative results are declared (families are weak structure, "slices of a continuum"; they do not beat a one-variable end-position rule for shots). Results come from pre-registered protocols on held-out matches and are reproducible from a clean clone.

## Operating Context

- Used on screen (laptop) during preparation, printed / saved as PDF for staff (the prep page is one A4 page), and projected in presentations and demos.
- Inputs: StatsBomb Open Data (`--statsbomb`) or any provider's events converted to the generic CSV format (`src/adapters/generic_csv.py`, `docs/data_format.md`). Optional video offsets file maps match time to video time.
- Outputs the analyst takes away: clip CSVs per sheet, Sportscode/Nacsport-style XML per match (`--xml`), review sheet (`review_<Team>.csv`, five fixed questions).
- Reference set: the 10 thesis teams (Leverkusen 23/24; Leicester, Arsenal, Barcelona, Atlético, Real Madrid, Napoli, Sassuolo, Gazélec Ajaccio, Bordeaux 15/16).

## Capabilities and Constraints

- Open play sequences with at least 3 passes; two phases: build-up (start x < 45, k = 5) and advanced (x >= 45, k = 3). Families are numbered labels (B1, A2), never tactical names until an analyst names them from video.
- Terminology to keep: family, build-up, advanced, share, shot rate, stability, structure check, start type, gain, held-out.
- Numbers, cautionary sentences and labels produced by the pipeline must not be changed, rounded differently or softened by the interface. Design never adds claims (see CLAUDE.md section 7).
- Team names contain accents (Atlético, Gazélec); everything must handle UTF-8.
- Not covered: pressing, off-ball positions, individual player evaluation. Counter-press share does not separate styles (17-19% for all teams tested).
- Open: L3 corner analysis direction (to decide with the professor). XML import never tested in a real video tool.

## Brand Commitments

- Name: "Automated Football Opposition Report" (thesis title); tool entry point `oppreport`.
- Voice: plain, direct, honest English for the interface; no hype, no "AI" framing. Cautions are stated, not hidden.
- Binding direction from the owner: the visualisation must be genuinely well designed, explicitly "no AI slop".
- Data attribution: cite StatsBomb (licence requirement).

## Evidence on Hand

- Example outputs for Leverkusen, Leicester, Barcelona, Arsenal in `examples/` (HTML, JSON, clip CSVs, review sheets).
- All result JSONs in `results/`; protocols in `docs/`; analyst guide `docs/analyst_guide.md`.
- Reproducibility check: `tests/reproduce_results.py` (41/41 files identical).
- Absent, must not be fabricated: any real club data, any analyst review or feedback, any club using the tool, any time-saving claim, testimonials or users.

## Product Principles

1. Honesty over impressiveness: uncertainty, sample-size limits and negative results are part of the interface, never footnotes to hide.
2. Every number is traceable to sequences and clips the analyst can watch.
3. Main facts first, detail on demand: the analyst's prep time is short.
4. Description, not prediction: families describe how a team plays; the product never implies they predict outcomes.
5. Local and reproducible: same inputs, same outputs; no data leaves the machine.

## Accessibility & Inclusion

Inferred from the confirmed use (print + projector), not yet confirmed by the owner: pages should print legibly in black and white and project well; charts should not rely on colour alone to distinguish families or categories.
