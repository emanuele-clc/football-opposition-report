# Starts the opposition-report app, after rebuilding and testing it.
# Usage (PowerShell, from the project folder):
#   powershell -ExecutionPolicy Bypass -File .\start_app.ps1
#   powershell -ExecutionPolicy Bypass -File .\start_app.ps1 -DataDir D:\other_data -Port 8770 -SkipTests
#   powershell -ExecutionPolicy Bypass -File .\start_app.ps1 -DataDir C:\Users\<user>\sbdata -WyscoutDir C:\Users\<user>\wyscout_app
# Steps: 1) stop an app already running on the same port  2) install what is missing  3) rebuild the frontend
#        4) clear the app cache (maps and networks are recomputed)  5) run the tests  6) start the app and open the browser
param(
    [string]$DataDir = $(if ($env:OPPREPORT_DATA) { $env:OPPREPORT_DATA } else { Join-Path $PSScriptRoot "examples" }),
    [string]$WyscoutDir = $(if ($env:OPPREPORT_DATA_WYSCOUT) { $env:OPPREPORT_DATA_WYSCOUT } else { Join-Path $PSScriptRoot "examples_wyscout" }),
    [int]$Port = 8765,
    [Alias("SaltaTest")][switch]$SkipTests,
    [switch]$Lan   # also reachable from staff tablets on the same Wi-Fi (no login: trusted networks only)
)
$ErrorActionPreference = "Continue"   # native tools write warnings to stderr: exit codes are checked instead
$env:PYTHONWARNINGS = "ignore"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
function Step($n, $text) { Write-Host ""; Write-Host "[$n/6] $text" -ForegroundColor Cyan }
function Fail($text) { Write-Host ""; Write-Host "ERROR: $text" -ForegroundColor Red; exit 1 }

if (-not (Test-Path $DataDir)) { Fail "data folder not found: $DataDir (use -DataDir)" }
$wy = @()
if (Test-Path $WyscoutDir) { $wy = @("--wyscout-dir", $WyscoutDir) } else { Write-Host "No Wyscout folder ($WyscoutDir): the app shows StatsBomb only" }

Step 1 "Stopping an app already running on port $Port"
$conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    foreach ($p in ($conn.OwningProcess | Sort-Object -Unique)) {
        try { Stop-Process -Id $p -Force -ErrorAction Stop; Write-Host "  stopped process $p" } catch { Write-Host "  could not stop process $p" }
    }
    Start-Sleep -Milliseconds 800
} else { Write-Host "  no app running" }

Step 2 "Checking Python and Node"
cmd /c "python -c ""import fastapi, uvicorn, pandas, matplotlib"" 2>nul"
if ($LASTEXITCODE -ne 0) {
    Write-Host "  installing the missing Python packages..."
    python -m pip install -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Fail "pip install failed" }
} else { Write-Host "  Python packages ok" }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Fail "Node.js/npm not found: install it from nodejs.org" }

Step 3 "Rebuilding the frontend"
Push-Location app\frontend
if (-not (Test-Path node_modules)) { Write-Host "  npm install (first time only)..."; cmd /c "npm install --no-audit --no-fund >nul 2>&1" }
cmd /c "npm run build >nul 2>&1"
$ok = $LASTEXITCODE
Pop-Location
if ($ok -ne 0) { Fail "frontend build failed (run 'cd app\frontend; npm run build' to see the error)" }
Write-Host "  frontend built"

Step 4 "Clearing the app cache"
foreach ($d in @($DataDir) + $(if ($wy.Count) { @($WyscoutDir) } else { @() })) {
    $cache = Join-Path $d "app_cache"
    if (Test-Path $cache) { Remove-Item -Recurse -Force $cache; Write-Host "  cache cleared in $d (maps are recomputed on first opening, a few seconds)" } else { Write-Host "  no cache in $d" }
}

if ($SkipTests) { Step 5 "Tests skipped (-SkipTests)" } else {
    Step 5 "Running the tests"
    $r1 = (cmd /c "python -X utf8 tests\test_app_api.py 2>nul" | Select-Object -Last 1)
    Write-Host "  repo examples:       $r1"
    $r2 = (cmd /c "python -X utf8 tests\test_app_api.py `"$DataDir`" 2>nul" | Select-Object -Last 1)
    Write-Host "  data folder:         $r2"
    if ($r1 -ne "ALL OK" -or $r2 -ne "ALL OK") { Fail "a test failed: run 'python -X utf8 tests\test_app_api.py $DataDir' for details" }
}

Step 6 "Starting the app on http://127.0.0.1:$Port (Ctrl+C to stop it)"
if ($Lan) { python -X utf8 app\run.py --data-dir $DataDir @wy --port $Port --lan } else { python -X utf8 app\run.py --data-dir $DataDir @wy --port $Port }
