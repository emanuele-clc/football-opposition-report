# Il codice spiegato, file per file

Aggiornato: 6 novembre 2026, dopo la pulizia (tracking, export XML e brief con Ollama spostati in `archive/`).

Questo file spiega **ogni file di codice**: a cosa serve, cosa riceve, cosa produce, cosa fa passo per passo e quali sono le sue funzioni. Alla fine di ogni file c'è una riga **"Se ti chiedono"**: la domanda più probabile all'esame, con la risposta breve.

Consiglio per studiarlo: leggi prima le sezioni 1 e 2 (servono per tutto il resto), poi un file alla volta, **con il file aperto accanto**. Le righe indicate (es. `L55-110`) ti dicono dove guardare.

---

## 1. La mappa

```
src/
  analysis/     le analisi della tesi (13 file)
  report/       le schede del report (12 file + xt_grid.json)
  adapters/     convertono dati di altri fornitori nel nostro formato (3 file)
  oppreport.py  un solo comando che fa tutto il report
app/
  run.py        avvia l'app
  backend/      server.py (le risposte alla pagina) e gameplan.py (gli spunti)
  frontend/     la parte grafica (React)
tests/          controlli: i numeri escono sempre uguali?
archive/        codice usato una volta, che non serve per rifare i numeri
results/        i risultati (JSON), mai modificati a mano
docs/           protocolli e spiegazioni
```

Il percorso dei dati è sempre lo stesso:

1. **Scarico** le partite (`download_data.py`).
2. **Taglio** ogni partita in sequenze di passaggi (`sequences_clustering.py`).
3. **Raggruppo** le sequenze simili in famiglie (`families.py`).
4. **Controllo** sulle partite tenute da parte se le famiglie reggono (`validate_replication.py`, `compare_simple_rules.py`).
5. **Do un voto** A-D a ogni frase del report (`evidence_grade.py`, RQ1) e provo a migliorare la previsione con l'avversario (`forecast_opponent.py`, RQ2).
6. **Scrivo il report** (`oppreport.py` lancia le schede di `src/report/`) e lo **mostro nell'app**.

---

## 2. Sei idee che tornano in tutti i file

Se capisci queste sei cose, capisci quasi tutto il codice.

**a) I dati StatsBomb.** Ogni partita è un file JSON in `ev/<match_id>.json`: una lista di **eventi** (passaggio, conduzione, tiro, pressione, ...). Ogni evento ha il tipo (`e["type"]["name"]`), la squadra (`e["team"]["name"]`), il minuto e il secondo, la posizione (`e["location"]` = [x, y]) e il numero di **possesso** (`e["possession"]`). Il campo è 120 × 80. StatsBomb gira già le coordinate in modo che ogni squadra attacchi **da sinistra a destra**: x = 0 è la propria porta, x = 120 quella avversaria; y piccolo = sinistra. L'elenco delle partite di un campionato è in `matches/<competizione>_<stagione>.json` (es. `9_281.json` = Bundesliga 2023/24).

**b) Partite di esplorazione e partite riservate.** Le partite sono ordinate per data. Il primo 70% serve per guardare e scegliere (esplorazione). L'ultimo 30% resta chiuso in un cassetto e si apre una volta sola, per il test vero (partite riservate). Nel codice: `k0 = int(round(n_matches * 0.7))`, poi `df.gi < k0` (esplorazione) oppure `df.gi >= k0` (riservate). `gi` è il numero della partita in ordine di data (0 = la prima).

**c) Le due fasi.** Una sequenza che parte prima di x = 45 è **costruzione** (build-up), da 45 in avanti è **fase avanzata**. Nel codice: `d.x0 < 45`. Le famiglie si chiamano B1-B5 e A1-A3 nel report (nei file vecchi della validazione: C1-C5, "C" di costruzione; sono le stesse).

**d) Le 11 caratteristiche (`COLS`).** Ogni sequenza diventa 11 numeri: dove inizia (`x0`, `w0`), dove finisce (`x1`, `w1`), quanto avanza (`net_x` = x1 − x0), quanta strada fa la palla (`path_len`), quanto va dritta (`directness` = net_x / path_len, tra −1 e 1), quanti passaggi (`n_pass`), quota di lanci lunghi (`long_share`, passaggi di almeno 30 m), quanto si allarga (`width_std`, deviazione standard di y) e quanto dura (`dur`, secondi). `w0` e `w1` sono la distanza dal centro del campo (`abs(y - 40)`): così sinistra e destra contano uguale.

**e) K-Means.** È l'algoritmo che fa i gruppi: mette insieme le sequenze con numeri simili. Prima i numeri si mettono sulla stessa scala (`StandardScaler`: media 0, deviazione 1), altrimenti i metri peserebbero più dei secondi. `KMeans(5, n_init=20, random_state=0)` vuol dire: 5 gruppi, prova 20 partenze diverse e tieni la migliore, con il seme fisso così il risultato è sempre uguale. Dopo il fit, le famiglie si **numerano per x di partenza media** (la famiglia 1 parte più indietro).

**f) Bootstrap per partite e seme fisso.** Serve a capire quanto un numero è sicuro. Si pescano a caso le partite (con ripetizione), si ricalcola il numero, e si fa 1000 volte. Il 95% dei risultati sta nell'**intervallo di confidenza** (IC95). Si pescano **partite** e non sequenze, perché le sequenze della stessa partita si somigliano (stesso avversario, stesso punteggio): pescarle una per una darebbe intervalli troppo stretti.

```python
rng = np.random.default_rng(2026)           # seme fisso: ogni volta gli stessi numeri casuali
for _ in range(1000):
    pick = rng.choice(games, len(games))     # pesco le partite, con ripetizione
    means.append(np.mean(...))               # ricalcolo il numero
ci = np.percentile(means, [2.5, 97.5])       # intervallo al 95%
```

Se l'intervallo è tutto sopra zero, l'effetto è "chiaro".

---

## 3. `src/analysis/`: le analisi della tesi

### `download_data.py` (43 righe): scaricare i dati
**A cosa serve:** scarica da GitHub i dati aperti StatsBomb di un campionato.
**Si lancia:** `python download_data.py 9 281 "Bayer Leverkusen"` (9 = Bundesliga, 281 = stagione 2023/24). Si lancia **dalla cartella dati**.
**Produce:** le cartelle `matches/` (elenco partite), `ev/` (eventi) e `t360/` (posizioni dei giocatori, quando ci sono).
**Passo per passo:**
1. Scarica l'elenco delle partite del campionato.
2. Se hai dato una squadra, tiene solo le sue partite.
3. Prepara la lista dei file da scaricare (eventi e 360) e li scarica **8 alla volta** (`ThreadPoolExecutor`).
4. `download(job)`: se il file c'è già ed è più grande di 100 byte, lo salta. Così, se si interrompe, basta rilanciarlo.

**Se ti chiedono** "perché 100 byte?": un file interrotto o una pagina di errore sono quasi vuoti; un file di eventi vero pesa megabyte.

### `sequences_clustering.py` (165 righe): le sequenze
**A cosa serve:** trasforma le partite di una squadra in una **tabella di sequenze** (una riga = una sequenza). Non si lancia da solo: quasi tutti gli altri file lo importano (`import sequences_clustering as S`, poi `S.extract()`).
**Riceve:** da riga di comando l'elenco partite, la squadra e la cartella dati (`MF`, `TEAM`, `BASE`).
**Passo per passo (`extract()`, L113-144):**
1. Legge l'elenco partite e tiene quelle della squadra, **ordinate per data**.
2. Per ogni partita trova l'avversario e apre il file degli eventi.
3. Tiene solo le azioni della squadra mentre ha il possesso: passaggi, conduzioni, tiri e dribbling. Le raggruppa per numero di possesso (`possessions.setdefault(...)`).
4. Per ogni possesso chiama `sequence_row()`. Se torna `None`, il possesso è scartato.
5. Restituisce la tabella (pandas DataFrame) e il numero di partite.

**Le funzioni:**
- `zone(x, y)` (L31): in quale delle 12 zone cade un punto. 4 fasce in lunghezza (A = la nostra area ... D = ultimo terzo) × 3 in larghezza (s = sinistra, C = centro, d = destra). `np.searchsorted` trova in quale intervallo cade il numero.
- `path_points(events)` (L39): il percorso della palla. Il punto di partenza, poi dove finisce ogni passaggio e ogni conduzione. Toglie i punti ripetuti.
- `sequence_row(...)` (L55-110): il cuore del file.
  - scarta se il possesso **non è gioco aperto** (`OPEN_PLAY`: gioco normale, contropiede, rinvio dal fondo, rimessa del portiere, rimessa laterale; quindi niente angoli, punizioni, calci d'inizio);
  - scarta se ha **meno di 3 passaggi** o meno di 4 punti nel percorso;
  - calcola le caratteristiche (sezione 2d), più il minuto, il tempo, se finisce con un tiro (`shot`) e le zone.
- `jaccard_stability(X, labels, k, B, seed)` (L147): la **stabilità**. Rifà K-Means 200 volte su dati ripescati; per ogni famiglia cerca il gruppo nuovo più simile e misura la sovrapposizione con l'indice di Jaccard (in comune / totale). Media vicina a 1 = la famiglia si ritrova sempre.

**Se ti chiedono** "cos'è una sequenza?": un possesso in gioco aperto con almeno 3 passaggi; partenze da calcio piazzato escluse.

### `families.py` (352 righe): le famiglie, solo sulle partite di esplorazione
**Si lancia:** `python families.py final|robustness|null <partite.json> "<Squadra>"`.
- **`final`** (L57-162), il metodo finale:
  1. prende le sequenze delle partite di esplorazione;
  2. in ogni fase: scala i numeri, K-Means (k = 5 costruzione, k = 3 avanzata), numera le famiglie per x di partenza;
  3. per ogni famiglia: quota, medie delle caratteristiche, tasso di tiro, stabilità (Jaccard) e i percorsi più frequenti fatti di 3 zone (`collapse()` toglie le zone ripetute di fila);
  4. salva `L2_results_<Squadra>.json`, i profili CSV, le sequenze CSV e una figura con un campo per famiglia.
- **`robustness`** (L166-304): le famiglie cambiano se cambio il taglio (35-55 invece di 45), il numero k o l'algoritmo (mistura gaussiana, Ward)? Si confronta con l'ARI (quanto due divisioni sono d'accordo). Prova anche a prevedere la famiglia della sequenza dopo.
- **`null`** (L308-344), test E1: rifà la stabilità su dati finti **senza gruppi**: (1) colonne mescolate a caso, (2) una nuvola gaussiana con le stesse medie e correlazioni. Se le famiglie vere sono più stabili dei dati finti di almeno 0.10, non sono solo un effetto di K-Means.
- `best_jaccard()` (L38): per ogni famiglia, il Jaccard con il gruppo più simile di un altro fit.

**Se ti chiedono** "perché k = 5 e 3?": scelti una volta sulle partite di esplorazione (`archive/choose_k.py`), poi congelati e dichiarati.

### `validate_replication.py` (211 righe): il test vero (H1, H2, H3)
**Si lancia:** `python validate_replication.py <partite.json> "<Squadra>" . --confirm` (`--no-h3` per Leverkusen e Leicester, validate prima che H3 esistesse; `--dry-run` per provare il codice solo sulle partite di esplorazione).
**Produce:** `holdout_<Squadra>.json`.
**Passo per passo (`run()`, L36-204):**
1. **Protezione:** senza `--confirm` (o `--dry-run`) si rifiuta di aprire le partite riservate. Il test si fa una volta sola, dopo aver committato il protocollo.
2. Estrae le sequenze e divide: 70% allenamento, 30% riservate.
3. **Fit** delle famiglie solo sull'allenamento, poi le **congela** (`models`: scaler, K-Means e numerazione per fase).
4. `assign()`: dà a ogni sequenza la famiglia più vicina e aggiunge `prev_cl`, la famiglia della sequenza precedente nella stessa partita.
5. **H2:** confronta le quote delle famiglie tra allenamento e riservate (scarto massimo ≤ 10 punti) e calcola la silhouette delle famiglie congelate sulle riservate (≥ 0.10). Passa se entrambe vanno bene.
6. **H1:** `context()` costruisce gli ingressi del modello: play pattern (come inizia la sequenza), minuto, secondo tempo sì/no, famiglia precedente. Una regressione logistica (C = 0.5) dà la probabilità di ogni famiglia. Si confronta con la previsione "di base" (le quote delle famiglie) usando il **log-loss**. Guadagno = log-loss base − log-loss modello, per sequenza. `boot_ci()` fa l'IC95 ripescando le partite. H1 passa se tutto l'intervallo è sopra zero.
7. **H3:** una logistica con la sola famiglia prevede il tiro; si confronta con il tasso di tiro medio. Come descrizione, anche un modello con le 11 caratteristiche grezze.
8. Salva il JSON.

**Le funzioni:** `boot_ci()` (L22, bootstrap per partite), `logloss_shot()` (L32, log-loss di una previsione sì/no).

**Se ti chiedono** "cos'è il log-loss?": la penalità di una previsione. Se dai probabilità 0.9 alla cosa che succede, paghi poco (−log 0.9 = 0.11); se le dai 0.1, paghi tanto (2.3). Più basso = meglio.

### `compare_simple_rules.py` (117 righe): le famiglie battono una regola banale?
**Protocollo:** `docs/protocol_simple_rule.md`. **Si lancia** con `--confirm` (riservate, una volta) o `--dry-run`.
**Passo per passo:**
1. Fa le famiglie sulle partite di esplorazione, come in validate.
2. Costruisce la regola banale: divide le sequenze in k fasce con lo stesso numero di sequenze in base a **dove finiscono** (x1). `bins()` (L54) calcola i confini sulle partite di esplorazione con i quantili.
3. Per famiglie e fasce usa lo stesso modello (logistica, C = 0.5) per prevedere il tiro sulle riservate.
4. `loss_per_sequence()` (L45): il log-loss di ogni sequenza per i due metodi; la differenza ha un IC95 per partite.
5. Verdetto: famiglie meglio, regola meglio o nessuna differenza.

**Risultato:** famiglie meglio in 0 squadre su 10. Risultato negativo, dichiarato.
**Se ti chiedono** "perché è importante?": se un'unica variabile (dove finisce l'azione) spiega il tiro altrettanto bene, le famiglie non aggiungono informazione sul tiro.

### `sample_size.py` (84 righe): quante partite servono?
**Passo per passo:**
1. Calcola i numeri della stagione intera (`numbers()`: passaggi per sequenza, lanci lunghi, quota dalla propria metà, tasso di tiro, lanci dai rinvii) e le quote delle famiglie (`shares()`, famiglie fatte sulla stagione intera).
2. Pesca a caso 3, 5, 8, 10 o 15 partite, 500 volte.
3. Misura quanto i numeri di quelle poche partite si allontanano da quelli della stagione.
4. Salva `samplesize_<Squadra>.json`.

**Se ti chiedono** il risultato: passaggi per sequenza e lanci lunghi servono 8-10 partite; il tasso di tiro non distingue bene le squadre nemmeno con 15.

### `ten_teams.py` (245 righe): tutto sulle 10 squadre
**Si lancia dalla cartella dati:**
- `run simplerule|samplesize|clustertest <selezione.json>`: lancia uno script su tutte le 10 squadre (`run_all()`, L48). Salta le squadre già fatte. `run_logged()` salva l'output in un file di log.
- `summary replication|simplerule|samplesize`: legge i risultati e stampa la tabella finale con la regola del protocollo (almeno 7 squadre su 10). `wilson()` (L73) è l'intervallo per una proporzione (es. 8 su 10 → [0.49, 0.94]).

L'estrazione a sorte delle 6 squadre (seme 20261013) è in `archive/select_and_replicate.py`.

### `exploratory_predictability.py` (250 righe, esplorativo): da dove viene la prevedibilità?
Usa **tutte** le partite con la validazione incrociata per partite (6 gruppi: alleno su 5, provo sul sesto, e giro; le famiglie si rifanno dentro ogni giro, così non c'è fuga di informazione).
- `cv`: il guadagno del modello H1 su tutte le partite.
- `ablation`: tolgo un ingrediente alla volta. Risultato: quasi tutto il guadagno viene da **come inizia la sequenza** (play pattern).
- `context`: a parità di play pattern, minuto, punteggio o casa/trasferta aiutano? Risultato: no.

**Funzioni:** `fit()` e `assign()` (famiglie dentro ogni giro), `blocks()` (i 6 gruppi di partite), `protocol_inputs()` (gli ingressi del modello), `proba()` e `loss()` (probabilità e log-loss), `boot_ci()`.

### `exploratory_clusters.py` (213 righe, esplorativo): le famiglie sono gruppi veri?
- `copula` (`copula_test()`, L59): crea 100 dataset finti con le stesse distribuzioni e correlazioni delle 11 caratteristiche ma **nessun gruppo** (copula gaussiana). Confronta silhouette e stabilità vere con quelle finte. p = (1 + finti con silhouette ≥ vera) / 101. Risultato: le famiglie sono solo un po' più nette dei dati finti, cioè "fette di un continuo".
- `methods` (`methods_test()`, L118): K-Means contro mistura gaussiana e Ward, e K-Means con altri k e tagli.

### `corners.py` (326 righe): gli angoli (L3)
**Domanda:** dove una squadra manda i suoi angoli, una difesa può sfruttarlo?
- `zone()` (L19): la zona di arrivo dell'angolo (corto/fuori area, primo palo, centro, secondo palo), misurata dal lato di chi batte.
- `corner_xg()` (L31): gli xG dei tiri nati dall'angolo.
- `setup_of(near, far)` (L44): la disposizione difensiva dalle posizioni 360 (più difensori vicini o lontani dal battitore).
- `matrix()`, `gain()`: xG medio per disposizione × zona, e quanto si guadagna scegliendo la disposizione migliore.
- `permutation_test()` (L71): mescola gli xG a caso 1000 volte; p = quanto spesso il caso dà un guadagno grande come quello vero.
- `leverkusen()`: il test sul Leverkusen (148 angoli con 360). Risultato: p = 0.17.
- `pooled()`: Mondiale 2022 + Europei 2020 e 2024 (846 angoli); disposizione scelta su Euro 2020 + Mondiale, provata su Euro 2024. Risultato: p = 0.41.

**Se ti chiedono** "allora gli angoli non si possono sfruttare?": no, il test aveva poca potenza (solo effetti enormi erano visibili). È un nullo debole.

### `evidence_grade.py` (676 righe): il voto A-D (RQ1, il contributo principale)
**Idea:** ogni frase del report ("il 40% dei rinvii va corto", "PPDA 12.6", ...) è un **tipo di frase** (34 in `CLAIMS`: S01-S06 sequenze, F07-F08 famiglie, R restarts, P angoli, T transizioni, D difesa, A attacco, K giocatori). Ognuna riceve un voto in base a due domande:
1. **Previsione:** il numero calcolato sulle partite passate prevede la **prossima** partita meglio della media del campionato?
2. **Discriminazione:** il numero distingue davvero le squadre, o le differenze sono rumore?

**Due passi:**
- `extract <data_dir> <work_dir>` (`extract()`, L218): per ogni squadra e partita chiama `match_values()` (L104-200), che calcola **numeratore e denominatore** di ogni frase usando **gli stessi script del report** (importati in cima: `restarts`, `setpieces`, `transitions`, `defending`, `xthreat`, `keyplayers`). Così il voto vale proprio per quello che il report scrive. Esempio: "rinvii corti" = numeratore rinvii corti, denominatore rinvii. Salva un `.pkl` per squadra.
- `analyse <work_dir> --set dev|confirm` (`analyse()`, L504): calcola i voti.

**Le funzioni, nell'ordine in cui lavorano:**
- `all_forecasts()` (L323): per ogni squadra, frase e partita dalla 6ª in poi (`MIN_PAST = 5`) chiama `forecast_rows()`.
- `forecast_rows()` (L254): tre previsioni per la partita t: **F** = la stagione finora (somma numeratori / somma denominatori delle partite prima), **B** = la media delle altre squadre del campionato prima di quella data, **L** = le ultime 5 partite. Salva anche il valore vero `y`.
- `pi_inside()` (L243): la partita vera cade nell'intervallo all'80% costruito dalle partite precedenti? (serve per la calibrazione)
- `ratio_ci()` (L395): un rapporto di somme con IC95, ripescando **squadre**.
- `se(col)` (L410): l'errore al quadrato di una previsione, pesato con il denominatore.
- **Skill** = 1 − errore(F) / errore(B). Positiva = la stagione della squadra prevede meglio della media del campionato. "strong" se il limite basso dell'IC ≥ 0.10, "weak" se > 0.
- `discrimination()` (L427): D = 1 − (rumore dentro la squadra) / (varianza tra squadre). Il rumore si stima ripescando le partite di ogni squadra. "high" ≥ 0.7, "medium" ≥ 0.5 (idea di Franks et al. 2016).
- `matches_needed()` (L451): con quante partite l'errore (90° percentile) scende sotto metà della differenza tipica tra squadre.
- `grade()` (L478): la tabellina. A = previsione forte e discriminazione alta; B = entrambe almeno sufficienti; C = solo una; D = nessuna. Per le quote delle famiglie conta solo la previsione.
- `guard()` (L588): prima del lancio vero controlla che protocollo e script siano committati e pushati e che il file risultato non esista già. È la regola "una volta sola" scritta nel codice.
- `drop_missing()` (L601): correzione del 19 ottobre (nota 1 del protocollo): toglie le partite dove il file eventi non contiene il nome della squadra (dato mancante, non zero).

**Controlli di buon senso (`checks`):** SC1 il contropressing dovrebbe discriminare poco (fallito: 0.71, dichiarato); SC2 passaggi per sequenza dovrebbe avere voto alto.
**Se ti chiedono** "perché la media del campionato come confronto?": è quello che un analista saprebbe senza guardare la squadra. Se la stagione della squadra non fa meglio, quel numero non dice niente di specifico.

### `evidence_grade_wyscout.py` (195 righe): RQ1, i voti su Wyscout
Stesso codice di `evidence_grade.py` (lo importa), con i dati Wyscout 2017/18 (5 campionati, 98 squadre) convertiti dall'adapter. Toglie le frasi che Wyscout non può calcolare (pressioni, xG).
- `all_teams()`, `extract()`, `load_teams()`: come in evidence_grade.
- `compare()` (L113): mette a confronto lettera per lettera i voti StatsBomb e Wyscout. `kappa_linear()` misura l'accordo tenendo conto del caso; `wilson()` dà l'intervallo della quota di lettere uguali.

**Risultato:** stessa lettera in 21 frasi su 29 (72%, la regola era 70%), nessuna a due lettere di distanza.

### `forecast_opponent.py` (237 righe): RQ2, l'avversario aiuta la previsione?
**Idea:** la previsione del voto (F, la stagione finora) non sa contro chi si gioca. Contro una squadra che pressa forte, chiunque perde più palloni.
**La formula (in cima al file):**
- `L` = valore del campionato prima della data;
- `A_Y` = cosa hanno fatto **gli avversari di Y** contro Y prima della data;
- `w_Y = n_Y / (n_Y + k)`: peso minore se Y ha giocato poche partite;
- `V` = metà della differenza casa − trasferta nel campionato;
- **F_adj = F + w_Y (A_Y − L) [± V]**. Le quote restano tra 0 e 1.

**Le funzioni:** `rows()` (L40) calcola F e F_adj per ogni partita; `summary()` (L109) il miglioramento = 1 − errore(F_adj)/errore(F) con IC95 ripescando squadre; `regrade()` (L124) rifà il voto con la previsione corretta; `confirm()` (L140) il lancio unico.
**Si lancia:** `dev` (sceglie k e se usare il campo, sulle 9 squadre di sviluppo, esplorativo), poi `confirm statsbomb` e `confirm wyscout` una volta.
**Risultato:** meglio in 21 frasi su 30 (StatsBomb) e 18 su 25 (Wyscout); il PPDA passa da C ad A.

---

## 4. `src/report/`: le schede del report

Ogni file fa **una scheda** per una squadra: una pagina HTML da stampare, un JSON con tutti i numeri (lo legge l'app) e spesso una **lista di clip** (CSV con partita, minuto, secondo di ogni azione). Si lanciano tutti insieme con `oppreport.py`. Si usano tutti così: `python <scheda>.py <partite.json> "<Squadra>" [cartella_dati]`. Funzionano allo stesso modo:

1. `extract()`: leggono l'elenco partite e gli eventi, e per ogni partita contano quello che serve;
2. `summarise()`: sommano sulla stagione e calcolano l'IC95 con il bootstrap per partite;
3. guardano anche le **ultime 5 partite**, per vedere se la squadra sta cambiando;
4. `html_page()` e `write_clips()`: scrivono la pagina, il JSON e le clip.

Le regole (cosa conta come "corto", come "palla persa", ...) sono scritte **in cima a ogni file**, nella docstring, e sono state fissate prima di guardare i risultati.

### `common.py` (80 righe): le funzioni in comune
- `team_matches(mf, team)`: le partite della squadra in ordine di data.
- `opponent(g, team)`: chi è l'avversario in quella partita.
- `third(x)`: terzo di campo (proprio < 40, centrale, ultimo ≥ 80).
- `is_type(e, name)`: l'evento è di quel tipo?
- `boot(values, gi, games)` e `boot_stat(stat, games)`: IC95 ripescando le partite.
- `pc(x)` e `ci(c)`: scrivono 0.23 come "23%" e [0.21, 0.27] come "21-27%".
- `fig_png(fig)`: trasforma un grafico matplotlib in un'immagine dentro l'HTML (base64), così la pagina è un file solo.

### `make_report.py` (421 righe): il report principale
Usa il metodo della tesi con le stesse impostazioni (taglio 45, k = 5 e 3, 11 caratteristiche), ma su **tutta** la stagione: qui si descrive, non si testa.
**Passo per passo:**
1. Prende le sequenze (`S.extract()`) e calcola lo **stile** (`style()`, L289): passaggi per sequenza, lanci lunghi, quota dalla propria metà, tiri, ognuno con IC95 (`boot_games()`) e il confronto con le altre squadre della cartella (i file `seq_<Squadra>.csv`).
2. `fit_phase()` (L115-187): le famiglie di una fase e, per ognuna, quota, profilo, tasso di tiro, quanto varia da partita a partita, stabilità (`jaccard_boot()`, ripescando partite) tradotta in parole da `reliability()`.
3. Il controllo di struttura (le famiglie sono più nette di dati senza gruppi?) e la tabella "come inizia la sequenza → in che famiglia finisce".
4. "Quanto fidarsi di questo report", in base al numero di partite.
5. `examples()` (L96): le 3 sequenze più vicine al centro di ogni famiglia, per il foglio di revisione.
6. Scrive `report_<Squadra>.html/.json`, `clips_<Squadra>.csv` (ogni sequenza con famiglia e minuto; con `video_time()` anche il tempo nel video, se ci sono gli offset) e il **foglio di revisione** `review_<Squadra>.csv/.html` (esempi per famiglia e cinque domande fisse).

Altre funzioni: `data_provider()` (StatsBomb, Wyscout o altro, scritto nella pagina), `family_shares()`, `fig_png()` (la barra media inizio → fine di ogni famiglia).

### `restarts.py` (241 righe): le ripartenze
Rinvii dal fondo, rimesse del portiere con le mani e rimesse laterali (nella propria metà e in quella avversaria).
- `restart_row()` (L51): un possesso che parte da una ripartenza. Guarda il **primo passaggio**: corto (< 30 m) o lungo, verso sinistra/centro/destra (`side_of()`), chi lo riceve. Poi come finisce: arriva nella metà avversaria? Nell'ultimo terzo? Tiro? Finisce nella propria metà?
- `end_of()` (L34): dove finisce un'azione.
- `summarise()` (L145): le quote con IC95, stagione e ultime 5.
- `pitch()` (L118): il campo con le frecce dei primi passaggi (corti in blu, lunghi in arancione).
- `write_clips()`: `restart_clips_<Squadra>.csv`.

### `setpieces.py` (210 righe): angoli e punizioni
- **Angoli:** lato (da dove si batte), `delivery_zone()` (zona di arrivo, le stesse zone di `corners.py`), chi batte e chi riceve (`name()`), se nasce un tiro e quanti xG (`possession_xg()`: NaN se i dati non hanno xG).
- **Punizioni** dall'ultimo terzo (x ≥ 80): tiro diretto, cross in area o gioco corto.
- `set_piece_row()` (L60): una riga per palla inattiva; `summarise()`, `html_page()`, `write_clips()` come sopra.

### `transitions.py` (289 righe): palle perse e recuperate
Non usa i possessi di StatsBomb, ma solo **l'ordine delle azioni** (`actions()`, L40: passaggi, conduzioni, tiri, dribbling in ordine di tempo), così funziona con qualunque fornitore.
- **Palla persa:** una nostra azione seguita da almeno 2 azioni di fila dell'avversario (o da un suo tiro), in gioco aperto.
- **Contropressing:** torniamo ad agire entro 5 secondi.
- **Tiro subito:** l'avversario tira entro 10 secondi.
- **Recupero:** il contrario; tiro nostro entro 10 secondi.

`extract()` (L63) scorre le azioni e applica queste regole; `heat()` (L129) fa le mappe 6 × 3; `summarise()` conta per terzo di campo. Nella scheda c'è scritto che il contropressing è 17-19% per tutte le squadre, quindi non distingue gli stili.
**Se ti chiedono** "perché non usi i possessi StatsBomb?": StatsBomb non apre un nuovo possesso se la palla viene persa e ripresa subito; con i possessi avevo solo ~4% di recuperi, un numero falso.

### `defending.py` (222 righe): come difende
- `match_stats()` (L32): per una partita conta i passaggi avversari nella loro zona (x < 72), le nostre azioni difensive lì (x ≥ 48), le pressioni, il contropressing, l'altezza delle azioni difensive, tiri e xG subiti.
- **PPDA** = passaggi avversari / nostre azioni difensive (duelli, intercetti, falli). Basso = pressing alto e intenso.
- `pressure_map()` (L70): mappa delle pressioni 6 × 4 con la linea dell'altezza media.
- Ha bisogno degli eventi difensivi StatsBomb (Pressure, Duel, ...): con il CSV generico si ferma e lo dice.

### `matchups.py` (236 righe): contro chi va meglio o peggio
Divide le partite passate in due gruppi e confronta.
- `one_match()` (L80): i numeri di una partita (xG fatti e subiti, tiri, palle perse nella propria metà, passaggi sotto pressione, punti) e le caratteristiche dell'avversario (il suo PPDA; `back_line()` = difesa a 3/5 o a 4 dal modulo iniziale).
- `compare()` (L142): media del gruppo A − media del gruppo B, IC95 con bootstrap dentro ogni gruppo. Verdetto: "chiaro", "incerto" o "gruppo troppo piccolo" (< 6 partite). Le misure che condividono eventi con il PPDA sono segnate "in parte per costruzione".
- Divisioni: avversario che pressa tanto o poco (PPDA sotto o sopra la mediana), difesa a 3/5 o a 4, casa o trasferta.
**Solo descrittivo:** non dice quale modulo usare.

### `keyplayers.py` (319 righe): i giocatori chiave
- `events_view()` (L132-284): il lavoro principale. I primi 3 giocatori per ruolo: chi riceve in costruzione, chi entra nell'ultimo terzo, chi fa più xG, chi batte angoli e punizioni, chi perde più palloni nella propria metà (portiere segnalato). Anche le zone dei falli e i passaggi sotto pressione per zona della propria metà (`zone()` 3 × 3).
- `match_goals()` (L91): ogni gol della partita (fatti e subiti) con l'origine (`goal_origin()`: come è iniziato il possesso). Controllato: i gol corrispondono ai risultati veri delle partite.
- `time_slot()`: in quale quarto d'ora (per la linea del tempo dei gol).
- `short(name)`: tiene il nome completo, perché tagliarlo sbaglia i doppi cognomi spagnoli.

### `xt_model.py` (136 righe) + `xt_grid.json`: il modello xT
Si lancia **una volta sola**. Divide il campo in 16 × 12 zone; il valore di una zona è la probabilità che, avendo la palla lì, il possesso finisca in gol nelle azioni successive (Karun Singh 2018).
- `move(e)` (L41): un passaggio o una conduzione in gioco aperto → (inizio, fine, riuscito?, tipo).
- `open_shot(e)`: un tiro su azione.
- `fit()` (L65): per ogni zona conta s (quota di tiri), g (quota di gol sui tiri), T (dove va la palla dopo un movimento riuscito). Poi risolve **xT = s·g + m·T·xT** ripetendo il calcolo finché non cambia più.
- Salva la griglia in `xt_grid.json`, così tutte le squadre usano lo stesso "righello".

### `xthreat.py` (256 righe): la scheda della pericolosità
Usa la griglia. Per ogni passaggio o conduzione **riuscita**: xT aggiunto = valore della zona di arrivo − valore della zona di partenza (`val()`). Somma per partita.
Mostra: passaggi contro conduzioni, da quale terzo e corridoio parte (`chan()` = corridoio), i 5 giocatori migliori, l'xT concesso, le ultime 5, `maps()` (griglia e xT per zona di partenza). Le 40 azioni più pericolose vanno in `xt_clips_<Squadra>.csv`.
Ha bisogno di sapere se un passaggio è riuscito: con il CSV generico senza quella colonna si ferma.
**È anche la frase A31 del voto**, per questo è rimasto nel progetto.

### `summary.py` (157 righe): la pagina di preparazione
Una pagina da stampare con i fatti principali di tutte le schede. Non calcola niente di nuovo: legge i JSON (`load()`).
- `others()` (L20): la stessa scheda di tutte le altre squadre nella cartella.
- `compare()` (L38): la posizione della squadra tra le altre (1 = valore più alto) e la media.
- `flag()` (L57): "controlla sul video" quando le ultime 5 escono dall'intervallo della stagione.

### `summarize_review.py` (60 righe)
Legge il foglio di revisione compilato dall'analista (sì / in parte / no per ogni sequenza) e conta, per famiglia e in totale, quante sequenze l'analista trova coerenti. Con 3 sequenze per famiglia non è una stima precisa, ed è scritto.

---

## 5. `src/oppreport.py` (109 righe): un comando per tutto

**Si lancia:**
- dati StatsBomb: `python src/oppreport.py --statsbomb matches/9_281.json --data-dir <cartella> --team "Bayer Leverkusen" --out reports`
- altro fornitore: `python src/oppreport.py --csv eventi.csv --team "LASK" --out reports`

**Passo per passo:**
1. Controlla che tu abbia dato **uno solo** tra `--csv` e `--statsbomb`.
2. Se è un CSV, lo converte con `adapters/generic_csv.py` in una cartella `_work`.
3. Se è StatsBomb, controlla che la squadra giochi in quell'elenco e che ci siano gli eventi di **tutte** le partite. Se ne mancano, si ferma e scrive il comando esatto per scaricarli.
4. Lancia le schede una dopo l'altra (lista `SHEETS`). Le prime quattro (report, restarts, set pieces, transitions) devono riuscire; le altre quattro (defending, matchups, keyplayers, xthreat) hanno bisogno di eventi StatsBomb e, se falliscono, vengono saltate con un messaggio.
5. Fa la pagina di preparazione (`summary.py`) e copia tutti i file nella cartella `--out`.

Con `--video-offsets offsets.csv` la lista delle clip ha anche il tempo nel video.

---

## 6. `src/adapters/`: altri fornitori di dati

### `generic_csv.py` (254 righe)
Legge un CSV semplice (una riga per evento) e lo riscrive **come se fosse StatsBomb**, così tutto il resto del codice funziona uguale.
- Colonne obbligatorie: partita, data, squadre, tempo, minuto, secondo, squadra, tipo di evento, x, y. Facoltative: fine dell'azione, possesso, ripartenza, giocatore, ricevente, xG, esito del passaggio.
- `validate()` (L40): controlla il file e dice cosa manca (`--validate-only` fa solo questo).
- `new_possessions()` (L81): se il CSV non ha i numeri di possesso, li ricostruisce: nuovo possesso quando cambia il tempo, a ogni ripartenza, o quando l'altra squadra fa 2 azioni di fila (o tira). Un tocco solo dell'altra squadra (un rinvio) non basta.
- `play_pattern()` (L122): ripartenza → play pattern StatsBomb ("From Goal Kick", ...).
- `to_event()` (L128): una riga del CSV → un evento in formato StatsBomb (coordinate portate a 120 × 80).
- `convert()` (L174): fa tutto e scrive `matches/generic.json` e `ev/<id>.json`.

**Se ti chiedono** "funziona davvero?": sì, con il test di andata e ritorno (sezione 7). Con i possessi originali le sequenze escono identiche; con quelli ricostruiti i numeri si spostano un po' (passaggi per sequenza 8.3 contro 9.3).

### `wyscout_to_generic_csv.py` (192 righe)
Trasforma i dati pubblici Wyscout (Pappalardo et al. 2019) nel CSV generico. Le regole sono in cima al file: coordinate già 0-100 e nella direzione giusta; tempo dal secondo dell'evento; Pass → pass, Acceleration → carry; i tag dicono gol (101), autogol (102), passaggio riuscito (1801) o no (1802); i rinvii dal fondo partono da un punto finto e vengono spostati nell'area piccola.
`event_type()` (L43) traduce il tipo; `main()` (L63) fa la conversione (con `ALL` converte un campionato intero, che serve per la media del campionato nel voto).

### `statsbomb_to_generic_csv.py` (83 righe)
Il contrario: StatsBomb → CSV generico. Serve solo per il test di andata e ritorno e come esempio di come si mappa un fornitore. `--no-possession` toglie i numeri di possesso, per vedere quanto conta ricostruirli.

---

## 7. `tests/`: i controlli

- **`reproduce_results.py`**: rilancia le analisi della tesi in una **cartella separata** e confronta tutti i risultati con `results/`. Devono essere **identici** (51 su 51). Non scrive niente in `results/`. Da fare prima di riportare un numero al professore.
- **`reproduce_sheets.py`**: lo stesso per le schede (difesa, matchup, giocatori, transizioni, xT): 50 su 50 identiche. Collega gli eventi alla cartella temporanea invece di copiarli (`link()`).
- **`test_adapter_roundtrip.py`**: StatsBomb → CSV → di nuovo StatsBomb (`run()`), poi estrae le sequenze. Con i possessi deve riprodurre almeno il 99% delle sequenze, altrimenti fallisce. Controlla anche ripartenze, palle inattive, transizioni e parte della difesa.
- **`test_app_api.py`**: carica l'app sugli esempi e controlla che ogni squadra si apra, che le classifiche siano uguali ai file, che le clip e l'export CSV corrispondano riga per riga, che il foglio di revisione si salvi senza toccare l'originale e che i gol siano uguali ai risultati veri.
- **`test_all_teams.py`**: chiama ogni pagina dell'app per ogni squadra. Nessuna deve dare un errore del server o un JSON con NaN.
- **`check_clips.py`**: per ogni clip apre il replay e controlla che inizi al minuto giusto, abbia gli stessi passaggi, la stessa durata e il tiro quando la lista dice tiro.
- **`check_replays.py`**: controlla che i replay non disegnino cose strane (azioni fuori dal campo, punti finti in un angolo, passaggi lunghi zero).

---

## 8. `app/`: l'app web

### `app/run.py` (53 righe)
Avvia l'app su http://127.0.0.1:8765. `--data-dir` sceglie la cartella delle squadre (di default `examples/`), `--wyscout-dir` aggiunge Wyscout, `--lan` la rende visibile agli altri computer della rete. Il frontend va compilato una volta (`npm run build`).

### `app/backend/server.py` (~1300 righe): il "cameriere" dell'app
Quando la pagina chiede qualcosa, legge i file prodotti dalla pipeline e li manda. **Non calcola stime nuove.** È scritto con FastAPI: ogni funzione con `@app.get("/api/...")` è un indirizzo che la pagina può chiamare.
- In cima: le due fonti dati (`PROVIDERS`: StatsBomb e Wyscout, mai mischiate). `pick_provider()` legge quale vuole la pagina.
- `teams()`: tutte le squadre della cartella (dai file `report_*.json`). Sotto 8 partite (`MIN_MATCHES`) una squadra è "provvisoria": niente classifica.
- `ranks()`: per ogni numero, la posizione della squadra tra le altre, con il voto A-D accanto (letto da `results/evidence_grade_*.json`).
- Gli indirizzi principali:
  - `/api/teams` e `/api/teams/{key}`: elenco squadre e tutti i numeri di una squadra;
  - `/api/evidence`: i voti;
  - `/api/teams/{key}/replay` (e `replay.gif`): le azioni di un possesso, lette dagli eventi grezzi, per disegnare il replay;
  - `/api/teams/{key}/clips/{kind}` ed `export/{kind}.csv`: le liste di clip, filtrate;
  - `/api/teams/{key}/paths`, `pressing`, `network`, `similar`: tutte le sequenze di una famiglia, la mappa del pressing, la rete di passaggi, le sequenze più simili;
  - `/api/stylemap`: tutte le squadre su una mappa (le prime due componenti principali dei numeri);
  - `/api/teams/{key}/gameplan`, `without`: il piano partita e il confronto con e senza un giocatore (da `gameplan.py`);
  - `/api/teams/{key}/review` (GET e POST): il foglio di revisione nell'app;
  - `/api/sources` e `/api/jobs`: aggiungere una squadra nuova (scarica gli eventi e lancia `oppreport.py` in background).
- `SafeJSON` / `_finite()`: trasforma NaN e infinito in `null`, perché il JSON non li accetta (squadre con 2 partite).

### `app/backend/gameplan.py` (655 righe): il piano partita
**Spunti, non consigli.** Regole fisse: se la squadra è tra le prime k o le ultime k per un numero (k = n/5, almeno 4 squadre), scatta uno spunto su **dove guardare** nel video, con i numeri che l'hanno fatto scattare. Nessuna regola è stata testata per vedere se seguirla fa vincere.
- `build()` (L197): moduli, stile e spunti contro l'avversario (e contro la tua squadra, se la scegli).
- `brief()` (L334): gli stessi spunti come piano per fase (con palla, senza palla, transizioni, palle inattive) e tre priorità. Testi fissi, nessun modello di IA.
- `watch_first()` (L362): quali loro partite guardare per prime: quelle contro avversari che difendevano più come la tua squadra.
- `pressure_zones()`, `pressure_hint()`: dove soffrono il pressing (precisione sotto pressione per zona contro le altre squadre).
- `without()` (L469): partite con e senza un giocatore titolare.
- `foul_zones()`, `breaks()`: zone dei falli e mappa dei recuperi.
- `versus()` (L581): la previsione per la prossima partita contro la tua squadra (RQ2, approssimata).
- `FORM()`: '4231' → '4-2-3-1'.

### `app/frontend/`: la parte grafica (React + TypeScript)
- `src/main.tsx`: punto di partenza, monta l'app nella pagina.
- `src/App.tsx`: la barra in alto, la navigazione e quale pagina mostrare (indirizzo `#/<squadra>/<sezione>`). Due viste: "analyst" (solo quello che serve a preparare la partita) e "full" (tutto).
- `src/api.ts`: i tipi dei dati e le chiamate al server (`api.team()`, `api.clips()`, ...).
- `src/charts.tsx`: i pezzi grafici riusati ovunque (campo, nastri colorati delle famiglie, voti, icone, "How to read").
- `src/format.ts`: arrotonda come le schede (percentuali, "3rd highest of 10").
- `src/i18n.ts` + `src/i18n-dict.ts`: le lingue. L'app è scritta in inglese; un `MutationObserver` guarda il testo della pagina e lo sostituisce con l'italiano o il tedesco del dizionario (`#` = un numero, `{0}` = un testo qualsiasi). Un testo nuovo senza voce nel dizionario resta in inglese.
- `src/provider.ts`: StatsBomb o Wyscout, ricordato in un cookie.
- `src/useClips.ts`: scarica le liste di clip una volta per sessione.
- `src/styles.css`: lo stile.
- `src/views/`, una pagina per file:

| file | pagina |
|---|---|
| `Overview.tsx` | il riassunto: replay, 5 punti chiave dove la squadra è più estrema, famiglie, quanto fidarsi |
| `GamePlan.tsx` | il piano partita (spunti, moduli, tu contro loro, partite da guardare) |
| `CoachSheet.tsx` | una pagina A4 per l'allenatore, dagli stessi numeri del piano |
| `Evidence.tsx` | i voti A-D e da cosa dipendono |
| `Families.tsx` | le famiglie (quote, replay, ogni numero per famiglia) |
| `Threat.tsx` | la pericolosità (xT) |
| `Restarts.tsx`, `PressingMap.tsx` | le ripartenze; dove va il primo passaggio e chi lo riceve |
| `SetPieces.tsx` | angoli e punizioni |
| `Goals.tsx`, `GoalToggle.tsx` | tutti i gol con replay; l'interruttore "solo gol" |
| `Transitions.tsx` | palle perse e recuperate |
| `Defending.tsx` | come difende |
| `Clips.tsx`, `VideoSync.tsx` | le liste di clip con filtri ed export CSV; il video della partita accanto al replay |
| `MoreLikeThis.tsx` | le sequenze più simili a quella scelta |
| `Compare.tsx` | due squadre sulla stessa scala |
| `StyleMap.tsx` | tutte le squadre su una mappa |
| `Matchups.tsx` | contro chi va meglio o peggio, con e senza un giocatore |
| `Review.tsx` | il foglio di revisione per l'analista |
| `NewTeam.tsx` | aggiungere una squadra |

---

## 9. `archive/`: quello che non serve più

Codice già usato una volta, o tolto per tenere la tesi sulle sue domande. Non serve per rifare i numeri della tesi, ma resta qui (e nella storia git), così ogni risultato ha ancora il suo codice.

| file | cosa faceva |
|---|---|
| `choose_k.py` | ha scelto il numero di famiglie (k = 5 e 3) sulle partite di esplorazione |
| `select_and_replicate.py` | ha estratto a sorte le 6 squadre nuove e ha fatto il primo lancio della replica |
| `smoke_grade.py` | prove del codice del voto prima del test vero (solo conteggi) |
| `evidence_provider.py`, `exploratory_provider_samematch.py` | il confronto StatsBomb contro Wyscout sulle stesse 36 partite del Barcellona |
| `clips_to_mp4.py` | taglia clip MP4 da un video |
| `clips_to_xml.py` | lista di clip → XML per Sportscode/Nacsport (mai provato in un programma vero; tolto il 6 nov) |
| `ai_brief.py` | il brief per l'allenatore scritto da un modello locale (Ollama); tolto il 6 nov |
| `tracking/` | i dati di tracking DFL: `dfl_load.py`, `pitch_control.py`, `ghosting.py` (LSTM contro modelli semplici: la regressione lineare vinceva), `app_tracking.py` (la vecchia pagina Tracking lab). Esplorativo, altre partite; tolto il 6 nov. I risultati restano in `results/exploratory_*.json` |

---

## 10. Parole difficili, in una riga

| parola | vuol dire |
|---|---|
| evento | una cosa che succede in partita (passaggio, tiro, ...) con posizione e tempo |
| possesso | il periodo in cui una squadra ha la palla (numerato da StatsBomb) |
| play pattern | come è iniziato il possesso (gioco normale, rinvio, rimessa, angolo, ...) |
| K-Means | l'algoritmo che divide le sequenze in k gruppi di numeri simili |
| silhouette | quanto i gruppi sono separati (da −1 a 1; vicino a 0 = gruppi che si toccano) |
| Jaccard | quanto un gruppo si ritrova uguale rifacendo l'analisi (1 = identico) |
| ARI | quanto due divisioni in gruppi sono d'accordo (1 = identiche) |
| regressione logistica | il modello che dà la probabilità di ogni famiglia (o del tiro) |
| log-loss | quanto una previsione sbaglia (più basso = meglio) |
| guadagno | log-loss di base − log-loss del modello; positivo = il modello è meglio |
| bootstrap | ripescare i dati a caso tante volte per vedere quanto un numero può cambiare |
| IC95 | l'intervallo in cui sta il numero vero con 95% di fiducia |
| Wilson | l'intervallo per una proporzione (es. 8 squadre su 10) |
| seme (seed) | il numero che fissa il caso: stessi numeri casuali ogni volta |
| permutazione | mescolare i dati per vedere cosa succede "per caso" |
| validazione incrociata | dividere le partite in gruppi, allenare su tutti meno uno, provare su quello, e girare |
| copula | dati finti con le stesse distribuzioni e correlazioni di quelli veri, ma senza gruppi |
| skill | quanto una previsione è migliore di quella di confronto (1 − errore/errore di confronto) |
| discriminazione (D) | quanto un numero distingue le squadre invece del rumore (vicino a 1 = molto) |
| xG | probabilità che un tiro diventi gol |
| xT | quanto una zona del campo è pericolosa; xT aggiunto = quanto un passaggio porta la palla in zone più pericolose |
| PPDA | passaggi concessi all'avversario per ogni azione difensiva (basso = pressing alto) |
| protocollo pre-registrato | il file con ipotesi e soglie, committato **prima** di lanciare il test |
