# Il codice aggiunto il 28 ottobre 2026, spiegato facile

Questo file spiega **tutto il codice scritto il 28 ottobre** per rispondere alle due domande di ricerca:
- **RQ1:** i voti A-D valgono anche con dati Wyscout?
- **RQ2:** si prevede meglio la prossima partita se si guarda **contro chi** si gioca e **dove**?

Sono **4 file di codice modificati** e **2 nuovi**, più protocolli e risultati.

| File | Nuovo o modificato | A cosa serve | Domanda |
|---|---|---|---|
| `src/adapters/wyscout_to_generic_csv.py` | modificato | traduce Wyscout nel nostro formato, ora anche le azioni difensive | RQ1 |
| `src/adapters/generic_csv.py` | modificato | legge il formato comune, ora capisce le azioni difensive | RQ1 |
| `src/adapters/statsbomb_to_generic_csv.py` | modificato | esporta StatsBomb nel formato comune (serve per il test) | RQ1 |
| `tests/test_adapter_roundtrip.py` | modificato | controlla che le modifiche non abbiano rotto niente | RQ1 |
| `src/week4/evidence_grade_wyscout.py` | **nuovo** | calcola i voti su Wyscout e li confronta con StatsBomb | RQ1 |
| `src/week4/forecast_opponent.py` | **nuovo** | la "previsione furba" con avversario e campo | RQ2 |

---

## Parte 1: gli adapter (i "traduttori")

### Il problema
StatsBomb e Wyscout scrivono le partite in modo diverso, come due persone che fanno la cronaca in due lingue. Il nostro programma capisce **una sola lingua**: il "CSV generico" (descritto in `docs/data_format.md`).

L'adapter è il **traduttore**: Wyscout → CSV generico → programma.

Prima del 28 ottobre il traduttore conosceva solo le azioni **con la palla**: passaggio, conduzione, tiro, dribbling. Mancavano le azioni **difensive**, quindi non si poteva calcolare il **PPDA** né l'**altezza della difesa**. Mancava anche se un passaggio era **riuscito o sbagliato**, che serve per l'xT.

### 1a. `wyscout_to_generic_csv.py`: cosa è stato aggiunto

**Le azioni difensive.** Wyscout usa dei "tag" numerici. La traduzione:

| Nel nostro formato | In Wyscout |
|---|---|
| `interception` (intercetto) | qualsiasi evento con tag **1401** |
| `duel` (contrasto) | "Ground defending duel", oppure "Air duel" **perso** (tag 701) |
| `foul` (fallo) | Foul, Hand foul, Late card foul, Out of game foul, Violent Foul |
| `clearance` (rinvio) | "Clearance" |

Perché il duello aereo solo se perso? Perché StatsBomb fa così (il suo "Duel" = contrasti e duelli aerei persi). Vogliamo contare le stesse cose.

**Un dettaglio furbo sugli intercetti.** In Wyscout, a volte l'intercetto è "attaccato" a un passaggio: il giocatore intercetta e passa subito, un solo evento. Se lo traducessimo solo come passaggio, l'intercetto si perderebbe. Allora il codice scrive **due righe**: il passaggio, e subito dopo una riga "interception".

```python
if etype in ("pass", "carry", "shot") and 1401 in tags:
    rows.append(dict(rows[-1], event_type="interception", ...))
```

**Esito del passaggio.** Tag 1801 = riuscito → `complete`; tag 1802 = sbagliato → `incomplete`.

**Tutto il campionato in una volta.** Prima si convertiva una squadra alla volta. Ora con la squadra `ALL` si converte **l'intero campionato**. Serve perché il voto confronta ogni squadra con la **media del campionato**, quindi servono tutte le squadre.

Queste regole sono scritte nell'intestazione del file **prima** di confrontare qualsiasi numero con StatsBomb.

### 1b. `generic_csv.py`: cosa è stato aggiunto

È il file che legge il CSV generico e lo trasforma nel formato interno (che assomiglia a StatsBomb).

Aggiunto un dizionario che dice come chiamare le azioni difensive, **con gli stessi nomi di StatsBomb**:

```python
DEFT = {"duel": "Duel", "interception": "Interception", "foul": "Foul Committed",
        "clearance": "Clearance", "ball_recovery": "Ball Recovery", "block": "Block"}
```

Così il resto del programma (`defending.py`, che calcola il PPDA) **non è stato toccato**: riceve gli stessi nomi di sempre.

Aggiunta anche la colonna facoltativa `pass_outcome`: se c'è scritto `incomplete`, il passaggio è segnato come sbagliato.

**Importante:** le azioni difensive **non** aprono una nuova possessione. Quindi le sequenze di gioco, e i vecchi risultati, restano identici.

### 1c. `statsbomb_to_generic_csv.py`
Fa il viaggio inverso: StatsBomb → CSV generico. Ora esporta anche le azioni difensive e l'esito dei passaggi. Serve solo per il test qui sotto.

### 1d. Il test: `tests/test_adapter_roundtrip.py`
**Idea del test ("andata e ritorno"):**
1. prendo le partite StatsBomb;
2. le traduco nel CSV generico;
3. le rileggo con `generic_csv.py`;
4. calcolo i numeri e li confronto con quelli calcolati direttamente da StatsBomb.

Se il traduttore funziona, i numeri devono essere **uguali**. È come tradurre un testo in inglese e poi di nuovo in italiano: se torna uguale, la traduzione è buona.

Aggiunto il controllo della parte difensiva: passaggi avversari, azioni difensive alte, numero di azioni difensive, loro altezza, tiri concessi.

**Risultato:** 38 partite su 38 identiche. Anche tutti i vecchi controlli sono identici (es. 1867 sequenze su 1867).

---

## Parte 2: `evidence_grade_wyscout.py` (RQ1)

### Cosa fa, in una frase
Rifà **gli stessi voti A-D** sui dati Wyscout, **con lo stesso codice** di StatsBomb, e poi confronta le lettere.

### Perché non è stato riscritto il metodo
Il file **non ricalcola niente da solo**: importa `evidence_grade.py` (il codice dei voti originale) e lo usa così com'è.

```python
import evidence_grade as E
```

Se avessimo riscritto il calcolo, qualcuno potrebbe dire "hai cambiato il metodo". Invece il metodo è **lo stesso file**, cambiano solo i dati.

### Le parti del file, una per una

**1. Le affermazioni non testabili.** Wyscout non ha le **pressioni** né l'**xG**. Quindi 5 affermazioni su 34 non si possono calcolare e vengono tolte:

```python
NOT_TESTABLE = {"D24": "needs pressures", "D25": "needs pressures", "A32": "needs pressures",
                "D28": "needs xG", "A30": "needs xG"}
```

**2. `all_teams`: trova le squadre.** Legge i 5 campionati (Inghilterra, Francia, Germania, Italia, Spagna) e per ogni squadra mette in ordine di data le sue partite. Risultato: 98 squadre.

**3. `extract`: calcola i numeri partita per partita.** Per ogni squadra e ogni partita chiama `E.match_values` (codice originale) e salva tutto in un file `.pkl` per squadra (in `C:\Users\ecole\evidence_work\wyscout\teams`). Se una squadra è già fatta, la salta: così se il computer si spegne si riparte da dove si era.

**4. `load_teams`: rilegge i file.** Si ferma se due squadre hanno lo stesso nome (ad esempio due "Athletic" in due campionati): sarebbe un errore silenzioso.

**5. `compare`: il cuore della RQ1.** Per ogni affermazione mette accanto la lettera StatsBomb e la lettera Wyscout, e conta:
- **stessa lettera** (es. A e A);
- **distanza di una lettera** (es. B e C);
- **distanza di due o più** (es. A e C): questo sarebbe grave.

Poi applica la regola **scritta prima** nel protocollo:

```python
verdict = "hold" if share >= 0.70 and not far else ("partly hold" if share >= 0.50 else "do not hold")
```

In italiano:
- **reggono** se almeno il 70% ha la stessa lettera e nessuna è lontana due lettere;
- **reggono in parte** se almeno il 50%;
- altrimenti **non reggono**.

**6. `wilson`: l'intervallo di confidenza.** 21 su 29 è il 72%. Ma con solo 29 affermazioni il 72% è incerto. Wilson dà l'intervallo: [54%, 85%]. Vuol dire: "il valore vero sta probabilmente tra 54% e 85%".

**7. `kappa_linear`: l'accordo "vero".** Se le lettere fossero messe a caso, qualche volta coinciderebbero per fortuna. Il kappa toglie la fortuna: 0 = accordo da caso, 1 = accordo perfetto. È "lineare" perché A contro B pesa meno di A contro D. Risultato: **0.70**, un buon accordo.

**8. `guard`: il "lucchetto".** Prima di lanciare il test vero, il programma controlla:
- che il protocollo e il codice siano **committati**;
- che non siano stati **modificati dopo** il commit;
- che il commit sia **su GitHub** (pushato);
- che il file dei risultati **non esista già**.

Se uno di questi non va, il programma **si rifiuta di partire**. Così è impossibile lanciare il test due volte per avere un numero migliore, o cambiare le regole dopo.

### Le tre modalità
| Comando | Cosa fa |
|---|---|
| `smoke` | prova veloce su 2 squadre × 8 partite, stampa solo **conteggi**, mai valori (per non "sbirciare") |
| `extract` | calcola i numeri di tutte le 98 squadre |
| `analyse --set dev` | voti sulle 2 squadre di sviluppo (Barcellona, Napoli): solo controllo del codice |
| `analyse --set confirm` | **il test vero**, una volta sola, sulle altre 96 squadre |

Barcellona e Napoli sono tenute fuori dal test vero perché le avevamo già guardate prima: sarebbe stato "barare".

### Risultato (`results/evidence_grade_wyscout.json`)
21 su 29 stessa lettera, nessuna lontana due lettere, kappa 0.70 → **i voti reggono** (appena sopra la soglia del 70%).

---

## Parte 3: `forecast_opponent.py` (RQ2)

### L'idea, con un esempio
Oggi il programma prevede: *"il Napoli fa in media PPDA 9 → la prossima partita farà 9"*.

Ma se il Napoli gioca contro una squadra che **tiene tanto palla**, il PPDA sarà diverso. E in casa il Napoli pressa di più che fuori.

La previsione furba fa:

> **previsione = media del Napoli + effetto dell'avversario + effetto casa/fuori**

### I pezzi della formula (nel codice, funzione `rows`)

Per la squadra X, la partita t, contro l'avversario Y:

| Simbolo | Cosa è | Esempio |
|---|---|---|
| **F** | media di X nelle partite **già giocate** | Napoli finora: 9 |
| **L** | media del campionato finora | campionato: 10 |
| **A_Y** | cosa hanno fatto gli **avversari di Y** quando hanno giocato contro Y | contro Y le squadre fanno 12 |
| **A_Y − L** | quanto Y "cambia" chi lo affronta | 12 − 10 = +2 |
| **w_Y** | quanto fidarsi dell'effetto di Y: `n_Y / (n_Y + 5)` | Y ha giocato 10 partite → 10/15 = 0.67 |
| **V** | effetto casa: metà della differenza tra casa e fuori nel campionato | ±0.5 |

**F_adj = F + w_Y × (A_Y − L) ± V**

Esempio: 9 + 0.67 × 2 + 0.5 = **10.8** (Napoli in casa).

**Perché w_Y?** Se Y ha giocato solo 2 partite, il suo "effetto" è molto incerto. Con 2 partite w_Y = 2/7 = 0.29: usiamo solo un pezzetto dell'effetto. Con 30 partite w_Y = 30/35 = 0.86: ci fidiamo quasi del tutto. Il 5 (cioè k) dice quanto essere prudenti.

**Regola importante:** si usano **solo partite giocate prima** di quella da prevedere (`past = T[T.date < d]`). Non si "guarda nel futuro".

Ultima riga: se il numero è una percentuale, resta tra 0 e 1; altrimenti non va sotto 0.

### Come si misura se è meglio (funzione `improvement`)

> **miglioramento = 1 − (errore previsione furba) / (errore media semplice)**

- **+0.27** = la previsione furba sbaglia il 27% in meno;
- **0** = uguale;
- **negativo** = peggio.

L'intervallo al 95% si calcola col **bootstrap sulle squadre**: si rifà il calcolo 2000 volte pescando squadre a caso, e si vede quanto oscilla.
- Se tutto l'intervallo è sopra 0 → **meglio**.
- Se è tutto sotto 0 → **peggio**.
- Altrimenti → **nessuna differenza**.

### Le due fasi del file

**Fase `dev` (esplorativa, prima).** Sulle 9 squadre StatsBomb di sviluppo prova 5 valori di k (1, 3, 5, 10, 20), con e senza effetto casa. Sceglie **k = 5 con effetto casa** (il migliore). Risultato salvato come `exploratory_...`: non è un test, serve solo a scegliere.

**Fase `confirm` (il test vero, una volta).** Con k = 5 bloccato nel codice:

```python
K, VENUE = 5, True  # chosen in the development step
```

Gira su 70 squadre StatsBomb e su 96 Wyscout, **mai viste prima** con questa previsione. Anche qui c'è il lucchetto `guard`.

Regola scritta prima (funzione `confirm`):
- **aiuta** se è meglio in almeno il 50% delle affermazioni e peggio in al massimo il 10%;
- **aiuta per alcune** se meglio in almeno il 20%;
- altrimenti **non aiuta**.

### `regrade`: i voti cambiano?
Ricalcola il voto con la previsione furba al posto della media. La parte "distingue le squadre?" (discrimination) **non cambia**, perché non dipende dalla previsione. Cambia solo la parte "si ripete?".

### Risultato
| | StatsBomb (70 squadre) | Wyscout (96 squadre) |
|---|---|---|
| meglio | 21 su 30 | 18 su 25 |
| peggio | 2 | 1 |
| risposta | **aiuta** | **aiuta** |
| miglioramento mediano | +0.08 | +0.06 |
| PPDA | +0.27, voto da C ad A | +0.26, voto da C ad A |

Non aiuta per goal kick, portiere, rimesse e corner: lì conta come gioca la squadra stessa, non l'avversario.

---

## Parte 4: i documenti e i risultati

| File | Cosa è |
|---|---|
| `docs/protocol_evidence_grade_wyscout.md` | regole della RQ1, scritte e pushate **prima** del test |
| `docs/protocol_opponent_forecast.md` | regole della RQ2, scritte e pushate **prima** del test |
| `docs/data_format.md` | aggiunte le nuove colonne e la sezione difensiva Wyscout |
| `results/evidence_grade_wyscout_dev.json` | RQ1 su Barcellona e Napoli: solo controllo del codice |
| `results/evidence_grade_wyscout.json` | **RQ1, il risultato vero** |
| `results/exploratory_opponent_forecast_dev.json` | RQ2, scelta di k (esplorativo) |
| `results/opponent_forecast_statsbomb.json` | **RQ2 su StatsBomb** |
| `results/opponent_forecast_wyscout.json` | **RQ2 su Wyscout** |

L'ordine dei commit mostra la disciplina: **prima** il protocollo, **poi** il risultato.
```
b9677ab  feat:    adapter Wyscout con azioni difensive
4ce5f5a  docs:    protocollo RQ1          <- prima le regole
8d41a27  results: RQ1 sviluppo (2 squadre)
50c46a0  results: RQ1 vero (96 squadre)   <- poi il risultato
757cffa  feat:    previsione con avversario, sviluppo (esplorativo)
80552a6  docs:    protocollo RQ2          <- prima le regole
05f23f2  results: RQ2 vero                <- poi il risultato
```

---

## Parte 5: come rifare tutto (comandi)

Dalla cartella del repo, in PowerShell:

```powershell
# 1. Convertire un campionato Wyscout (esempio: Italia)
python -X utf8 src/adapters/wyscout_to_generic_csv.py C:\Users\ecole\wyscout_open\events_Italy.json C:\Users\ecole\wyscout_open\matches_Italy.json C:\Users\ecole\wyscout_open\teams.json C:\Users\ecole\wyscout_open\players.json "ALL" italy.csv
python -X utf8 src/adapters/generic_csv.py italy.csv C:\Users\ecole\wyscout_generic\Italy

# 2. Test andata e ritorno (deve finire con OK)
python -X utf8 tests/test_adapter_roundtrip.py <matches.json> "Barcelona" <cartella_dati>

# 3. RQ1: estrarre i numeri delle 98 squadre (lungo; salta quelle già fatte)
python -X utf8 src/week4/evidence_grade_wyscout.py extract C:\Users\ecole\wyscout_generic C:\Users\ecole\evidence_work\wyscout
```

I test veri (`analyse --set confirm` e `forecast_opponent.py confirm ...`) **non si possono rilanciare**: il file dei risultati esiste già e il lucchetto lo impedisce. È voluto.

---

## Limiti da dire sempre
- Wyscout non ha pressioni né xG: 5 affermazioni non testabili.
- Wyscout non ha le possessioni: sono ricostruite (un po' diverse da StatsBomb).
- I **valori** dei numeri sono diversi tra i due provider (es. PPDA del Barcellona 10.2 contro 4.5): è il **voto** che regge, non il valore.
- Cambiano insieme provider, stagione e squadre: se un voto cambia, non si sa per quale dei tre motivi.
- La previsione furba non guarda lo **stile** dell'avversario contro lo stile della squadra, solo la sua media; l'effetto casa è uguale per tutte le squadre di un campionato.
- Prevedere meglio non vuol dire che un analista prepari meglio la partita (servirebbe la RQ3).
