# Cosa resta da fare

Aggiornato: 28 ottobre 2026. Ordine = importanza. Quando una voce è fatta, segnala con la data (`FATTO 2026-xx-xx`) e il risultato, non cancellarla.

Direzione della tesi (28 ott, dopo l'incontro con il Prof. Pichler, relatore all'FH): **uno strumento di report sull'avversario che dice accanto a ogni numero quanto fidarsi (voto A-D)**. Il professore ha chiesto domande di ricerca a cui si possa rispondere **senza analisti esterni e con dati che ho già**. Regola che resta valida (feedback del 21 ott): un messaggio centrale, niente analisi laterali.

Domande di ricerca (modulo firmato: `C:\Users\ecole\Downloads\Proposal_for_a_custom_topic_for_a_masters_thesis_v2_signed.pdf`):
- **RQ1:** quali affermazioni del report sono affidabili per la partita successiva, e i voti restano validi su un secondo provider (Wyscout pubblico, 5 campionati 2017/18)?
- **RQ2:** una previsione che tiene conto del prossimo avversario e del campo (solo partite già giocate) prevede meglio della media stagionale, e cambia quali affermazioni sono affidabili?
- **RQ3 (opzionale, se ci sono analisti):** i voti aiutano gli analisti a decidere su cosa basarsi?

## 0. Fatto questa settimana
- FATTO 2026-10-28: incontro con il Prof. Pichler (slide `slides/Thesis Proposal 2026-10 FINAL v3.pptx`, 28 visibili, dettagli nascosti); modulo rifatto con le nuove RQ, firmato e mandato per mail con i prossimi passi; modifiche dell'app committate e pushate (5031e9f).
- FATTO 2026-10-28: chiesto al Prof. Ianni (UNICAL, su Teams) se fa da relatore o chi potrebbe farlo. **In attesa di risposta.**

## 1. Piano fino alla discussione (luglio 2027; da confermare con il professore)
| Periodo | Lavoro | Domanda |
|---|---|---|
| Nov | Estrarre i 5 campionati Wyscout; estendere `src/adapters/wyscout_to_generic_csv.py` e `evidence_provider.py` per calcolare più affermazioni (oggi 24 di 34; recuperare PPDA, tiri concessi); import Wyscout nel tool; letteratura | RQ1 |
| Dic | Protocollo del grade su Wyscout ("regge" = stesso voto, non stesso valore: sul Barcellona 18 valori su 24 differiscono tra provider) → commit → un solo lancio. Definire la previsione con avversario e campo sulle 9 squadre di sviluppo StatsBomb | RQ1, RQ2 |
| Gen | Protocollo della previsione con avversario → commit → un solo lancio su Wyscout | RQ2 |
| Feb-Apr | Integrare voti e previsione nel tool; scrittura dei capitoli; (opzionale) valutazione con analisti | RQ3 |
| Mag-Giu | Risultati e discussione; bozza completa al professore a maggio; consegna a giugno (data da confermare) | - |
| Lug | Discussione con demo | - |

- FATTO 2026-10-28 (RQ1, preparazione): 5 campionati Wyscout convertiti in `C:\Users\ecole\wyscout_generic\` (1.826 partite, 98 squadre, nessuna partita senza eventi di una squadra). Adapter esteso con azioni difensive ed esito dei passaggi: 29 affermazioni su 34 calcolabili (mancano pressioni e xG); le 24 di prima identiche, round trip difesa 38/38. Bozza `docs/protocol_evidence_grade_wyscout.md` e `src/week4/evidence_grade_wyscout.py`, smoke test passato (solo conteggi).
- FATTO 2026-10-28 (RQ1, confermativo, protocollo commit 4ce5f5a): `results/evidence_grade_wyscout.json`, 96 squadre, un solo lancio. Stessa lettera in 21 di 29 affermazioni (72%, Wilson 95% [0.54, 0.85]), nessuna spostata di due lettere, kappa pesato 0.70: secondo la regola fissata prima, **i voti reggono** (appena sopra la soglia del 70%). Le quattro A di StatsBomb (passaggi per sequenza, quota di lanci lunghi, durata, goal kick corti) sono A anche su Wyscout. 7 delle 8 lettere cambiate passano il confine previsione "weak"/"none" (limite inferiore vicino a 0). SC1 fallisce di nuovo (contropressing D 0.69, appena sotto "high"). Voti Wyscout: 5 A, 11 B, 10 C, 3 D; 5 affermazioni non testabili (pressioni, xG).
- FATTO 2026-10-28 (RQ2, sviluppo esplorativo sulle 9 squadre StatsBomb di sviluppo): `results/exploratory_opponent_forecast_dev.json`. Con avversario + campo la previsione migliora (mediana +0.10 sulle 30 affermazioni; solo avversario +0.06); scelto k = 5 con effetto campo. Protocollo `docs/protocol_opponent_forecast.md` e codice del test vero pronti (controllo del codice sulle 2 squadre Wyscout di sviluppo).
- FATTO 2026-10-28 (RQ2, confermativo, protocollo commit 80552a6, un lancio per provider): `results/opponent_forecast_statsbomb.json` (70 squadre) e `results/opponent_forecast_wyscout.json` (96). Per la regola fissata prima **la previsione con avversario e campo aiuta su entrambi**: migliore in 21 di 30 affermazioni e peggiore in 2 (StatsBomb), migliore in 18 di 25 e peggiore in 1 (Wyscout); migliore su entrambi in 16 di 25. Mediana del miglioramento +0.08 / +0.06. Più grandi: PPDA +0.27 / +0.26, tiri concessi +0.17 / +0.24, tiri +0.17 / +0.19, xT, altezza difensiva. Niente miglioramento per goal kick, portiere e rimesse (dipendono dalla squadra, non dall'avversario). Con la previsione corretta il PPDA passa da C ad A su entrambi i provider. Tra le affermazioni su cui si calcola la correzione (famiglie e giocatori esclusi), le A diventano 14 di 30 (StatsBomb) e 13 di 25 (Wyscout).
- Prossimo: decidere con il professore se mettere la previsione corretta nell'app (l'analista indica il proprio team e il campo); scrivere i capitoli dei metodi.

Tolto dalla proposta il 28 ott: brief scritto da un modello di IA locale; lo studio con utenti diventa opzionale (RQ3). Le clip tagliate dal video restano un miglioramento del tool, non una domanda di ricerca.

Limiti da dire sempre: niente dati veri di un club (dati pubblici Wyscout); nessuna promessa che un club lo adotti; definizioni diverse tra provider.

## 1b. Export per i programmi video: cosa abbiamo scoperto (26 ott)
- Nacsport Basic (installato) ha la voce "Importare file XML (sul timeline)" nel menu con il tasto destro sulla timeline, ma l'import richiede un account Nacsport Hub, che non si può creare da soli (bisogna contattare Nacsport). Quindi l'XML non è ancora stato provato in un programma vero.
- File di prova pronti: `C:\Users\ecole\Downloads\nacsport_test\` (XML di Leverkusen-Leipzig, 41 clip; video di test con cronometro).
- Da fare: (a) chiedere a Nacsport un account Hub o una licenza per studenti, spiegando che è per una tesi; (b) in alternativa provare l'XML in un altro programma che lo importi senza cloud; (c) valutare un export indipendente dal programma: tagliare le clip direttamente dal video della partita (file mp4 per clip o una playlist), che un analista può usare con qualsiasi strumento.

## 2. Letteratura (primo compito di novembre)
- Base: `docs/related_work_evidence_grade.md`.
- FATTO 2026-10-24: forward citations di Franks (56 articoli, 4 tenuti), ricerche web mirate, Deb et al. 2023 letto per intero. Nuovi lavori vicini: Russomanno, Linke, Geromiller & Lames 2019 e Garrido et al. 2020. Ancora nessuno studio che dia voti alle frasi di un report.
- Da fare:
  - scaricare dall'università e leggere Matteo et al. 2026 e Russomanno et al. 2019 (paywall);
  - una ricerca su Scopus, annotando risultati trovati e tenuti;
  - aggiungere letteratura su usabilità e valutazione con utenti (SUS, studi con analisti sportivi) per RQ3.
- Finché non è fatto, scrivere "to our knowledge", mai "first".

## 3. Revisione da parte di un analista (diventa RQ3)
- Nessuno con esperienza di calcio ha mai usato il report.
- Materiale esistente: `docs/analyst_review_kit.md`, `review_<Team>.csv` / `.html`, `src/report/summarize_review.py`. Va ampliato in un protocollo di valutazione (compito, misure, consenso) prima del primo giro.
- LASK: la candidatura alle posizioni dell'Akademie è già stata mandata (24 ott). Un contatto per la tesi solo dopo l'ok del professore.

## 4. App (dentro RQ1 ora, non più "se avanza tempo")
- FATTO 2026-10-24 (non ancora committato): i tre P1 della critique (spunti con solo le condizioni scattate, cautele sempre visibili, voti su key point, spunti e Coach sheet).
- FATTO 2026-10-26: nuova critique, 26/40. I due P1 nuovi sono chiusi: voto o "–" su ogni numero principale e legenda dei voti; cautele su struttura e tiri accanto alla card della famiglia; n dei passaggi nel Coach sheet; "Partly reliable"; "9th highest of 10".
- FATTO 2026-10-26: xG per tiro concesso nel defending sheet e nei rank (descrittivo, non valutato). Altri valori identici; reproduce_sheets 50/50, test_app_api ALL OK.
- Da fare, dalla critique del 26 ott (dettagli in `.impeccable/critique/`):
  - colori (giallo con quattro significati, rosso/verde decorativi in Transitions, stato della trust list solo dal colore, "opponent" e "shot" entrambe rosse);
  - contrasto nel tema chiaro ("Print all" 1.2:1, "Hints, not advice" 3.5:1);
  - Game plan ancora lungo; priorità 1 senza zona; Key players ordinati per totale; ordine delle squadre in Watch first;
  - dettagli: focus sulle barre dei rank, frasi del backend non tradotte, path locale nel footer, easing con rimbalzo, testo piccolo nel Coach sheet, "own goal · Own goal";
  - etichetta "clear structure": decidere se cambiarla.

## 5. Idee dal corso StatsBomb (non prioritarie)
Regola: solo descrittive, per squadra (mai per famiglia), definizione nell'header prima di una sola esecuzione.
- Profilo dei tiri per origine (filtrante, cross alto, cutback, piazzato).
- Mappa del primo pallone sui corner.
- Non ora: aggression, trendline nel tempo.
- Correggere tre righe "Link to my thesis" nelle pagine Notion del corso (PPDA e pressioni ci sono già; rete di passaggi e completamento sotto pressione ci sono già; togliere "xG by family").

## 6. Piccole cose
- FATTO 2026-10-26: PDF "Il codice della tesi spiegato" reimpaginato (39 pagine) e aggiornato; stesse correzioni nel Claude Doc https://claude.ai/artifact/SGiJMtkT6bYKPe3msod2em.
- Opzionale: aggiornare il Claude Doc "La tesi spiegata passo passo", che dice ancora 4 squadre.
- Opzionale: versione inglese della guida al codice, se il professore la chiede.
