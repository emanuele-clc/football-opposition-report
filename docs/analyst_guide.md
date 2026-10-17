# Opposition report: guide for analysts

## Run it
```
pip install -r requirements.txt
python src/oppreport.py --csv events.csv --team "Team name" --out reports
```
Open `reports/report_<Team>.html` in a browser (print to PDF from there). Details on the input in `docs/data_format.md`. With open StatsBomb data: `python src/oppreport.py --statsbomb matches/9_281.json --data-dir <data folder> --team "Bayer Leverkusen" --out reports`.

## What you get
- `report_<Team>.html`: style at a glance with intervals; sequence families (build-up and advanced) with share, profile, shot rate, per-match variation and stability; how sequence start types map to families; how much to trust the report given the number of matches.
- `restarts_<Team>.html`: one page on goal kicks, keeper distributions and throw-ins (own half and opponent half): first pass short or long, which side, how often the possession reaches the opponent half or the final third, ends in the own half or in a shot. Season with interval and last 5 matches (highlighted when outside the season interval: check on video). Every possession is in `restart_clips_<Team>.csv` with a label such as `Goal kick short left`.
- XML for video tools: add `--xml` (and `--video-offsets offsets.csv`) to get `xml/` with one file per match (Sportscode / Nacsport timeline format). Each clip starts 3 s before the possession and ends 3 s after. Not yet tested by importing into those tools: try one match first.
- `clips_<Team>.csv`: every sequence with its family, date, opponent, half, minute, second, start type, passes, duration, shot and (with offsets) video time. Filter by family to build a clip list in your video tool.
- `review_<Team>.csv` and `.html`: a sheet to check the families against video and five fixed questions. Fill the column `coherent_with_family` with yes, partly or no and run `python src/report/summarize_review.py review_<Team>.csv`.

## How to read it
- Families are numbered labels (B1, A2). They describe how this team builds up; they are not tactical categories until you name them from video.
- The families depend mostly on how the sequence starts (goal kick, throw-in, open play). That table is the most robust part.
- Stability and the structure check tell you how much to trust a partition. If the report says "slices of a continuum", treat the families as a convenient grouping.
- The families did not explain shots better than a simple rule on where the sequence ends (validated on 10 teams): use them to describe, not to predict.
- The section "How much can you trust this report?" shows how far numbers can move with few matches. With under 8 matches treat style numbers as rough; shot rate and the share of sequences starting in the own half do not separate teams reliably even with 15 matches.

## What it does not cover
Only open play with at least 3 passes. No pressing, set pieces, transitions after lost balls, individual players or off-ball positions. Tactical meaning of the families has not been validated by coaches. Data from the provider's possession identifiers give the most reliable numbers.
