# Cosa resta da fare

Aggiornato: 26 ottobre 2026. Ordine = importanza. Quando una voce è fatta, segnala con la data (`FATTO 2026-xx-xx`) e il risultato, non cancellarla.

Direzione della tesi (26 ott, dopo la mail del Prof. Pichler, che fa da relatore): **uno strumento di report sull'avversario che un analista può usare, e che dice accanto a ogni numero quanto fidarsi (voto A-D)**. Il prototipo attuale è la base; il lavoro va da novembre 2026 alla discussione di luglio 2027. Regola che resta valida (feedback del 21 ott): un messaggio centrale, niente analisi laterali.

## 0. Questa settimana: incontro con il professore
- FATTO 2026-10-26: modulo della proposta compilato, `C:\Users\ecole\Downloads\Proposal custom topic - Colecchia.pdf` (titolo: "An opposition report tool for football analysts that states how far each number can be trusted").
- FATTO 2026-10-26: PPT `slides/Thesis Proposal 2026-10 full.pptx` (38 slide, ★ = da mostrare) e foglio in italiano `slides/Speech_proposal_IT.pdf`. PDF del codice spiegato rifatto (`slides/Il codice della tesi spiegato.pdf`, 39 pagine).
- Da fare:
  - inserire la matricola nel modulo;
  - rispondere alla mail con l'orario (27 ott qualsiasi ora, oppure 28 ott 13:00/16:00) e il modulo allegato;
  - studiare il foglio "cosa dire" (soprattutto le slide ★ e le risposte "Se chiede");
  - committare e pushare le modifiche di oggi (app, defending, examples, docs), così il repo che lui può aprire è aggiornato;
  - all'incontro: fare le 4 domande della slide finale, prendere nota delle risposte, firmare il modulo.

## 1. Piano fino alla discussione (luglio 2027; da confermare con il professore)
| Periodo | Lavoro | Domanda |
|---|---|---|
| Nov-Dic | Letteratura (Scopus); import degli export Wyscout; clip tagliate dal video della partita + XML provato in un programma; installazione senza Python; protocollo della replica committato | RQ1, RQ2 |
| Gen | Voto A-D su Wyscout 2017/18, un solo lancio; protocollo dello studio con utenti; inizio reclutamento; (opzionale, se il professore è d'accordo) brief scritto da un modello di IA locale | RQ2, RQ3 |
| Feb-Mar | Primo giro di valutazione; correzioni; scrittura dei capitoli sul prototipo | RQ3 |
| Apr | Secondo giro di valutazione | RQ3 |
| Mag-Giu | Risultati e discussione; bozza completa al professore a maggio; consegna a giugno (data da confermare) | - |
| Lug | Discussione con demo | - |

Estensioni decise il 26 ott: clip tagliate dal video (dentro RQ1); gli analisti indovinano quali numeri valgono prima di vedere i voti (dentro RQ3); brief scritto da un modello di IA locale (Ollama) solo con voti A-B, misurando affermazioni inventate (opzionale, da decidere con il professore).

Rischio principale: trovare gli utenti. Ideale analisti di club (solo con l'ok del professore); realistico allenatori e video analyst di dilettanti e giovanili, studenti di scienze motorie; minimo 8-10 persone, dichiarato come limite.
Limiti da dire sempre: niente dati veri di un club (dati pubblici Wyscout nel formato export); nessuna promessa che un club lo adotti.

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
