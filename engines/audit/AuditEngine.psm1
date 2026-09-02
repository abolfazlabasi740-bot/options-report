Set-StrictMode -Version Latest

function New-RunId {
    return (Get-Date -Format 'yyyyMMdd_HHmmss_fff') + '_' + [guid]::NewGuid().ToString('N').Substring(0,8)
}

function Write-AuditRecord {
    param(
        [Parameter(Mandatory=$true)][object]$Record,
        [Parameter(Mandatory=$true)][string]$AuditDirectory
    )
    New-Item -ItemType Directory -Force -Path $AuditDirectory|Out-Null
    $path=Join-Path $AuditDirectory ($Record.RunId+'.json')
    $Record|ConvertTo-Json -Depth 9|Set-Content -Encoding UTF8 -LiteralPath $path
    return $path
}

function Write-ProcessingLog {
    param([string]$LogPath,[string]$RunId,[string]$Stage,[string]$Status,[string]$Message)
    $entry=[pscustomobject]@{Timestamp=(Get-Date).ToString('o');RunId=$RunId;Stage=$Stage;Status=$Status;Message=$Message}
    ($entry|ConvertTo-Json -Compress)|Add-Content -Encoding UTF8 -LiteralPath $LogPath
}

Export-ModuleMember -Function *
