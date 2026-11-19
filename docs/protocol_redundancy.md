# Fewer variables: which statements say the same thing? (exploratory)

Written on 19 November 2026, before any run of `src/analysis/exploratory_redundancy.py`. **Exploratory**. It answers the expert's request (call of 13 November 2026, "fewer variables, but each one explainable") with a fixed rule, so the choice of what to keep is not made by hand after looking at the teams.

## Question
The report has 34 types of statement. Some may measure the same thing twice (for example shots conceded and xG conceded). **Which statements are redundant, and which small core set is left once redundant and weak ones are set aside?**

## What was already seen before this protocol (declared)
- The grade results (skill, D, grade per statement) on the 70 confirmatory teams, and the matches needed (`results/exploratory_trust_n.json`).
- No correlation between statements was computed on any team. Some pairs are expected to be related by construction (D27-D28, A29-A30, D24-D25, T18-T19): stated here, the rule below is applied to them like to every other pair.

- On 19 November the script was run once on the 9 development teams (`results/exploratory_redundancy_dev.json`) only to check that the code runs. With 2-3 teams per league these numbers are not meaningful and were not used; nothing in this protocol was changed after that run.

## Data
The 70 confirmatory teams with the correction of note 1, per-match values from the grade extraction. Season value of a statement for a team = sum of numerators / sum of denominators (as in the grade). The 30 scalar statements (S01-S06, R09-R13, P14-P17, T18-T22, D23-D28, A29-A32). F07, F08 (family shares, different families per team) and K33, K34 (main player) are left out: one number per team does not exist in the same sense.

## Measures (fixed)
1. **League-standardised values:** within each league, subtract the league mean and divide by the league standard deviation of the season values (so that league differences do not create correlations).
2. **Correlation** between every pair of statements: Spearman rank correlation over the 70 teams, with a 95% interval from 2000 bootstrap draws of teams (seed 19).
3. **Redundant pair:** |rho| ≥ **0.80**.
4. **Groups:** statements joined by redundant pairs (connected components). In each group **one statement is kept**: best grade (A > B > C > D), then higher skill, then higher D. The others are labelled "redundant with <kept one>".
5. **Proposed core set:** kept statements with grade A or B. **Secondary (only as a hint):** kept statements with grade C. **Set aside:** grade D, and every redundant statement.

## Output
`results/exploratory_redundancy.json`: the correlation matrix, the redundant pairs with intervals, the groups, the label of each statement (core / secondary / set aside, with the reason) and the size of the core set.

## Procedure
Protocol and script committed and pushed first; one run; result committed unedited. The app may mark statements with this label; it does not delete any section.

## Known weaknesses
- Correlation across teams says two numbers rank teams the same way; it does not say they mean the same thing tactically (an analyst may still want both).
- 0.80 is a convention. Pairs between 0.60 and 0.80 are listed as "related" without consequences.
- 70 teams of one season (2015/16): another season may give other pairs.
- The rule prefers the better grade, so the core set inherits the limits of the grade.
