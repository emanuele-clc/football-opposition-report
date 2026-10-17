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
- The restart sheet also draws the first pass of every goal kick and keeper distribution on a pitch (short in blue, long in orange, thick arrows = average direction) and lists who receives the first pass, when the data contain player names.
- `setpieces_<Team>.html`: corners (side, delivery zone: short, near post, centre, far post; shot after, goals, xG when available) and attacking free kicks (cross into the box, played short, direct shot), with takers and first receivers. Every set piece is in `setpiece_clips_<Team>.csv`.
- `transitions_<Team>.html`: where the team loses and wins back the ball in open play (two pitch maps), losses and recoveries per match by third, how often the ball is regained within 5 s of a loss (counter-press) and how often the opponent shoots within 10 s, shots within 10 s of a recovery, last 5 matches. Built from the order of actions, so it does not depend on the provider's possession definition. The counter-press share varied little between the teams we tested (17-19%): it describes, it does not separate styles. Every loss and recovery is in `transition_clips_<Team>.csv`.
- XML for video tools: add `--xml` (and `--video-offsets offsets.csv`) to get `xml/` with one file per match (Sportscode / Nacsport timeline format). Each clip starts 3 s before the possession and ends 3 s after. Not yet tested by importing into those tools: try one match first.
- `clips_<Team>.csv`: every sequence with its family, date, opponent, half, minute, second, start type, passes, duration, shot and (with offsets) video time. Filter by family to build a clip list in your video tool.
- `review_<Team>.csv` and `.html`: a sheet to check the families against video and five fixed questions. Fill the column `coherent_with_family` with yes, partly or no and run `python src/report/summarize_review.py review_<Team>.csv`.

## How to read it
- Families are numbered labels (B1, A2). They describe how this team builds up; they are not tactical categories until you name them from video.
- The families depend mostly on how the sequence starts (goal kick, throw-in, open play). That table is the most robust part.
- Stability and the structure check tell you how much to trust a partition. The report's structure check uses the whole season and fewer resamples than the thesis test, so it can differ from the thesis figure (clear structure in 4 of 10 teams on exploration matches; the report says 'clear structure' for 5 of 10). If the report says "slices of a continuum", treat the families as a convenient grouping.
- The families did not explain shots better than a simple rule on where the sequence ends (validated on 10 teams): use them to describe, not to predict.
- The section "How much can you trust this report?" shows how far numbers can move with few matches. With under 8 matches treat style numbers as rough; shot rate and the share of sequences starting in the own half do not separate teams reliably even with 15 matches.

## What it does not cover
Only open play with at least 3 passes. No pressing, set pieces, transitions after lost balls, individual players or off-ball positions. Tactical meaning of the families has not been validated by coaches. Data from the provider's possession identifiers give the most reliable numbers.
