# Analyst review kit

Purpose: get one structured opinion from a person with football analysis experience on (1) whether the sequence families match what they see, and (2) whether the report would be useful before a match. It is the only external check the thesis does not have yet. Commit this file before the first review so that the procedure is fixed in advance.

## Who
One or more people with practical experience: a club or academy video analyst, a coach with a UEFA licence, or a performance-analysis student with match-preparation experience. Record their role and years of experience (not their name, unless they agree). LASK Linz only with the professor's consent.

## Format (30 minutes, in person or screen share)
The reviewer does not install anything: you run the app on your PC (`powershell -ExecutionPolicy Bypass -File .\start_app.ps1`) and share the screen.
1. **5 min — context.** Read the paragraph in "What to say" below. Do not explain what the families "mean": let the reviewer judge.
2. **5 min — Overview of one team** they know (preferably a team they have watched: Bayer Leverkusen 2023/24 or a 2015/16 team). Let them look; note spontaneous comments word for word.
3. **15 min — Review tab.** For each of the 24 sequences (3 per family): play the replay, and the video if available, then ask "Does this sequence fit the family it was assigned to?" (yes / partly / no). For partly and no, write what does not fit. Do not suggest answers.
4. **5 min — Part 2.** Ask the five fixed questions in the order shown, read aloud, and write the answers in their words.
Click **Save review**: the app writes `review_<Team>_filled.csv` and `review_<Team>_answers.json` in the data folder; the original sheet is not changed.

## What to say (read aloud, same for every reviewer)
"This is a prototype from my master's thesis. It groups a team's open-play possessions into numbered families (B1, B2…) automatically from event data. I want to know whether the grouping makes sense to someone who analyses football, and whether you would use anything like this. There are no right answers; negative comments are as useful as positive ones."

## The five questions (fixed; same as review_<Team>.html)
1. Does this description match what you know about this team? What is right and what is wrong?
2. Which parts would you use before a match and which would you skip?
3. What is missing that you would need?
4. Do the reliability notes change how you read the report?
5. How long would it take you to get the same overview from video, and would this report shorten it?

## After the review
```powershell
python -X utf8 src\report\summarize_review.py <data_folder>\review_<Team>_filled.csv --out results\analyst_review_<Team>_<n>.json
```
Report per family the share of yes or partly, all "no" comments, and the five answers verbatim. With 3 sequences per family this is descriptive, not an estimate. Do not change the families, the report or the questions between reviewers.

## Message to ask someone (Italian)
"Ciao, sto finendo una tesi magistrale su un report automatico dell'avversario costruito su dati evento. Mi servirebbero 30 minuti di una persona che fa analisi video o allena, per guardare insieme alcune azioni e dirmi se il raggruppamento ha senso e se uno strumento così sarebbe utile. Nessuna preparazione richiesta, lo facciamo anche in videochiamata. Ti andrebbe?"

## Message to ask someone (English)
"Hi, I am finishing a master's thesis on an automated opposition report built from event data. I would need 30 minutes of someone who does video analysis or coaching, to look at a few possessions together and tell me whether the grouping makes sense and whether such a tool would be useful. No preparation needed; a video call is fine. Would you be up for it?"
