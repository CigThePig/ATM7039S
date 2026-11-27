# Exercise real fallback script with simulated storage APIs and a private venv.
# No actual card, volume, firmware or administrator operations.
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$work = Join-Path $env:RUNNER_TEMP ("fallback lab ü " + [guid]::NewGuid())
$letters = @('Q','R','S','T','U','V','W','X','Y','Z' | Where-Object { -not (Get-PSDrive -Name $_ -ErrorAction SilentlyContinue) })
if ($letters.Count -lt 2) { throw 'Need two unused simulated drive letters' }
$bootLetter = $letters[0]
$shareLetter = $letters[1]
$scriptPath = Join-Path $work 'tools\v3_operator.ps1'
try {
    New-Item -ItemType Directory -Force (Join-Path $work 'tools'), (Join-Path $work 'boot'), (Join-Path $work 'share'), (Join-Path $work 'capture') | Out-Null
    Copy-Item (Join-Path $project 'tools\v3_operator.ps1') $scriptPath
    New-Item -ItemType File (Join-Path $work 'boot\KERNEL.DTB') | Out-Null
    New-PSDrive -Name $bootLetter -PSProvider FileSystem -Root (Join-Path $work 'boot') | Out-Null
    New-PSDrive -Name $shareLetter -PSProvider FileSystem -Root (Join-Path $work 'share') | Out-Null
    function Get-Volume { param($FileSystemLabel) [pscustomobject]@{DriveLetter = $(if ($FileSystemLabel -eq 'BATOCERA') {$bootLetter} else {$shareLetter})} }
    function Get-Partition { param($DriveLetter) [pscustomobject]@{DiskNumber = $(if ($DriveLetter -in @($bootLetter,$shareLetter)) {7} else {0})} }
    function Get-Disk { param($Number) [pscustomobject]@{IsBoot=$false;IsSystem=$false;BusType='USB'} }
    # The fallback must fail early before accessing volumes if Setup was not run.
    $failed = $false
    try { & $scriptPath -Action Prepared -Results (Join-Path $work 'results') }
    catch { if ($_ -notmatch 'Action Setup first') { throw }; $failed = $true }
    if (-not $failed) { throw 'Missing virtual environment was not rejected' }

    python -m venv --without-pip (Join-Path $work '.venv-lab')
    if ($LASTEXITCODE -ne 0) { throw 'Could not create fixture environment' }
    $expected = Join-Path $work '.venv-lab\Scripts\python.exe'
    $probe = @'
import json, sys
from pathlib import Path
with Path("trace.jsonl").open("a", encoding="utf-8") as f:
    f.write(json.dumps({"python": sys.executable, "args": sys.argv}) + "\n")
'@
    foreach ($name in @('v3_preflight.py','v3_rootfs_review.py','runtime_capture.py')) {
        Set-Content -LiteralPath (Join-Path $work "tools\$name") -Value $probe -Encoding utf8
    }
    foreach ($action in @('Prepared','Postflight','RootfsReview','Analyse')) {
        & $scriptPath -Action $action -Results (Join-Path $work 'results') -CaptureFolder (Join-Path $work 'capture')
    }
    $records = @(Get-Content (Join-Path $work 'trace.jsonl') | ForEach-Object { ConvertFrom-Json $_ })
    if ($records.Count -ne 4) { throw "Expected four Python calls; got $($records.Count)" }
    foreach ($record in $records) {
        if ($record.python -ne $expected) { throw "Wrong interpreter: $($record.python)" }
    }
    if ($records[0].args -notcontains 'prepared' -or $records[1].args -notcontains 'post-capture') { throw 'Phase arguments lost' }
    Write-Host 'Fallback interpreter smoke test passed'
} finally {
    Remove-PSDrive -Name $bootLetter,$shareLetter -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}
