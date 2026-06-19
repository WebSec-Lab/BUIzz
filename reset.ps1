<#
.SYNOPSIS
    BUIZZ teardown / reset.
    Undoes every persistent change the install scripts made, so you can
    re-run setup.ps1 / certs.ps1 / makeDB.py from a clean slate.

    It removes:
      1. the mkcert root CA from the Windows trust store
      2. the BUIZZ domain entries from the hosts file
      3. the distributed TLS .pem certs under server\
      4. the MySQL 'diffuserinter' database (12 leftover rows -> gone)

.PARAMETER FreshCA
    Also delete the mkcert CAROOT directory, so a brand-new root CA is
    generated the next time certs.ps1 runs (default: keep CAROOT, just
    untrust it).

.PARAMETER DbPassword
    MySQL root password (default: 1234, same as makeDB.py).

.EXAMPLE
    PowerShell -ExecutionPolicy Bypass -File reset.ps1
    PowerShell -ExecutionPolicy Bypass -File reset.ps1 -FreshCA
#>
param(
    [switch]$FreshCA,
    [string]$DbPassword = "1234"
)

#Requires -RunAsAdministrator

$ErrorActionPreference = "Continue"
$ScriptDir = $PSScriptRoot

# ── 1) mkcert root CA ───────────────────────────────────────────────────────
Write-Host "`n[1/4] Removing mkcert root CA from the trust store..." -ForegroundColor Cyan
if (Get-Command mkcert -ErrorAction SilentlyContinue) {
    mkcert -uninstall
    if ($FreshCA) {
        $caroot = (mkcert -CAROOT 2>$null).Trim()
        if ($caroot -and (Test-Path $caroot)) {
            Remove-Item -Recurse -Force $caroot
            Write-Host "    Deleted CAROOT: $caroot (a new CA will be created on reinstall)"
        }
    } else {
        Write-Host "    CAROOT kept; certs.ps1 will re-trust the same CA."
    }
} else {
    Write-Host "    mkcert not found in PATH; skipping."
}

# ── 2) hosts file ───────────────────────────────────────────────────────────
Write-Host "`n[2/4] Cleaning BUIZZ entries from the hosts file..." -ForegroundColor Cyan
$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$domains   = @("leak.test","adition.com","attacker.test","attacker.com","victim.com")

$inBuizzBlock = $false
$kept = Get-Content $hostsPath | Where-Object {
    $line = $_
    # drop the marked BUIZZ block, if present
    if ($line -match "# BUIZZ fuzzer domains") { $script:inBuizzBlock = $true; return $false }
    if ($script:inBuizzBlock) {
        if ($line -match "# END BUIZZ") { $script:inBuizzBlock = $false }
        return $false
    }
    # drop any bare line that maps one of our domains
    foreach ($d in $domains) {
        if ($line -match "(^|\s)$([regex]::Escape($d))(\s|$)") { return $false }
    }
    return $true
}
Set-Content -Path $hostsPath -Value $kept -Encoding ASCII
Write-Host "    Removed BUIZZ domain entries."

# ── 3) distributed TLS certs ────────────────────────────────────────────────
Write-Host "`n[3/4] Removing distributed TLS certs under server\..." -ForegroundColor Cyan
$pems = Get-ChildItem -Path (Join-Path $ScriptDir "server") -Recurse -Include *.pem -ErrorAction SilentlyContinue
if ($pems) {
    foreach ($p in $pems) { Remove-Item $p.FullName -Force; Write-Host "    deleted $($p.FullName)" }
} else {
    Write-Host "    none found."
}

# ── 4) MySQL database ───────────────────────────────────────────────────────
Write-Host "`n[4/4] Dropping MySQL database 'diffuserinter'..." -ForegroundColor Cyan
$mysql = "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"
if (Test-Path $mysql) {
    & $mysql -u root "-p$DbPassword" -e "DROP DATABASE IF EXISTS diffuserinter;"
    if ($LASTEXITCODE -eq 0) { Write-Host "    Dropped (if it existed)." }
    else { Write-Host "    mysql returned an error; drop manually: DROP DATABASE diffuserinter;" }
} else {
    Write-Host "    mysql.exe not at default path. Drop manually: DROP DATABASE diffuserinter;"
}

Write-Host "`n[Done] Reset complete." -ForegroundColor Green
Write-Host "Next: re-run the install from the example\ README:" -ForegroundColor Yellow
Write-Host "  PowerShell -ExecutionPolicy Bypass -File setup.ps1"
Write-Host "  PowerShell -ExecutionPolicy Bypass -File certs.ps1"
Write-Host "  pip install mysql-connector-python pywin32   # not covered by setup.ps1"
Write-Host "  python makeDB.py"
