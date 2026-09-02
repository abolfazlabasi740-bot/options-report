Set-StrictMode -Version Latest

function Read-ProjectConfig {
    param([Parameter(Mandatory=$true)][string]$Path)
    return Get-Content -Raw -Encoding UTF8 -LiteralPath $Path | ConvertFrom-Json
}

function Assert-ProjectConfig {
    param(
        [Parameter(Mandatory=$true)][object]$Config,
        [Parameter(Mandatory=$true)][string]$ProjectRoot
    )
    if ($Config.protocol -ne 'PROTOCOL_OPTIONS_RANKING_V3') {
        throw "Production protocol must remain PROTOCOL_OPTIONS_RANKING_V3; received $($Config.protocol)."
    }
    if ([bool]$Config.master_project_book.v4_production_approved) {
        throw 'V4 cannot be marked Production without an approved executable specification.'
    }
    $blockTotal = 0.0
    foreach ($property in $Config.block_weights.PSObject.Properties) {
        $blockTotal += [double]$property.Value
    }
    if ([Math]::Abs($blockTotal - 100.0) -gt 0.000001) {
        throw "Block weights must sum to 100; received $blockTotal."
    }
    foreach ($block in @('liquidity','valuation','payoff','time','greeks','market')) {
        $factorTotal = 0.0
        foreach ($property in $Config.factor_weights.$block.PSObject.Properties) {
            $factorTotal += [double]$property.Value
        }
        $expected = [double]$Config.block_weights.$block
        if ([Math]::Abs($factorTotal - $expected) -gt 0.000001) {
            throw "Factor weights for $block must sum to $expected; received $factorTotal."
        }
    }
    if ($null -eq $Config.liquidity_controls -or $null -eq $Config.liquidity_controls.low_volume_penalty) {
        throw 'Liquidity low-volume penalty configuration is missing.'
    }
    $maxVolumePenalty = [double]$Config.liquidity_controls.low_volume_penalty.max_points
    if ($maxVolumePenalty -lt 0.0 -or $maxVolumePenalty -gt [double]$Config.block_weights.liquidity) {
        throw "Low-volume penalty must be between zero and the liquidity block weight; received $maxVolumePenalty."
    }
    if ([string]$Config.liquidity_controls.low_volume_penalty.curve -ne 'SQRT_COMPLEMENT') {
        throw 'Unsupported low-volume penalty curve.'
    }
    $masterPath = [IO.Path]::GetFullPath((Join-Path $ProjectRoot ([string]$Config.master_project_book.relative_path)))
    if (-not (Test-Path -LiteralPath $masterPath -PathType Leaf)) {
        throw "Master Project Book was not found: $masterPath"
    }
    $actualMasterHash = Get-FileSha256 $masterPath
    if ($actualMasterHash -ne ([string]$Config.master_project_book.sha256).ToLowerInvariant()) {
        throw "Master Project Book hash mismatch. Expected $($Config.master_project_book.sha256), received $actualMasterHash."
    }
    $versionRecordPath = [IO.Path]::GetFullPath((Join-Path $ProjectRoot ([string]$Config.version_record)))
    if (-not (Test-Path -LiteralPath $versionRecordPath -PathType Leaf)) {
        throw "Version Record was not found: $versionRecordPath"
    }
    $versionRecord = Get-Content -Raw -Encoding UTF8 -LiteralPath $versionRecordPath | ConvertFrom-Json
    if ([string]$versionRecord.version -ne [string]$Config.version) {
        throw "Version Record mismatch. Config=$($Config.version), Record=$($versionRecord.version)."
    }
    return [pscustomobject]@{
        Status='PASS'
        MasterProjectBook=$masterPath
        MasterSha256=$actualMasterHash
        BlockWeightTotal=$blockTotal
        Baseline=$Config.master_project_book.baseline
        Candidate=$Config.master_project_book.candidate
        VersionRecord=$versionRecordPath
        VersionRecordSha256=Get-FileSha256 $versionRecordPath
        KnownGaps=@($Config.known_gaps)
    }
}

function Convert-OptionNumber {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    if ($Value -is [ValueType]) { return [double]$Value }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -in @('-', '--', 'N/A', 'null')) { return $null }
    $fa = '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩'
    $en = '01234567890123456789'
    for ($i=0; $i -lt $fa.Length; $i++) { $text = $text.Replace($fa[$i], $en[$i]) }
    $text = $text.Replace(',', '').Replace([string][char]0x066C, '').Replace('%', '').Replace(' ', '')
    $multiplier = 1.0
    if ($text -match '^(.*?)([KMB])$') {
        $text = $Matches[1]
        $multiplier = switch ($Matches[2]) { 'K' {1e3} 'M' {1e6} 'B' {1e9} }
    }
    $number = 0.0
    if (-not [double]::TryParse($text, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$number)) {
        return $null
    }
    return $number * $multiplier
}

function Convert-OpenInterest {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    $match = [regex]::Match(([string]$Value).Trim(), '^-?[0-9,]+(?:\.[0-9]+)?')
    if (-not $match.Success) { return $null }
    return Convert-OptionNumber $match.Value
}

function Get-PercentileRank {
    param([object[]]$Values, [double]$Value)
    $n = $Values.Count
    if ($n -le 1) { return 0.5 }
    $less = 0
    $equal = 0
    foreach ($item in $Values) {
        $number = [double]$item
        if ($number -lt $Value) { $less++ }
        elseif ($number -eq $Value) { $equal++ }
    }
    return [Math]::Max(0.0, [Math]::Min(1.0, ($less + (($equal - 1.0) / 2.0)) / ($n - 1.0)))
}

function Get-CenteredScore {
    param([double]$Percentile)
    return [Math]::Max(0.0, 1.0 - [Math]::Abs((2.0 * $Percentile) - 1.0))
}

function Get-WeightedBlock {
    param([object[]]$Factors, [double]$BlockWeight)
    $weighted = 0.0
    $available = 0.0
    foreach ($factor in $Factors) {
        if ($null -ne $factor.Score) {
            $weighted += [double]$factor.Score * [double]$factor.Weight
            $available += [double]$factor.Weight
        }
    }
    if ($available -le 0.0) { return $null }
    return $BlockWeight * ($weighted / $available)
}

function Get-PairwiseRisk {
    param([double[]]$Risks)
    $sum = 0.0
    $count = 0
    for ($i=0; $i -lt $Risks.Count; $i++) {
        for ($j=$i+1; $j -lt $Risks.Count; $j++) {
            $sum += $Risks[$i] * $Risks[$j]
            $count++
        }
    }
    if ($count -eq 0) { return 0.0 }
    return $sum / $count
}

function Get-Median {
    param([object[]]$Values)
    $sorted = @($Values | Where-Object { $null -ne $_ } | Sort-Object)
    if ($sorted.Count -eq 0) { return $null }
    $middle = [int][Math]::Floor($sorted.Count / 2)
    if ($sorted.Count % 2 -eq 1) { return [double]$sorted[$middle] }
    return ([double]$sorted[$middle-1] + [double]$sorted[$middle]) / 2.0
}

function Get-FileSha256 {
    param([Parameter(Mandatory=$true)][string]$Path)
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Get-StringSha256 {
    param([Parameter(Mandatory=$true)][string]$Value)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes($Value)
        return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Get-CodeManifest {
    param([Parameter(Mandatory=$true)][string]$ProjectRoot)
    $files = Get-ChildItem -LiteralPath $ProjectRoot -Recurse -File |
        Where-Object {
            $_.Extension -in @('.ps1','.psm1','.py') -and
            $_.FullName -notmatch '\\__pycache__\\'
        } |
        Sort-Object FullName
    return @($files | ForEach-Object {
        [pscustomobject]@{
            Path=$_.FullName.Substring($ProjectRoot.Length).TrimStart('\','/')
            Sha256=Get-FileSha256 $_.FullName
            Bytes=$_.Length
        }
    })
}

Export-ModuleMember -Function *
