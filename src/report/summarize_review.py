"""Riassume una o piu' schede di revisione compilate da un analista (review_<Squadra>.csv, colonna coherent_with_family = yes / partly / no).
Uso:  python summarize_review.py review_Barcelona.csv [altre schede ...] [--out riepilogo.json]
Stampa per famiglia e in totale quante sequenze l'analista giudica coerenti. Descrittivo: con 3 sequenze per famiglia non e' una stima precisa."""
import sys, json
import pandas as pd
VAL = {"yes": "yes", "y": "yes", "si": "yes", "sì": "yes", "partly": "partly", "in parte": "partly", "p": "partly", "no": "no", "n": "no"}
a = sys.argv[1:]; out = a[a.index("--out") + 1] if "--out" in a else None; files = [x for i, x in enumerate(a) if not x.startswith("--") and (i == 0 or a[i - 1] != "--out")]
if not files: sys.exit(__doc__)
d = pd.concat([pd.read_csv(f, encoding="utf-8").assign(sheet=f) for f in files], ignore_index=True)
d["answer"] = d.coherent_with_family.astype(str).str.strip().str.lower().map(VAL)
bad = d[d.coherent_with_family.notna() & d.answer.isna()]
if len(bad): print(f"ATTENZIONE: {len(bad)} risposte non riconosciute (usa yes / partly / no): {sorted(bad.coherent_with_family.astype(str).unique())}")
filled = d[d.answer.notna()]; print(f"{len(files)} schede, {len(d)} sequenze, compilate {len(filled)}, vuote {d.coherent_with_family.isna().sum()}\n")
if not len(filled): sys.exit("Nessuna risposta: compila la colonna coherent_with_family.")
t = pd.crosstab(filled.family, filled.answer).reindex(columns=["yes", "partly", "no"], fill_value=0); t["n"] = t.sum(1); t["yes_or_partly"] = (t.yes + t.partly) / t.n
print(t.to_string(formatters={"yes_or_partly": "{:.0%}".format}))
tot = filled.answer.value_counts().reindex(["yes", "partly", "no"], fill_value=0)
print(f"\nTotale: yes {tot.yes}, partly {tot.partly}, no {tot.no} su {len(filled)} ({(tot.yes + tot.partly) / len(filled):.0%} yes o partly)")
for f, g in filled[filled.answer == "no"].groupby("family"):
    cm = [str(c) for c in g.comment if pd.notna(c) and str(c).strip()]
    if cm: print(f"commenti 'no' su {f}: " + " | ".join(cm))
if out: json.dump(dict(sheets=files, n=int(len(filled)), totals={k: int(v) for k, v in tot.items()}, by_family={f: {k: (float(v) if k == "yes_or_partly" else int(v)) for k, v in r.items()} for f, r in t.iterrows()}), open(out, "w", encoding="utf-8"), indent=1); print("salvato", out)
