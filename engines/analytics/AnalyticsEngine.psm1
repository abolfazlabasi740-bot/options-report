Set-StrictMode -Version Latest

function Add-ContractAnalytics {
    param([Parameter(Mandatory=$true)][object[]]$Contracts)
    $featureNames = @(
        'OI','SpreadRatio','Depth','IV','HV','IVHV','TimeCost','BSDiff','StrikeDiff',
        'TradingDays','CalendarDays','ThetaRatio','Delta','Gamma','Vega','Rho',
        'LastVsClosePct','IntradayRangePct','Status'
    )
    foreach ($contract in $Contracts) {
        $missing = @()
        foreach ($name in $featureNames) {
            if ($null -eq $contract.$name) { $missing += $name }
        }
        $available = $featureNames.Count - $missing.Count
        $confidence = if ($featureNames.Count -gt 0) { $available / [double]$featureNames.Count } else { 0.0 }
        $flags = [Collections.Generic.List[string]]::new()
        if ($null -eq $contract.IV) { $flags.Add('MISSING_IV') }
        if ($null -eq $contract.IVHV) { $flags.Add('MISSING_IV_HV') }
        if ($null -eq $contract.Status) { $flags.Add('MISSING_STATUS') }
        else { $flags.Add('STATUS_MAPPING_NOT_APPROVED') }
        if ($contract.RemainingDays -le 7) { $flags.Add('NEAR_EXPIRY') }
        if ($contract.SpreadRatio -ne $null -and $contract.SpreadRatio -gt 0.1) { $flags.Add('WIDE_SPREAD') }
        if ($contract.BEDistance -gt 0.1) { $flags.Add('DISTANT_BREAKEVEN') }
        $contract | Add-Member -NotePropertyName MissingData -NotePropertyValue $missing -Force
        $contract | Add-Member -NotePropertyName DataConfidence -NotePropertyValue $confidence -Force
        $contract | Add-Member -NotePropertyName Flags -NotePropertyValue @($flags) -Force
    }
    return $Contracts
}

function Get-FeatureCatalog {
    param([string]$RegistryPath)
    if ([string]::IsNullOrWhiteSpace($RegistryPath) -or -not (Test-Path -LiteralPath $RegistryPath)) {
        throw 'Feature Registry is required and was not found.'
    }
    return @((Get-Content -Raw -Encoding UTF8 -LiteralPath $RegistryPath | ConvertFrom-Json).features)
}

Export-ModuleMember -Function *
