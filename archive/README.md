# archive/

Code that was run once and is not needed to redo the thesis numbers. Kept so every result can still be traced to its code.
Moved here on 6 November 2026 (XML export and the local-model brief later the same day, to keep the thesis to its questions); the code is the same as before (checked where possible: same output files).

| file | what it did | result |
|---|---|---|
| `choose_k.py` | choice of the number of families k on the exploration matches (10 Oct 2026) | `results/k_selection_Bayer_Leverkusen.json` (rerun 6 Nov: identical) |
| `select_and_replicate.py` | draw of the 6 new teams (seed 20261013) and first run of the 10-team replication (13 Oct 2026) | `docs/replication10_selection.json` (rerun 6 Nov: identical), `results/holdout_*.json` |
| `smoke_grade.py` | smoke tests of the evidence grade before the protocols (counts only, no values) | none |
| `evidence_provider.py` | grade labels on the same 36 Barcelona matches in StatsBomb and Wyscout (20 Oct 2026) | `results/evidence_provider_Barcelona.json` |
| `exploratory_provider_samematch.py` | values on the same 36 Barcelona matches in both providers (18 Oct 2026) | `results/exploratory_provider_samematch_Barcelona.json` |
| `clips_to_mp4.py` | cuts MP4 clips from a match video (not used by the report or the app) | none |
| `clips_to_xml.py` | clip list -> Sportscode/Nacsport-style XML (was `oppreport.py --xml` and a button in the app; never tested in a real video tool) | none |
| `ai_brief.py` | coach brief written by a local language model (Ollama) from the game-plan hints (was in the app) | none |

Note: until 6 Nov 2026 `evidence_provider.py` and `exploratory_provider_samematch.py` (and `evidence_grade.py extract`) stopped at start because `src/report/defending.py` read the match file when imported; fixed that day, but these two were not rerun.
