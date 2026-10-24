# Cosa resta da fare

Aggiornato: 24 ottobre 2026. Ordine = importanza. Quando una voce è fatta, segnala con la data (`FATTO 2026-xx-xx`) e il risultato, non cancellarla.

Regola guida (feedback del professore, 21 ott): "troppe cose in troppo poco tempo". Niente nuove analisi né nuove funzioni dell'app finché i punti 1-3 non sono chiusi.

## 1. Revisione da parte di un analista (punto più debole della tesi)
- Nessuno con esperienza di calcio ha mai usato il report. Serve almeno una persona: video analyst, allenatore, anche di una squadra dilettanti.
- Materiale: `docs/analyst_review_kit.md`, `review_<Team>.csv` / `.html` (sì / in parte / no + le cinque domande fisse).
- Riassunto: `python -X utf8 src/report/summarize_review.py`.
- Anche un esito negativo va bene, purché documentato e non ritoccato.
- LASK Linz solo dopo il consenso del professore (proposta: report gratuito sul prossimo avversario in cambio di 30 minuti di feedback; chiedere provider, formato, possession id, cosa si può pubblicare).

## 2. Relatore e professore
- In attesa del relatore. Mail di aggiornamento a Prof. Pichler: bozza scritta il 24 ott (non ancora inviata).
- Da portare al relatore: il riassunto di una pagina (Claude Doc https://claude.ai/artifact/W4jXYoBPKK7P6g5HmgMkff).
- Decisioni da chiedere:
  - L3 corner: rifarlo (zone dai dati, protocollo prima, Euro 2024 come held-out) oppure chiuderlo come null debole documentato;
  - consenso per contattare LASK;
  - cornice della tesi.

## 3. Letteratura sull'evidence grade (il contributo nuovo)
- Base: `docs/related_work_evidence_grade.md`.
- FATTO 2026-10-24: forward citations di Franks (56 articoli, 4 tenuti), ricerche web mirate, Deb et al. 2023 letto per intero (la ripetibilità è fra run di K-Means, non su partite future). Nuovi lavori vicini: Russomanno, Linke, Geromiller & Lames 2019 (Bundesliga, stabilità e validità predittiva) e Garrido et al. 2020 (consistenza e identificabilità delle squadre). Ancora nessuno studio che dia voti alle frasi di un report. Dettagli nella sezione "Second search" del file.
- Da fare:
  - scaricare dall'università e leggere Matteo et al. 2026 e Russomanno et al. 2019 (paywall);
  - una ricerca su Scopus, annotando risultati trovati e tenuti.
- Finché non è fatto, scrivere "to our knowledge", mai "first".

## 4. Scrittura della tesi (da gennaio 2027)
- Scaletta: `docs/thesis_outline.md`.
- Cornice: valutazione critica delle famiglie di sequenze scoperte automaticamente su dati aperti, più un prototipo di report con evidence grade.
- Cosa si può e non si può dire: CLAUDE.md sezione 7.

## 5. App (solo se avanza tempo; non prioritario)
- FATTO 2026-10-24 (non ancora committato): i tre P1 della critique.
  - Gli spunti mostrano solo le condizioni che sono scattate (spunto PPDA corretto).
  - Cautele su copula e regola semplice sempre visibili.
  - Grade A-D su key point, spunti e Coach sheet.
- Restano due P2 (vedi `.impeccable/critique/`):
  - colori delle mappe non-famiglia (scala neutra), contrasto di "Stampa tutto" nel tema chiaro e delle etichette ambra;
  - Game plan ancora lungo (7 + 6 schede), frasi del backend non tradotte in italiano e tedesco.
- La critique va rifatta dopo il commit: l'ultimo voto è 28/40.

## 6. Piccole cose
- FATTO 2026-10-24: spiegazione completa del codice per il professore (codice, risultati per squadra, protocolli, soglie, limiti, 30 domande). Doc https://claude.ai/artifact/SGiJMtkT6bYKPe3msod2em, PDF in `slides/Il codice della tesi spiegato.pdf`. Da studiare; mail al professore ancora da inviare.
- Commit delle modifiche all'app del 24 ott (i comandi sono nella chat del 24 ott: `git add` dei file in `app/`).
- Opzionale: aggiornare il Claude Doc "La tesi spiegata passo passo", che dice ancora 4 squadre.
