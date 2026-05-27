# certs.ps1 — Install mkcert and distribute TLS certs to all BUIZZ servers
# Usage: PowerShell -ExecutionPolicy Bypass -File certs.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = $PSScriptRoot

function Ensure-Mkcert {
    if (Get-Command mkcert -ErrorAction SilentlyContinue) {
        Write-Host "[+] mkcert already installed: $(mkcert --version)"
        return
    }

    Write-Host "[-] mkcert not found. Attempting install..."

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "    Trying winget..."
        winget install FiloSottile.mkcert --silent --accept-package-agreements --accept-source-agreements
        if (Get-Command mkcert -ErrorAction SilentlyContinue) {
            Write-Host "[+] mkcert installed via winget."
            return
        }
    }

    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Host "    Trying Chocolatey..."
        choco install mkcert -y
        if (Get-Command mkcert -ErrorAction SilentlyContinue) {
            Write-Host "[+] mkcert installed via Chocolatey."
            return
        }
    }

    Write-Host "    Downloading mkcert directly from GitHub..."
    $release = Invoke-RestMethod "https://api.github.com/repos/FiloSottile/mkcert/releases/latest"
    $asset   = $release.assets | Where-Object { $_.name -like "*windows-amd64.exe" } | Select-Object -First 1
    if (-not $asset) { throw "Could not find mkcert Windows binary in latest GitHub release." }
    $dest = "$env:LOCALAPPDATA\Microsoft\WindowsApps\mkcert.exe"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $dest -UseBasicParsing
    Write-Host "[+] mkcert downloaded to $dest"

    if (-not (Get-Command mkcert -ErrorAction SilentlyContinue)) {
        throw "mkcert not in PATH after install. Add it manually and re-run."
    }
}

function Ensure-Dir([string]$path) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

function Copy-CertPair([string]$tmpDir, [string]$baseName, [string[]]$destinations) {
    $pem = Join-Path $tmpDir "$baseName.pem"
    $key = Join-Path $tmpDir "$baseName-key.pem"
    foreach ($dst in $destinations) {
        Ensure-Dir $dst
        Copy-Item $pem -Destination $dst -Force
        Copy-Item $key -Destination $dst -Force
        Write-Host "    -> $dst"
    }
}

# ── Main ──────────────────────────────────────────────────────────────────────

Ensure-Mkcert

Write-Host "`n[+] Registering mkcert root CA (may require UAC prompt)..."
mkcert -install

$tmpDir = Join-Path $env:TEMP ("buizz_certs_" + [System.IO.Path]::GetRandomFileName())
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null
Push-Location $tmpDir

try {
    # Group 1: victim.com + attacker.com  =>  victim.com+1.*
    Write-Host "`n[+] Generating cert: victim.com attacker.com"
    mkcert victim.com attacker.com
    Copy-CertPair $tmpDir "victim.com+1" @(
        "$ScriptDir\server\coop\nginx\certs",
        "$ScriptDir\server\csp\nginx\certs",
        "$ScriptDir\server\pp\nginx\certs",
        "$ScriptDir\server\xfo\nginx\certs"
    )

    # Group 2: leak.test + adition.com  =>  leak.test+1.*
    Write-Host "`n[+] Generating cert: leak.test adition.com"
    mkcert leak.test adition.com
    Copy-CertPair $tmpDir "leak.test+1" @(
        "$ScriptDir\server\hsts\corpus\certs"
    )

    # Group 3: leak.test + attacker.test + adition.com  =>  leak.test+2.*
    Write-Host "`n[+] Generating cert: leak.test attacker.test adition.com"
    mkcert leak.test attacker.test adition.com
    Copy-CertPair $tmpDir "leak.test+2" @(
        "$ScriptDir\server\samesite\corpus\certs",
        "$ScriptDir\server\rp\corpus\certs"
    )

} finally {
    Pop-Location
    Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}

Write-Host "`n[OK] All certificates installed. You can now start Docker Compose stacks."
