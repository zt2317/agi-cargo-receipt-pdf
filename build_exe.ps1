# PowerShell script to build a Windows .exe using PyInstaller
# Usage (on Windows PowerShell):
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   ./build_exe.ps1 -ProjectDir . -Entry main.py -OutName cargo_parser

param(
    [string]$ProjectDir = ".",
    [string]$Entry = "main.py",
    [string]$OutName = "cargo_parser",
    [string]$Python = "python"
)

$ErrorActionPreference = 'Stop'

Push-Location $ProjectDir
try {
    Write-Host "Using project dir: $ProjectDir"
    Write-Host "Entry script: $Entry"

    # Create venv
    if (-not (Test-Path ".venv")) {
        & $Python -m venv .venv
    }
    # Activate venv
    $activate = Join-Path -Path (Get-Location) -ChildPath ".venv/Scripts/Activate.ps1"
    if (Test-Path $activate) {
        . $activate
    }

    # Upgrade pip and install requirements
    & $Python -m pip install --upgrade pip
    if (Test-Path "requirements.txt") {
        & $Python -m pip install -r requirements.txt
    }
    & $Python -m pip install pyinstaller

    # Run PyInstaller to build one-file exe
    # --noconfirm overwrite dist folder
    # --onefile single exe
    # --name $OutName set exe name
    $cmd = "pyinstaller --noconfirm --onefile --name $OutName $Entry"
    Write-Host "Running: $cmd"
    Invoke-Expression $cmd

    Write-Host "Build finished. Look in the 'dist' folder for $OutName.exe"
} finally {
    Pop-Location
}

