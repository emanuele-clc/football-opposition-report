# Cosa resta da fare

Aggiornato: 26 ottobre 2026. Ordine = importanza. Quando una voce è fatta, segnala con la data (`FATTO 2026-xx-xx`) e il risultato, non cancellarla.

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
- FATTO 2026-10-26: nuova critique, 26/40 (verifica più severa, non un peggioramento). I due P1 nuovi sono chiusi:
  - voto o "–" (non valutato) su ogni numero principale (Families, Set pieces, Transitions, Restarts, Game plan, Coach sheet) e legenda dei voti accanto ai primi voti di ogni pagina;
  - cautele su struttura e tiri sempre accanto alla card della famiglia; nel Coach sheet la n dei passaggi e la frase sulle famiglie;
  - "Half reliable" diventa "Partly reliable"; il rank dice "9th highest of 10".
- FATTO 2026-10-26: xG per tiro concesso nel defending sheet e nei rank (descrittivo, non valutato; definizione nell'header di `defending.py`). Gli altri valori sono identici a prima; reproduce_sheets 50/50, test_app_api ALL OK. Da 0.069 (Atlético) a 0.118 (Bordeaux).
- Da fare, dalla critique del 26 ott (dettagli in `.impeccable/critique/`):
  - colori: il giallo ha quattro significati; riempimenti rosso/verde decorativi in Transitions; stato della trust list solo dal colore del pallino; "opponent" e "shot" sono entrambe linee rosse;
  - contrasto nel tema chiaro: "Print all" (1.2:1) ed etichetta "Hints, not advice" (3.5:1);
  - Game plan ancora lungo (5-6 blocchi, Coach brief con 5 tab); la priorità 1 non nomina la zona; Key players ordinati per totale ma mostrano il valore per partita; in Watch first l'ordine delle squadre nel risultato non è detto;
  - dettagli: focus non visibile sulle barre dei rank (`.track{outline:none}`), frasi del backend non tradotte, path locale nel footer, easing con rimbalzo, testo piccolo nel Coach sheet, "own goal · Own goal" fra gli ultimi gol;
  - etichetta "clear structure" (esce dalla pipeline): decidere se cambiarla;
  - rifare la critique dopo questi punti.

## 5b. Idee dal corso StatsBomb "Introduction to Football Analytics" (finito il 26 ott; non prioritarie)
Regola: solo descrittive, per squadra (mai per famiglia: sarebbe un outcome nuovo dopo il test simple-rule negativo), definizione nell'header prima di una sola esecuzione.
- Profilo dei tiri per origine: filtrante, cross alto, cutback, piazzato (flag dei passaggi StatsBomb). Modulo "Types of Attack".
- Mappa del primo pallone sui corner (chi tocca per primo, vinto/perso). Collegato a L3 e al setpieces sheet. Modulo "Set Pieces".
- Non ora: aggression (pressione entro 2 s dalla ricezione), perché il counter-press già non separa gli stili; trendline nel tempo, perché le ultime 5 partite prevedono peggio della stagione (evidence grade) e un trend inviterebbe a leggerci troppo.
- Correggere tre righe "Link to my thesis" nelle pagine Notion del corso:
  - Defensive Choices: PPDA, pressioni per zona e altezza difensiva ci sono già (`defending.py`); manca solo l'aggression;
  - Team/Opposition: rete di passaggi (Families -> Pass network) e completamento sotto pressione ("Where pressing hurts them") ci sono già;
  - Team/Opposition: togliere "xG by family" (regola 3 del CLAUDE.md).
- Per la tesi: lo schema del corso "squadra / rispetto alla lega / nel tempo" corrisponde a report, rank e ultime 5. Citare le fonti originali (es. Ensum, Pollard & Taylor 2004), non il corso.

## 6. Piccole cose
- FATTO 2026-10-24: spiegazione completa del codice per il professore (codice, risultati per squadra, protocolli, soglie, limiti, 30 domande). Doc https://claude.ai/artifact/SGiJMtkT6bYKPe3msod2em, PDF in `slides/Il codice della tesi spiegato.pdf`. Da studiare; mail al professore ancora da inviare.
- Commit delle modifiche all'app del 24 ott (i comandi sono nella chat del 24 ott: `git add` dei file in `app/`).
- Opzionale: aggiornare il Claude Doc "La tesi spiegata passo passo", che dice ancora 4 squadre.
