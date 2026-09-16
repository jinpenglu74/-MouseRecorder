param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
$env:PYTHONPATH = Join-Path $project "src"
$version = (& python -c "from fund_platform import __version__; print(__version__)").Trim()
$setupNameBase64 = (& python -c "import base64; from fund_platform import artifact_name; print(base64.b64encode(artifact_name('setup').encode('utf-8')).decode('ascii'))").Trim()
$setupName = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($setupNameBase64))
$dist = Join-Path $project "dist\FundForecastApp"
$iss = Join-Path $PSScriptRoot "FundForecastApp.iss"

if (-not $version -or -not $setupName) {
    throw "Unable to read the application version."
}
if (-not (Test-Path (Join-Path $dist "FundForecastApp.exe"))) {
    throw "Run the PyInstaller build before creating the installer."
}
if (-not (Test-Path $iss)) {
    throw "Inno Setup definition is missing: $iss"
}

$innoCandidates = @()
if (${env:ProgramFiles(x86)}) {
    $innoCandidates += Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"
}
if ($env:ProgramFiles) {
    $innoCandidates += Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"
}
if ($env:ChocolateyToolsLocation) {
    $innoCandidates += Join-Path $env:ChocolateyToolsLocation "InnoSetup\ISCC.exe"
}
$innoCandidates = $innoCandidates | Where-Object { Test-Path $_ }
$iscc = $innoCandidates | Select-Object -First 1
if (-not $iscc) {
    $command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($command) { $iscc = $command.Source }
}
if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup 6 before building."
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$sourceDir = (Resolve-Path $dist).Path
$outputDir = (Resolve-Path $OutputDirectory).Path
& $iscc "/DMyAppVersion=$version" "/DSourceDir=$sourceDir" "/DOutputDir=$outputDir" $iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compiler failed with exit code $LASTEXITCODE."
}

$generated = Join-Path $OutputDirectory "基金预测-安装程序-v$version.exe"
$expected = Join-Path $OutputDirectory $setupName
if (-not (Test-Path $generated)) {
    throw "Inno Setup did not create the expected installer: $generated"
}
if ($generated -ne $expected) {
    Copy-Item -LiteralPath $generated -Destination $expected -Force
    Remove-Item -LiteralPath $generated -Force
}
Write-Output $expected
