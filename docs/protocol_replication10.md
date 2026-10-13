# Replication protocol on 10 teams (L2)

Written on 13 October 2026, **before** any event data of the six new teams was downloaded or analysed. Only match lists (`data_info/`) were used to draw the teams.

## Question
Does the L2 build-up result (families reproduced and predictable on held-out matches) hold in 7 or more teams out of 10, instead of 3 out of 4?

## Selection rule (fixed before the draw)
- Eligible: team-seasons of **La Liga, Serie A and Ligue 1, season 2015/2016** (full league seasons in the open data, at least 300 matches in the competition) with at least 30 available matches.
- Excluded: the four teams already analysed (Bayer Leverkusen, Leicester City, Barcelona, Arsenal).
- Stratified random draw, one seed declared here: **20261013**, `numpy.random.default_rng`, candidates sorted alphabetically. Per league: 2 primary teams and 1 reserve. One draw only, no redraw. Script: `src/week4/select_teams.py`; output: `docs/replication10_selection.json`.
- A reserve replaces a primary team **only for a technical failure**: scripts cannot run, event files missing, or fewer than 20 sequences in a phase on the exploration matches. Never because of a result.

| League | Primary | Reserve |
|---|---|---|
| La Liga | Atlético Madrid, Real Madrid | Granada |
| Serie A | Napoli, Sassuolo | AC Milan |
| Ligue 1 | Gazélec Ajaccio, Bordeaux | Olympique de Marseille |

Resulting set of 10 teams: Bayer Leverkusen (Bundesliga 2023/24), Leicester City and Arsenal (Premier League 2015/16), Barcelona, Atlético Madrid, Real Madrid (La Liga 2015/16), Napoli, Sassuolo (Serie A 2015/16), Gazélec Ajaccio, Bordeaux (Ligue 1 2015/16).

## What is frozen
Identical to `docs/protocol_replication.md`: 70/30 split by match date, phase cut x = 45, k = 5 (build-up) and k = 3 (advanced), 11 features, K-Means (n_init = 20, random_state = 0), predictability model (logistic regression, C = 0.5; inputs play pattern, minute, half, previous family), bootstrap 1000 resamples over matches (seeds 2026 and 2027), same scripts (`src/week4/validate_replication.py`). Nothing is tuned on the new teams. Runner: `src/week4/run_new_teams.py` (download, E1, validation; a team already validated is skipped, so each team is run once).

## Hypotheses per team (same as the replication protocol)
- **H1 (build-up):** out-of-sample predictability gain positive, 95% interval excluding zero.
- **H2 (build-up):** no family changes its share by more than 10 points and the frozen silhouette on held-out data is at least 0.10.
- **H3 (both phases separately):** the families carry shot information (gain in log-loss vs the exploration shot rate, 95% interval excluding zero).
- **E1 (descriptive):** build-up stability above both nulls by at least 0.10, reported but not decisive.

## Decision rule
- A team **passes** the build-up claim if H1 and H2 both pass.
- The claim **holds across teams** if at least **7 of the 10** teams pass (3 of the first 4 already pass, so at least 4 of the 6 new teams are needed). The proportion is reported with its 95% Wilson interval. Script: `src/week4/summarize_replication10.py`.
- "Families carry shot information in the build-up" holds if H3 passes in at least **6 of the 8** teams where it is tested (Barcelona, Arsenal and the six new teams). The advanced phase is reported only.
- If the rule is not met, the thesis states the result as "k teams out of 10" without a generalisation claim.
- No team is dropped, replaced for result reasons, or rerun. Result files are committed unedited. Any further analysis is labelled exploratory.

## Known weaknesses
- Nine of the ten teams are from the 2015/16 season and none is from a recent era except Leverkusen; the open data limits this.
- Teams of very different strength and style are mixed (Real Madrid, Gazélec Ajaccio); no analysis by strength is pre-registered.
- Ten teams is still a small sample; the interval for a proportion such as 8 of 10 stays wide.
- No correction for multiple comparisons: H1, H2 and H3 are tested per team.
- The threshold of 7 of 10 was chosen after seeing 3 of 4 on the first teams.
- The first four teams were chosen for data and style reasons (Leverkusen, Leicester) or by hand (Barcelona, Arsenal); only the six new ones come from the random draw.
- Stability, predictability and shot association do not show tactical meaning, and predictability comes mostly from how sequences start (exploratory result on the first four teams).
