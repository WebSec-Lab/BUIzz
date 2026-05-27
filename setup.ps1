<#
.SYNOPSIS
    BUIZZ environment setup script.
    - Installs required Python packages
    - Updates C:\Windows\System32\drivers\etc\hosts with fuzzer domains

.PARAMETER IP
    Optional. The IP address to use for hosts file entries.
    If omitted, the primary local IP is detected automatically.

.EXAMPLE
    .\setup.ps1
    .\setup.ps1 10.20.23.182
#>

param(
    [string]$IP = ""
)

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

# ── Python packages ───────────────────────────────────────────────────────────

Write-Host "`n[1/2] Installing Python packages..." -ForegroundColor Cyan

$packages = @(
    "playwright",
    "psutil",
    "pywinauto",
    "pyautogui",
    "webdriver-manager"
)

foreach ($pkg in $packages) {
    Write-Host "  pip install $pkg"
    pip install $pkg
}

Write-Host "`n  Installing Playwright browsers..."
python -m playwright install

# ── hosts file ────────────────────────────────────────────────────────────────

Write-Host "`n[2/2] Updating hosts file..." -ForegroundColor Cyan

if ($IP) {
    $localIP = $IP
    Write-Host "  Using IP (from argument): $localIP"
} else {
    # Detect the primary local IP (first non-loopback IPv4)
    $localIP = (
        Get-NetIPAddress -AddressFamily IPv4 |
        Where-Object { $_.IPAddress -notmatch "^127\." -and $_.PrefixOrigin -ne "WellKnown" } |
        Sort-Object InterfaceMetric |
        Select-Object -First 1
    ).IPAddress

    if (-not $localIP) {
        Write-Warning "Could not detect local IP automatically. Falling back to 127.0.0.1"
        $localIP = "127.0.0.1"
    }

    Write-Host "  Using IP (auto-detected): $localIP"
}

$hostsPath = "C:\Windows\System32\drivers\etc\hosts"

$domains = @(
    "leak.test",
    "adition.com",
    "attacker.test",
    "attacker.com",
    "victim.com"
)

$marker = "# BUIZZ fuzzer domains"

# Read existing hosts content
$content = Get-Content $hostsPath -Raw

# Remove previous BUIZZ block if it exists
if ($content -match "(?ms)$marker.*?# END BUIZZ") {
    $content = $content -replace "(?ms)\r?\n$marker.*?# END BUIZZ", ""
}

# Build new block
$block = "`r`n$marker`r`n"
foreach ($domain in $domains) {
    $block += "$localIP`t$domain`r`n"
}
$block += "# END BUIZZ"

# Append and write back
$content = $content.TrimEnd() + $block
Set-Content -Path $hostsPath -Value $content -Encoding ASCII -NoNewline

Write-Host "`n  Added to hosts file:"
foreach ($domain in $domains) {
    Write-Host "    $localIP`t$domain"
}

Write-Host "`n[Done] Setup complete." -ForegroundColor Green
