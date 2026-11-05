param(
    [string]$Python = "",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

if ([string]::IsNullOrWhiteSpace($Python)) {
    $localVenv = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
    $parentVenv = Join-Path (Split-Path -Parent $ProjectRoot) ".venv\Scripts\python.exe"
    if (Test-Path $localVenv) {
        $Python = $localVenv
    } elseif (Test-Path $parentVenv) {
        $Python = $parentVenv
    } else {
        $Python = "python"
    }
}

if ([System.IO.Path]::IsPathRooted($Python) -and -not (Test-Path $Python)) {
    throw "Python not found: $Python"
}

Write-Host "Using Python: $Python"
& $Python -c "import PySide6, PyInstaller; print('PySide6', PySide6.__version__, '| PyInstaller', PyInstaller.__version__)"
if ($LASTEXITCODE -ne 0) {
    throw "Build dependencies are missing. Run: $Python -m pip install -r requirements-dev.txt"
}

if (-not $SkipTests) {
    Write-Host "Running tests..."
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "Tests failed; packaging aborted."
    }
}

$DistRoot = Join-Path $ProjectRoot "dist"
$BuildRoot = Join-Path $ProjectRoot "build"
$AppDir = Join-Path $DistRoot "Qingdan"
$UserDataDir = Join-Path $AppDir "data"
$UserDataBackup = Join-Path $ProjectRoot ".user-data-backup"
$ZipPath = Join-Path $DistRoot "Qingdan-Windows-v1.2.0.zip"

# Build artifacts live next to the portable app data, so preserve the user's
# data folder before recreating dist. The zip is created without personal data;
# the data is restored into the unpacked developer copy afterwards.
if (Test-Path $UserDataBackup) {
    Remove-Item $UserDataBackup -Recurse -Force
}
if (Test-Path $UserDataDir) {
    Copy-Item $UserDataDir $UserDataBackup -Recurse -Force
}

if (Test-Path $DistRoot) {
    Remove-Item $DistRoot -Recurse -Force
}

Write-Host "Building Qingdan.exe..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name Qingdan `
    --icon "assets\app.ico" `
    --version-file "version_info.txt" `
    --distpath $DistRoot `
    --workpath $BuildRoot `
    "main.py"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

if (-not (Test-Path (Join-Path $AppDir "Qingdan.exe"))) {
    throw "Build completed but Qingdan.exe was not produced."
}

Copy-Item "README.md" (Join-Path $AppDir "README.md") -Force
$AppDocs = Join-Path $AppDir "docs"
New-Item -ItemType Directory -Path $AppDocs -Force | Out-Null
Copy-Item "docs\*.png" $AppDocs -Force

Write-Host "Creating release zip..."
Compress-Archive -Path $AppDir -DestinationPath $ZipPath -CompressionLevel Optimal -Force

if (Test-Path $UserDataBackup) {
    New-Item -ItemType Directory -Path $UserDataDir -Force | Out-Null
    Copy-Item (Join-Path $UserDataBackup "*") $UserDataDir -Recurse -Force
    Remove-Item $UserDataBackup -Recurse -Force
}

$exeSize = (Get-Item (Join-Path $AppDir "Qingdan.exe")).Length
$zipSize = (Get-Item $ZipPath).Length
Write-Host ""
Write-Host "Build complete."
Write-Host ("  Exe : {0}  ({1:N1} MB)" -f (Join-Path $AppDir "Qingdan.exe"), ($exeSize / 1MB))
Write-Host ("  Zip : {0}  ({1:N1} MB)" -f $ZipPath, ($zipSize / 1MB))
