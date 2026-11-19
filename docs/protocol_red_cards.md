# Red cards: do matches played with ten men change the grades? (exploratory)

Written on 19 November 2026, before any run of `src/analysis/exploratory_red_cards.py`. **Exploratory**: it checks the A-D grade against one source of noise named by the expert (call of 13 November 2026) and by the supervisor's roadmap. It does not replace the grade, its thresholds or its result file.

## Question
The grade (`docs/protocol_evidence_grade.md`) uses every match as it is. A team that plays 60 minutes with ten men (or against ten) changes its numbers for reasons that are not its style: fewer pressures, deeper defending, more or fewer shots. **Do these matches change the skill, the discrimination D or the grade of the statements?**

## What was already seen before this protocol (declared)
- The grade results on the 70 confirmatory teams (`results/evidence_grade_corrected.json`).
- No count of red cards, no per-match value split by red cards, on any team. The minutes code (`src/report/minutes.py`) was checked only for consistency (team minutes = 11 x match length minus time after own sending-offs), not on any statement value.

- On 19 November the script was run once on the 9 development teams (`results/exploratory_red_cards_dev.json`) only to check that the code runs. With 2-3 teams per league these numbers are not meaningful and were not used; nothing in this protocol was changed after that run.

## Data
The 80 extracted teams of the grade (StatsBomb 2015/16, four leagues), per-match values from `evidence_grade.py extract`, with the correction of note 1 of the grade protocol. Subjects: the 70 confirmatory teams, as in the grade. The other 10 teams stay in the league baselines, as in the grade.

## Sending-offs (fixed)
From the events, with `src/report/minutes.py`: a sending-off is a 'Red Card' or 'Second Yellow' in 'Foul Committed' or 'Bad Behaviour', of either team, in periods 1-4. Time is the real elapsed time (stoppage time counted once). **Uneven time** of a match = match length minus the elapsed time of the first sending-off.

## Two variants (fixed)
- **E, exclude:** drop every team-match with at least **15 minutes** of uneven time (from the team's series and from the league baselines). Everything else as in the grade (`analyse()` unchanged).
- **T, truncate:** for every team-match with a sending-off, recompute the per-match values (`match_values()` unchanged) on the events **before the first sending-off** only. Per-match counts (S01, P14, T18, D24, D27, D28, A29, A30, A31) get the denominator `even time / match length` instead of 1, so they stay "per full match"; the other statements are ratios and keep their own denominators. Matches whose first sending-off comes before minute 1 of elapsed time would be empty: dropped. Main-player counters (K33, K34) and sequences (F07, F08) are also cut.

## Measures
The official values are recomputed by the same script on the unchanged data and checked against `results/evidence_grade_corrected.json` (they must be equal). For each statement and each variant: skill, D, grade (same code and seeds as the grade), and the differences from the official values: Δskill, ΔD, grade changed (yes/no). Also: number of team-matches with a sending-off and with ≥ 15 uneven minutes (subjects and all 80 teams).

## Reading (fixed in advance)
- A statement is **sensitive to red cards** if its grade changes in **both** variants, or if |Δskill| > **0.05** or |ΔD| > **0.05** in variant T.
- Overall: if **at most 3** of the 34 statements are sensitive, the conclusion is "matches with ten men do not change the grades in a meaningful way; the report keeps all matches and shows which matches had a sending-off". If more, the sensitive statements are listed with both values in the app and the thesis, and the official grade stays as the reference (the protocol of the grade is not changed after the fact).

## Output
`results/exploratory_red_cards.json`: counts, per statement the official and the two variant values, flags, and the overall reading.

## Procedure
Protocol and script committed and pushed first; one run; result committed unedited. The script refuses to run if the result file exists or if the protocol or the script differ from the pushed commit.

## Known weaknesses
- 15 minutes is a convention. Shorter uneven spells stay in variant E (variant T removes them).
- Variant T keeps the team-match but with a shorter time: the per-match counts assume a constant rate over the match, which is not true (more happens late in matches).
- A sending-off is not the only in-match context (score, early goals): those belong to the context study (proposal B), not here.
- Exploratory: the same team-seasons as the grade.
