# Avvia l'app del report sull'avversario, dopo averla ricostruita e testata.
# Uso (PowerShell, dalla cartella del progetto):
#   powershell -ExecutionPolicy Bypass -File .\avvia_app.ps1
#   powershell -ExecutionPolicy Bypass -File .\avvia_app.ps1 -DataDir D:\altri_dati -Port 8770 -SaltaTest
# Passi: 1) ferma l'app gia' accesa sulla stessa porta  2) installa cio' che manca  3) ricompila il frontend
#        4) svuota la cache dell'app (mappe e reti vengono ricalcolate)  5) esegue i test  6) avvia l'app e apre il browser
param(
    [string]$DataDir = "C:\Users\ecole\sbdata",
    [int]$Port = 8765,
    [switch]$SaltaTest
)
$ErrorActionPreference = "Continue"   # native tools write warnings to stderr: exit codes are checked instead
$env:PYTHONWARNINGS = "ignore"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
function Passo($n, $testo) { Write-Host ""; Write-Host "[$n/6] $testo" -ForegroundColor Cyan }
function Errore($testo) { Write-Host ""; Write-Host "ERRORE: $testo" -ForegroundColor Red; exit 1 }

if (-not (Test-Path $DataDir)) { Errore "cartella dati non trovata: $DataDir (usa -DataDir)" }

Passo 1 "Fermo l'app gia' accesa sulla porta $Port"
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($p in ($conn.OwningProcess | Sort-Object -Unique)) {
        try { Stop-Process -Id $p -Force -ErrorAction Stop; Write-Host "  fermato il processo $p" } catch { Write-Host "  impossibile fermare il processo $p" }
    }
    Start-Sleep -Milliseconds 800
} else { Write-Host "  nessuna app accesa" }

Passo 2 "Controllo Python e Node"
cmd /c "python -c ""import fastapi, uvicorn, pandas, matplotlib"" 2>nul"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  installo i pacchetti Python mancanti..."
    python -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Errore "pip install non riuscito" }
} else { Write-Host "  pacchetti Python ok" }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Errore "Node.js/npm non trovato: installalo da nodejs.org" }

Passo 3 "Ricompilo il frontend"
Push-Location app\frontend
if (-not (Test-Path node_modules)) { Write-Host "  npm install (solo la prima volta)..."; cmd /c "npm install --no-audit --no-fund >nul 2>&1" }
cmd /c "npm run build >nul 2>&1"
$ok = $LASTEXITCODE
Pop-Location
if ($ok -ne 0) { Errore "build del frontend non riuscita (esegui 'cd app\frontend; npm run build' per vedere l'errore)" }
Write-Host "  frontend compilato"

Passo 4 "Svuoto la cache dell'app"
$cache = Join-Path $DataDir "app_cache"
if (Test-Path $cache) { Remove-Item -Recurse -Force $cache; Write-Host "  cache svuotata (le mappe si ricalcolano alla prima apertura, qualche secondo)" } else { Write-Host "  nessuna cache" }

if ($SaltaTest) { Passo 5 "Test saltati (-SaltaTest)" } else {
    Passo 5 "Eseguo i test"
    $r1 = (cmd /c "python -X utf8 tests\test_app_api.py 2>nul" | Select-Object -Last 1)
    Write-Host "  esempi del repo:     $r1"
    $r2 = (cmd /c "python -X utf8 tests\test_app_api.py `"$DataDir`" 2>nul" | Select-Object -Last 1)
    Write-Host "  cartella dati:       $r2"
    if ($r1 -ne "ALL OK" -or $r2 -ne "ALL OK") { Errore "un test non e' passato: esegui 'python -X utf8 tests\test_app_api.py $DataDir' per i dettagli" }
}

Passo 6 "Avvio l'app su http://127.0.0.1:$Port (Ctrl+C per fermarla)"
python -X utf8 app\run.py --data-dir $DataDir --port $Port
