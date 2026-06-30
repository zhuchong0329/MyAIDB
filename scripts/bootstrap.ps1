$ErrorActionPreference = "Stop"

function Command-Exists {
    param([string]$Name)
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "==> MyAIDB environment bootstrap (Windows)"

$CargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
if (Test-Path $CargoBin) {
    $env:PATH = "$CargoBin;$env:PATH"
}

if (Command-Exists "winget") {
    winget list --id Microsoft.VisualStudio.2022.BuildTools -e | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "==> Visual Studio Build Tools not found; installing C++ workload with Windows SDK"
        winget install --id Microsoft.VisualStudio.2022.BuildTools -e --accept-package-agreements --accept-source-agreements --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"
        Write-Host "==> Visual Studio Build Tools installation finished. A reboot may be required."
    }
} else {
    Write-Host "winget is unavailable; skipping Visual Studio Build Tools check."
    Write-Host "If cargo fails with link.exe not found, install Visual Studio Build Tools with the C++ workload."
}

if (-not (Command-Exists "rustup")) {
    if (Command-Exists "winget") {
        Write-Host "==> rustup not found; installing Rustup with winget"
        winget install --id Rustlang.Rustup -e --accept-package-agreements --accept-source-agreements
        if (Test-Path $CargoBin) {
            $env:PATH = "$CargoBin;$env:PATH"
        }
    } else {
        Write-Host "rustup was not found and winget is unavailable."
        Write-Host "Install Rustup from https://rustup.rs/, restart the terminal, then rerun this script."
        exit 1
    }
}

if (-not (Command-Exists "rustup")) {
    Write-Host "rustup is still not available in PATH."
    Write-Host "Restart the terminal after installation, then rerun this script."
    exit 1
}

Write-Host "==> Installing or updating the pinned Rust toolchain"
rustup toolchain install stable --component rustfmt --component clippy
rustup component add rustfmt clippy --toolchain stable

Write-Host "==> Active versions"
rustc --version
cargo --version
rustup --version

Write-Host "==> Bootstrap complete"
