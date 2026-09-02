param([string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot))
$ErrorActionPreference='Stop'
$pipeline=Join-Path $PSScriptRoot 'run_pipeline.ps1'
$result=& $pipeline -Download -ProjectRoot $ProjectRoot -Quiet
if($result.Status-eq'NO_NEW_FILE'){
    $result.Message
    exit 0
}
if($result.Status-ne'COMPLETED'){throw 'Scheduled pipeline did not complete.'}
Get-Content -Raw -Encoding UTF8 -LiteralPath $result.Report
