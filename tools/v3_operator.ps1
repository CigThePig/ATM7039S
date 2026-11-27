# Read-only Windows operator helper. No raw disk access or device writes.
param(
    [Parameter(Mandatory=$true)][ValidateSet('Setup','Prepared','Analyse','Postflight')][string]$Action,
    [string]$CaptureFolder,
    [string]$Results = (Join-Path $HOME 'Downloads\ATM7039S-V3-results')
)
$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
$root = Split-Path -Parent $PSScriptRoot
function Get-TestVolume([string]$Label) {
    $vol = @(Get-Volume -FileSystemLabel $Label | Where-Object DriveLetter)
    if ($vol.Count -ne 1) { throw "Expected one mounted $Label partition. Check Disk Management; never format." }
    $part = Get-Partition -DriveLetter $vol[0].DriveLetter
    $disk = Get-Disk -Number $part.DiskNumber
    if ($disk.IsBoot -or $disk.IsSystem -or $disk.BusType -notin @('USB','SD','MMC')) { throw "Not a confirmed removable test disk: $Label" }
    return @{ Path = "$($vol[0].DriveLetter):\"; Disk = $part.DiskNumber }
}
function Invoke-Python([string[]]$Arguments) {
    & python @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Python exited with code $LASTEXITCODE. Preserve the card and report the output." }
}
Push-Location $root
try {
    if ($Action -eq 'Setup') {
        Invoke-Python -Arguments @('-m','pip','install','--user','-r','requirements-dev.txt','-r','requirements-firmware.txt')
        return
    }
    $boot = Get-TestVolume 'BATOCERA'
    $share = Get-TestVolume 'SHARE'
    if ($boot.Disk -ne $share.Disk) { throw 'BATOCERA and SHARE are not on the same disk.' }
    if (-not (Test-Path (Join-Path $boot.Path 'KERNEL.DTB') -PathType Leaf)) { throw 'Missing KERNEL.DTB.' }
    $Results = [IO.Path]::GetFullPath($Results)
    $resultPartition = Get-Partition -DriveLetter $Results.Substring(0,1)
    if ($resultPartition.DiskNumber -eq $boot.Disk) { throw 'Results must be on the computer, not the card.' }
    New-Item -ItemType Directory -Force -Path $Results | Out-Null
    if ($Action -eq 'Analyse') {
        if (-not $CaptureFolder -or -not (Test-Path $CaptureFolder -PathType Container)) { throw 'Provide the local copied capture folder with -CaptureFolder.' }
        $CaptureFolder = [IO.Path]::GetFullPath($CaptureFolder)
        if ((Get-Partition -DriveLetter $CaptureFolder.Substring(0,1)).DiskNumber -eq $boot.Disk) { throw 'Copy the raw capture to a private local folder first.' }
        Invoke-Python -Arguments @('tools/runtime_capture.py',$CaptureFolder,(Join-Path $Results 'summary.json'),'--report',(Join-Path $Results 'summary.md'),'--reference-dtb',(Join-Path $boot.Path 'KERNEL.DTB'))
    } else {
        $prefix = if ($Action -eq 'Prepared') {'preflight-prepared'} else {'preflight-after'}
        & python tools/v3_preflight.py --boot-dir ($boot.Path + '.') --share-dir ($share.Path + '.') --json (Join-Path $Results "$prefix.json") | Tee-Object -FilePath (Join-Path $Results "$prefix.txt")
        if ($LASTEXITCODE -ne 0) { throw "Preflight failed; preserved results in $Results. Do not boot or reflash automatically." }
    }
    Write-Host "Results saved in $Results. Review for identifiers before sharing."
} finally { Pop-Location }
