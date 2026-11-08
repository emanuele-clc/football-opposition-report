# Il codice spiegato su tre livelli

Aggiornato: 8 novembre 2026, dopo la semplificazione del codice (risultati verificati identici: `reproduce_results.py` 51/51, `reproduce_sheets.py` 50/50, voti A-D identici).

Per ogni file:
- **Livello 1, cosa fa:** la responsabilità del file in una frase.
- **Livello 2, come lavora:** i passaggi interni in ordine.
- **Livello 3, perché è fatto così:** le scelte principali e come giustificarle.

Prima i file della tesi (`src/analysis/`), poi il report (`src/report/`), gli adapter, l'app e i test.

---

## Le scelte che tornano in tutti i file

Valgono per quasi ogni file: conviene saperle a memoria.

- **Perché le partite in ordine di data e il taglio 70/30?** Il test deve imitare l'uso reale: un analista guarda le partite già giocate e prevede le prossime. Mescolare le partite a caso farebbe "vedere il futuro" al modello (data leakage) e darebbe risultati troppo ottimisti.
- **Perché lo StandardScaler?** K-Means usa la distanza euclidea. Senza scalare, le variabili con numeri grandi (metri percorsi, fino a 200) peserebbero molto più di quelle piccole (directness, tra −1 e 1). Così tutte e 11 contano allo stesso modo.
- **Perché il bootstrap sulle partite e non sulle sequenze?** Le sequenze della stessa partita si somigliano (stesso avversario, stesso punteggio, stesso campo). Ripescarle una per una farebbe credere di avere più informazione di quella vera, con intervalli troppo stretti. Ripescando partite intere si rispetta questa correlazione.
- **Perché semi casuali fissi (`random_state=0`, `default_rng(2026)`, ...)?** Ogni esecuzione dà esattamente gli stessi numeri: chiunque può rifare i risultati e controllarli (`tests/reproduce_results.py`).
- **Perché i protocolli committati prima?** Ipotesi e soglie sono scritte e pubblicate (git) prima di guardare i dati riservati. Così non si possono cambiare le regole dopo aver visto il risultato.

---

## 1. `src/analysis/`: le analisi della tesi

### `sequences_clustering.py`
**Livello 1.** Trasforma le partite di una squadra in una tabella di sequenze in gioco aperto, ognuna descritta da 11 numeri, e contiene le funzioni comuni a tutte le analisi.

**Livello 2.**
1. `extract()` legge l'elenco partite, tiene quelle della squadra in ordine di data e raggruppa passaggi, conduzioni, tiri e dribbling per numero di possesso.
2. `sequence_row()` scarta i possessi che non sono gioco aperto o hanno meno di 3 passaggi, poi calcola le 11 caratteristiche (inizio, fine, avanzamento, lunghezza del percorso, directness, passaggi, lanci lunghi, larghezza, durata).
3. Le funzioni comuni: `split()` (70/30), `fit_families()` (scaler + K-Means per fase, famiglie numerate per x di partenza), `assign()` (famiglia di ogni sequenza con modelli congelati), `context()` (gli ingressi del modello H1), `boot_ci()` (intervallo bootstrap per partite).

**Livello 3.**
- *Perché solo gioco aperto e almeno 3 passaggi?* Angoli e punizioni sono schemi preparati, non costruzione; con 1-2 passaggi non c'è un'azione da descrivere.
- *Perché `w0 = |y − 40|` e non y?* Interessa quanto l'azione è larga, non da che lato: così sinistra e destra contano uguale e le famiglie non si dividono per lato.
- *Perché le funzioni comuni in un solo file?* Prima erano copiate in 5-6 script. Un solo posto vuol dire che tutti usano esattamente le stesse impostazioni del protocollo (taglio 45, k = 5 e 3).

### `families.py`
**Livello 1.** Costruisce le famiglie di sequenze con K-Means sulle sole partite di esplorazione e ne misura profilo e stabilità.

**Livello 2.**
- `final`: per fase (costruzione x0 < 45, k = 5; avanzata, k = 3) scala, fa K-Means, numera le famiglie e calcola quota, profilo, tasso di tiro, stabilità Jaccard e i percorsi di 3 zone più frequenti; salva JSON, CSV e figura.
- `robustness`: rifà tutto con altri tagli (35-55), altri k, altri algoritmi (mistura gaussiana, Ward) e misura quanto cambia (ARI).
- `null` (test E1): confronta la stabilità vera con quella su due dataset senza gruppi (colonne mescolate e nuvola gaussiana).

**Livello 3.**
- *Perché le famiglie si numerano per x di partenza?* K-Means dà etichette casuali (0..k−1). Ordinarle per dove partono le rende confrontabili tra squadre e tra esecuzioni.
- *Perché il test con dati senza gruppi?* K-Means trova sempre k gruppi, anche nel rumore. Solo se le famiglie vere sono più stabili di quelle trovate nel rumore (margine ≥ 0.10) hanno una struttura reale.
- *Perché solo le partite di esplorazione?* Le partite riservate servono al test vero: se le usassi per scegliere il metodo, il test non sarebbe più su dati "mai visti".

### `validate_replication.py`
**Livello 1.** Esegue il test confermativo sul 30% di partite più recenti, con le famiglie allenate sul 70% e congelate (ipotesi H1, H2, H3).

**Livello 2.**
1. Controlla i flag: senza `--confirm` o `--dry-run` si ferma.
2. Estrae le sequenze, divide 70/30, allena le famiglie sul 70% e le applica congelate sul 30%.
3. **H2:** confronta le quote delle famiglie (scarto massimo ≤ 10 punti) e la silhouette delle famiglie congelate sul test (≥ 0.10).
4. **H1:** una regressione logistica (play pattern, minuto, tempo, famiglia precedente) prevede la famiglia; il guadagno in log-loss rispetto alle sole quote ha un IC95 bootstrap per partite e deve stare tutto sopra 0.
5. **H3:** la famiglia aiuta a prevedere il tiro rispetto al tasso medio?
6. Salva `holdout_<Squadra>.json`.

**Livello 3.**
- *Perché il flag `--confirm` / `--dry-run`?* Per impedire di aprire le partite riservate per sbaglio o più volte. Il dry-run prova il codice solo sulle partite di esplorazione; il test vero si fa una volta, dopo aver committato il protocollo.
- *Perché congelare le famiglie?* Se rifacessi K-Means sul test, le famiglie si adatterebbero ai dati nuovi e il test non direbbe niente. Congelate, si misura se lo stesso modello funziona su partite future.
- *Perché il log-loss e non l'accuratezza?* Il log-loss premia le probabilità ben calibrate e punisce molto le previsioni sicure e sbagliate; l'accuratezza guarda solo la classe più probabile.
- *Perché C = 0.5?* Un po' di regolarizzazione evita che il modello si adatti troppo alle partite di allenamento; il valore è fissato nel protocollo, non scelto dopo.

### `compare_simple_rules.py`
**Livello 1.** Controlla se le famiglie prevedono i tiri meglio di una regola banale con una sola variabile (dove finisce la sequenza).

**Livello 2.** Allena famiglie e fasce di x1 (stesso numero di celle, fasce con lo stesso numero di sequenze) sulle partite di esplorazione; usa lo stesso modello logistico su entrambe; confronta il log-loss sulle riservate con IC95 bootstrap per partite; verdetto per fase.

**Livello 3.**
- *Perché confrontarsi con una regola banale?* Un metodo complicato va giustificato: se una sola variabile fa altrettanto bene, le famiglie non aggiungono informazione sul tiro. Il risultato (0 squadre su 10) è negativo ed è dichiarato.
- *Perché fasce a uguale frequenza?* Ogni cella ha lo stesso numero di sequenze, come succede più o meno con le famiglie: il confronto è alla pari.

### `sample_size.py`
**Livello 1.** Misura quante partite servono perché i numeri del report siano vicini a quelli della stagione intera.

**Livello 2.** Calcola i numeri della stagione; pesca 3, 5, 8, 10, 15 partite a caso (500 volte); misura l'errore (90° percentile) rispetto alla stagione; salva per ogni n.

**Livello 3.**
- *Perché il 90° percentile e non la media?* Interessa il caso sfavorevole: un analista vuole sapere quanto può sbagliare nel 90% dei casi, non in media.
- *Perché è solo descrittivo?* Non c'è un'ipotesi da accettare o rifiutare: serve a dire nel report "con meno di N partite questo numero è poco affidabile".

### `ten_teams.py`
**Livello 1.** Lancia un'analisi su tutte le 10 squadre e stampa il riepilogo con la regola del protocollo (almeno 7 su 10).

**Livello 2.** `run` esegue uno script per ogni squadra (saltando quelle già fatte e salvando i log); `summary` legge i risultati, conta quante squadre passano e calcola l'intervallo di Wilson.

**Livello 3.**
- *Perché l'intervallo di Wilson?* Con 10 squadre una proporzione (8 su 10) è molto incerta; Wilson dà un intervallo corretto anche con campioni piccoli ([0.49, 0.94]).
- *Perché salta le squadre già fatte?* Il test confermativo si fa una volta: rilanciarlo per avere un numero migliore non è permesso.

### `exploratory_clusters.py` (esplorativo)
**Livello 1.** Controlla se le famiglie sono gruppi veri o fette di un continuo, e quanto dipendono dal metodo.

**Livello 2.** `copula`: crea 100 dataset con le stesse distribuzioni e correlazioni ma senza gruppi e confronta silhouette e stabilità. `methods`: K-Means contro mistura gaussiana e Ward, e altri k e tagli.

**Livello 3.**
- *Perché la copula gaussiana?* Tiene uguali le distribuzioni di ogni variabile e le loro correlazioni, toglie solo i gruppi. Se i dati veri non sono più "a gruppi" di questi, le famiglie sono solo un modo di tagliare un continuo (il risultato della tesi).
- *Perché "esplorativo"?* Non era nel protocollo: lo si dice, e non si usano questi risultati per cambiare il metodo.

### `exploratory_predictability.py` (esplorativo)
**Livello 1.** Misura da dove viene la prevedibilità della famiglia, usando tutte le partite.

**Livello 2.** Validazione incrociata per partite (6 gruppi); dentro ogni giro le famiglie si rifanno sulle partite di allenamento. `cv` = guadagno del modello H1; `ablation` = tolgo un ingrediente alla volta; `context` = a parità di play pattern, minuto, punteggio o casa/trasferta aiutano?

**Livello 3.**
- *Perché rifare le famiglie dentro ogni giro?* Se le famiglie fossero fatte su tutte le partite, la partita di test avrebbe già "insegnato" le famiglie: sarebbe una fuga di informazione.
- *Cosa si è scoperto?* Quasi tutto il guadagno viene da come inizia la sequenza (play pattern); il resto non aggiunge niente.

### `corners.py`
**Livello 1.** Verifica se una difesa può sfruttare dove una squadra manda i suoi angoli (L3).

**Livello 2.** Zona di arrivo dell'angolo, xG generati, disposizione difensiva dai dati 360; guadagno della disposizione migliore per zona; test di permutazione (1000 rimescolamenti). Leverkusen da solo, poi tre tornei insieme con scelta su due e test sul terzo.

**Livello 3.**
- *Perché il test di permutazione?* Con pochi angoli e pochi gol una formula classica non regge; rimescolando gli xG si vede quanto guadagno dà il puro caso.
- *Perché scegliere su Euro 2020 + Mondiale e provare su Euro 2024?* Stessa logica del 70/30: la disposizione migliore scelta sui dati vecchi deve funzionare su dati nuovi.
- *Come leggere p = 0.17 e 0.41?* Nullo debole: il test aveva poca potenza, solo effetti enormi sarebbero emersi.

### `evidence_grade.py` (RQ1, il contributo principale)
**Livello 1.** Dà un voto da A a D a ognuno dei 34 tipi di frase del report, in base a quanto si può fidarsi di quel numero.

**Livello 2.**
1. `extract`: per ogni squadra e partita calcola numeratore e denominatore di ogni frase, usando gli stessi script del report (importati); un file per squadra.
2. `analyse`: dalla 6ª partita in poi, tre previsioni della partita successiva: stagione finora (F), media del campionato (B), ultime 5 (L).
3. Skill = 1 − errore(F) / errore(B), con IC95 ripescando squadre; discriminazione D = 1 − rumore dentro la squadra / varianza tra squadre.
4. `grade()`: A = previsione forte e discriminazione alta, B = entrambe sufficienti, C = una sola, D = nessuna.
5. `guard()` blocca il lancio confermativo se protocollo e script non sono committati e pushati o se il risultato esiste già.

**Livello 3.**
- *Perché la media del campionato come confronto?* È quello che un analista saprebbe senza guardare la squadra. Se la stagione della squadra non prevede meglio, quel numero non dice niente di specifico su di lei.
- *Perché gli stessi script del report?* Il voto deve valere per i numeri che il report scrive davvero, non per una versione ricalcolata a parte.
- *Perché ripescare squadre per l'intervallo della skill?* Le previsioni della stessa squadra sono correlate; l'unità indipendente è la squadra.
- *Perché `guard()`?* La regola "una volta sola, dopo il protocollo" non è affidata alla memoria: è scritta nel codice.

### `evidence_grade_wyscout.py` (RQ1, secondo fornitore)
**Livello 1.** Rifà i voti A-D sui dati Wyscout 2017/18 e li confronta lettera per lettera con quelli StatsBomb.

**Livello 2.** Converte i campionati con gli adapter, estrae e analizza con il codice di `evidence_grade.py` (importato), toglie le frasi che Wyscout non può calcolare (pressioni, xG), poi confronta le lettere con kappa lineare e intervallo di Wilson.

**Livello 3.**
- *Perché un secondo fornitore?* Se i voti dipendessero da come StatsBomb registra gli eventi, non direbbero niente sul calcio. Stessa lettera in 21 frasi su 29: i voti reggono.
- *Perché la kappa e non la sola percentuale?* Una parte dell'accordo può venire dal caso; la kappa lo toglie.

### `forecast_opponent.py` (RQ2)
**Livello 1.** Verifica se una previsione che tiene conto dell'avversario e del campo batte la media stagionale della squadra.

**Livello 2.** F_adj = F + w_Y (A_Y − L) [± V]: si corregge la stagione della squadra con quanto l'avversario di solito concede rispetto al campionato, pesato per quante partite ha giocato, più il vantaggio casa. Si misura il miglioramento dell'errore con IC95 ripescando squadre; `dev` sceglie k e il campo, `confirm` è il lancio unico.

**Livello 3.**
- *Perché il peso w_Y = n/(n + k)?* A inizio stagione l'avversario ha poche partite e il suo valore è rumoroso: pesa poco. Con tante partite pesa di più (shrinkage).
- *Perché k scelto in `dev` sulle 9 squadre di sviluppo?* Così la scelta non usa le 70 squadre del test confermativo.

### `download_data.py`
**Livello 1.** Scarica i dati aperti StatsBomb di un campionato.

**Livello 2.** Elenco partite, filtro per squadra, poi eventi e file 360, 8 download alla volta.

**Livello 3.** *Perché salta i file sopra 100 byte?* Se il download si interrompe basta rilanciarlo; un file troncato o una pagina di errore sono quasi vuoti, un file vero pesa megabyte.

---

## 2. `src/report/`: le schede del report

Tutte le schede seguono lo stesso schema: `extract()` conta partita per partita, si somma sulla stagione con IC95 bootstrap per partite, si guardano le ultime 5, si scrivono pagina HTML, JSON (per l'app) e lista di clip.

*Perché le definizioni scritte in cima a ogni scheda?* Sono state fissate prima di guardare i risultati di qualunque squadra: così non si possono aggiustare dopo.

### `make_report.py`
**Livello 1.** Scrive il report principale: stile di gioco, famiglie e quanto fidarsi di ogni parte.

**Livello 2.** Estrae le sequenze; calcola lo stile con IC95 e il confronto con le altre squadre; famiglie per fase con stabilità e controllo di struttura; tabella "come inizia → in che famiglia finisce"; esempi per il foglio di revisione; lista di clip con il tempo nel video.

**Livello 3.**
- *Perché qui su tutta la stagione?* Il report descrive, non testa: le impostazioni sono già state validate sul 70/30.
- *Perché un solo generatore casuale per tutto il report?* L'ordine delle chiamate decide ogni intervallo: con un generatore unico il report è sempre identico.

### `restarts.py`
**Livello 1.** Descrive come la squadra riparte da rinvii, rimesse del portiere e rimesse laterali.

**Livello 2.** Per ogni possesso da ripartenza: primo passaggio (corto < 30 m o lungo, lato, ricevente) ed esito (metà avversaria, ultimo terzo, tiro, fine nella propria metà); quote stagione e ultime 5.

**Livello 3.** *Perché 30 m?* È la stessa soglia del "lancio lungo" del report: una definizione sola per tutte le schede.

### `setpieces.py`
**Livello 1.** Descrive angoli e punizioni nella metà offensiva.

**Livello 2.** Angoli: lato, zona di arrivo, battitore, ricevente, tiro, xG. Punizioni dall'ultimo terzo: tiro diretto, cross o gioco corto.

**Livello 3.** *Perché le stesse zone di `corners.py`?* Così la scheda è coerente con lo studio L3 e i numeri si possono confrontare.

### `transitions.py`
**Livello 1.** Mostra dove la squadra perde e recupera palla e cosa succede nei secondi dopo.

**Livello 2.** Ordina le azioni di entrambe le squadre nel tempo; palla persa = nostra azione seguita da almeno 2 azioni avversarie (o un loro tiro); contropressing entro 5 s; tiro entro 10 s; mappe per zona.

**Livello 3.** *Perché non usare i possessi StatsBomb?* StatsBomb non apre un nuovo possesso se la palla è persa e ripresa subito: con i possessi i recuperi erano circa 4%, un numero falso. L'ordine delle azioni funziona con qualunque fornitore.

### `defending.py`
**Livello 1.** Descrive come la squadra difende: intensità del pressing, dove, quanto alta, cosa concede.

**Livello 2.** Per partita: passaggi avversari nella loro zona, nostre azioni difensive lì (PPDA), pressioni per terzo, altezza delle azioni difensive, tiri e xG concessi.

**Livello 3.** *Perché il PPDA va letto con le pressioni nell'ultimo terzo?* Dipende anche da quanto l'avversario tiene palla: il Leverkusen ha il PPDA più alto ma anche la quota più alta di pressioni alte.

### `matchups.py`
**Livello 1.** Confronta i numeri della squadra contro avversari diversi (pressing alto o basso, difesa a 3/5 o a 4, casa o trasferta).

**Livello 2.** Numeri di ogni partita, divisione in due gruppi, differenza delle medie con IC95 bootstrap dentro ogni gruppo, verdetto "chiaro", "incerto" o "gruppo troppo piccolo" (meno di 6 partite).

**Livello 3.** *Perché "solo descrittivo"?* I gruppi sono piccoli e le partite differiscono in tante cose insieme: una differenza è uno spunto da guardare in video, non un consiglio.

### `keyplayers.py`
**Livello 1.** Indica i giocatori chiave per ruolo e la linea del tempo dei gol.

**Livello 2.** Primi 3 per ruolo (ricezioni in costruzione, ingressi nell'ultimo terzo, xG, palle inattive, palle perse nella propria metà); ogni gol con origine e quarto d'ora.

**Livello 3.** *Come sai che è giusto?* I gol della linea del tempo coincidono con i risultati veri delle partite per tutte le 10 squadre.

### `xt_model.py` e `xthreat.py`
**Livello 1.** `xt_model.py` costruisce una volta la griglia xT (quanto è pericolosa ogni zona); `xthreat.py` misura quanto la squadra porta palla in zone pericolose.

**Livello 2.** Griglia 16 × 12; per zona: probabilità di tiro, di gol e di dove va la palla dopo un movimento riuscito; si risolve xT = s·g + m·T·xT ripetendo finché non cambia più. Nella scheda: xT aggiunto = valore della zona di arrivo − valore della zona di partenza, per passaggi e conduzioni riusciti.

**Livello 3.**
- *Perché la griglia stimata una volta per tutti?* Ogni squadra è misurata con lo stesso "righello".
- *Perché non l'xT per famiglia?* Le famiglie avevano già perso il confronto con la regola semplice sui tiri: dividere l'xT per famiglia sarebbe un nuovo esito provato dopo aver visto quel risultato.

### `summary.py`, `summarize_review.py`, `common.py`
- `summary.py`: **cosa fa:** una pagina con i fatti principali di tutte le schede. **Come:** legge i JSON, calcola la posizione tra le altre squadre, segnala "controlla in video" quando le ultime 5 escono dall'intervallo. **Perché:** non calcola niente di nuovo, così non può contraddire le schede.
- `summarize_review.py`: **cosa fa:** conta le risposte sì / in parte / no dell'analista sul foglio di revisione. **Perché:** è l'unico controllo umano previsto; con 3 sequenze per famiglia è indicativo e lo dice.
- `common.py`: **cosa fa:** le piccole funzioni comuni alle schede (partite della squadra, avversario, terzo di campo, bootstrap, formati). **Perché:** una definizione sola, usata da tutte.

---

## 3. Adapter e comando unico

### `src/adapters/generic_csv.py`
**Livello 1.** Trasforma un CSV di eventi di qualunque fornitore in file nel formato StatsBomb.

**Livello 2.** Controlla le colonne (`validate`), ricostruisce i possessi se mancano, traduce ogni riga in un evento StatsBomb con coordinate 120 × 80, scrive elenco partite ed eventi.

**Livello 3.** *Perché tradurre verso StatsBomb e non riscrivere le analisi?* Tutto il resto del codice funziona uguale: per un nuovo fornitore basta mappare le colonne. Il test di andata e ritorno dimostra che con i possessi originali le sequenze escono identiche.

### `src/adapters/wyscout_to_generic_csv.py` e `statsbomb_to_generic_csv.py`
**Livello 1.** Il primo converte i dati pubblici Wyscout nel CSV generico; il secondo fa il contrario (StatsBomb → CSV) per il test di andata e ritorno.

**Livello 3.** *Perché documentare ogni scelta di mappatura?* I due fornitori definiscono gli eventi in modo diverso (es. rinvii da un punto finto): le differenze vanno dichiarate, non nascoste.

### `src/oppreport.py`
**Livello 1.** Un solo comando che produce tutto il report di una squadra.

**Livello 2.** Controlla gli argomenti, converte il CSV se serve, verifica che ci siano gli eventi di tutte le partite, lancia le schede in ordine, fa la pagina di preparazione e copia tutto nella cartella di uscita.

**Livello 3.** *Perché le schede difesa, matchup, giocatori e xT possono fallire senza fermare tutto?* Hanno bisogno di dati che non tutti i fornitori hanno (pressioni, xG): il report base esce comunque, con un messaggio chiaro.

---

## 4. L'app

### `app/run.py` e `start_app.ps1`
**Livello 1.** Avviano l'app in locale (`start_app.ps1` prima ricostruisce e testa).

**Livello 3.** *Perché testare ad ogni avvio?* L'app non si apre mai su una versione rotta o su dati sbagliati.

### `app/backend/server.py`
**Livello 1.** Risponde alle richieste della pagina leggendo i file prodotti dal report.

**Livello 2.** Fonti dati separate (StatsBomb, Wyscout), elenco squadre, classifiche con il voto A-D accanto, replay dagli eventi grezzi, liste di clip ed export, piano partita, foglio di revisione, aggiunta di una squadra.

**Livello 3.**
- *Perché non calcola stime nuove?* Ogni numero mostrato è lo stesso del report verificato: l'app non può dire cose diverse dalla tesi.
- *Perché StatsBomb e Wyscout mai mischiati?* I valori cambiano tra fornitori (RQ1): si confrontano solo dentro lo stesso fornitore.
- *Perché NaN diventa null?* Il JSON non accetta NaN: una squadra con 2 partite rompeva la pagina.

### `app/backend/gameplan.py`
**Livello 1.** Costruisce il piano partita: moduli, stile e spunti su dove guardare in video.

**Livello 2.** Uno spunto scatta se la squadra è tra le prime o le ultime k per un numero (k = n/5, almeno 4 squadre), con i numeri che l'hanno fatto scattare.

**Livello 3.** *Perché "spunti" e non "consigli"?* Nessuna regola è stata testata per vedere se seguirla fa vincere: dire di più sarebbe affermare più di quanto i dati sostengono.

### `app/frontend/` (React)
**Livello 1.** La parte grafica: una pagina per sezione del report.

**Livello 2.** `App.tsx` gestisce barra e navigazione, `api.ts` le chiamate al server, `charts.tsx` i pezzi grafici comuni, `views/` una pagina per file.

**Livello 3.** *Perché le traduzioni con un dizionario e non nel codice di ogni pagina?* L'app è scritta una volta in inglese; italiano e tedesco si aggiungono senza toccare le pagine.

---

## 5. `tests/`: i controlli

| file | cosa controlla | perché |
|---|---|---|
| `reproduce_results.py` | rifà le analisi in un'altra cartella: 51 risultati identici a `results/` | i numeri della tesi escono davvero dal codice pubblicato |
| `reproduce_sheets.py` | rifà le schede: 50 file identici | lo stesso per il report |
| `test_adapter_roundtrip.py` | StatsBomb → CSV → StatsBomb: almeno 99% delle sequenze uguali | l'adapter non cambia i dati |
| `test_app_api.py` | l'app sugli esempi: squadre, classifiche, clip, gol | l'app mostra gli stessi numeri dei file |
| `test_all_teams.py` | ogni pagina per ogni squadra: niente errori o NaN | nessuna squadra rompe l'app |
| `check_clips.py`, `check_replays.py` | ogni clip corrisponde al suo replay; niente disegni strani | quello che l'analista vede è giusto |

*Perché tanti test di riproducibilità?* Una volta è stato mandato al professore un numero sbagliato, poi corretto: da allora ogni numero si rifà da zero prima di riportarlo.
