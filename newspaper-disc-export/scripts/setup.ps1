param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectRoot
)

$ErrorActionPreference = 'Stop'
$root = [System.IO.Path]::GetFullPath($ProjectRoot)
$runtime = Join-Path $root 'temp\newspaper-disc-export-runtime'
$venv = Join-Path $runtime '.venv'
$requirements = Join-Path $PSScriptRoot 'requirements.txt'

New-Item -ItemType Directory -Force -Path $runtime | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $venv 'Scripts\python.exe'))) {
    $python = Get-Command python -ErrorAction Stop
    & $python.Source -m venv $venv
}

$venvPython = Join-Path $venv 'Scripts\python.exe'
& $venvPython -m pip install --disable-pip-version-check -r $requirements
if ($LASTEXITCODE -ne 0) {
    throw 'Python dependency installation failed.'
}

Write-Output $venvPython
