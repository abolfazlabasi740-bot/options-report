Set-StrictMode -Version Latest

function Get-FHProperty {
    param(
        [AllowNull()][object]$Object,
        [Parameter(Mandatory=$true)][string]$Name
    )
    if ($null -eq $Object) { return $null }
    if ($Object -is [Collections.IDictionary]) {
        if ($Object.Contains($Name)) { return $Object[$Name] }
        return $null
    }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Convert-FHNumber {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    if ($Value -is [byte] -or $Value -is [int16] -or $Value -is [int32] -or
        $Value -is [int64] -or $Value -is [single] -or $Value -is [double] -or
        $Value -is [decimal]) {
        $number = [double]$Value
        if ([double]::IsNaN($number) -or [double]::IsInfinity($number)) { return $null }
        return $number
    }
    $text = ([string]$Value).Trim()
    if ([string]::IsNullOrWhiteSpace($text) -or $text -in @('-', '--', 'N/A', 'NA', 'null', 'NULL')) {
        return $null
    }
    $persian = '۰۱۲۳۴۵۶۷۸۹'
    $arabic = '٠١٢٣٤٥٦٧٨٩'
    $latin = '0123456789'
    for ($i = 0; $i -lt $latin.Length; $i++) {
        $text = $text.Replace($persian[$i], $latin[$i]).Replace($arabic[$i], $latin[$i])
    }
    $text = $text.Replace(',', '').Replace([string][char]0x066C, '').Replace('٪', '').Replace('%', '').Replace(' ', '')
    $negative = $false
    if ($text.StartsWith('(') -and $text.EndsWith(')')) {
        $negative = $true
        $text = $text.Substring(1, $text.Length - 2)
    }
    $number = 0.0
    $parsed = [double]::TryParse(
        $text,
        [Globalization.NumberStyles]::Float,
        [Globalization.CultureInfo]::InvariantCulture,
        [ref]$number
    )
    if (-not $parsed -or [double]::IsNaN($number) -or [double]::IsInfinity($number)) { return $null }
    if ($negative) { $number = -$number }
    return $number
}

function Convert-FHDateTimeOffset {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    $parsed = [DateTimeOffset]::MinValue
    if ([DateTimeOffset]::TryParse(([string]$Value), [ref]$parsed)) { return $parsed }
    return $null
}

function Get-FHConfigObject {
    param([Parameter(Mandatory=$true)][object]$Config)
    if ($Config -is [string]) {
        if (-not (Test-Path -LiteralPath $Config -PathType Leaf)) {
            throw "Fundamental health config was not found: $Config"
        }
        return Get-Content -Raw -Encoding UTF8 -LiteralPath $Config | ConvertFrom-Json
    }
    return $Config
}

function Get-FHProfileName {
    param(
        [Parameter(Mandatory=$true)][object]$Record,
        [Parameter(Mandatory=$true)][object]$Config
    )
    $requested = [string](Get-FHProperty $Record 'Profile')
    if ([string]::IsNullOrWhiteSpace($requested)) { $requested = 'non_financial' }
    $profiles = Get-FHProperty $Config 'profiles'
    if ($null -eq (Get-FHProperty $profiles $requested)) {
        throw "Unsupported fundamental profile '$requested'."
    }
    return $requested
}

function Get-FHMetricDefinitions {
    param(
        [Parameter(Mandatory=$true)][string]$ProfileName,
        [Parameter(Mandatory=$true)][object]$Config
    )
    $profile = Get-FHProperty (Get-FHProperty $Config 'profiles') $ProfileName
    return @((Get-FHProperty $profile 'metrics'))
}

function Get-FHMetricEvidence {
    param(
        [Parameter(Mandatory=$true)][object]$Record,
        [Parameter(Mandatory=$true)][object]$Definition,
        [AllowNull()][DateTimeOffset]$DecisionTime,
        [Parameter(Mandatory=$true)][object]$Config
    )
    $metricId = [string](Get-FHProperty $Definition 'id')
    $metrics = Get-FHProperty $Record 'Metrics'
    $node = Get-FHProperty $metrics $metricId
    $nodeHasValue = $false
    if ($null -ne $node -and $null -ne (Get-FHProperty $node 'Value')) { $nodeHasValue = $true }

    $rawValue = if ($nodeHasValue) { Get-FHProperty $node 'Value' } else { $node }
    $value = Convert-FHNumber $rawValue
    $source = if ($nodeHasValue) { Get-FHProperty $node 'Source' } else { $null }
    if ([string]::IsNullOrWhiteSpace([string]$source)) { $source = Get-FHProperty $Record 'Source' }
    $releaseText = if ($nodeHasValue) { Get-FHProperty $node 'ReleaseTimestamp' } else { $null }
    if ($null -eq $releaseText) { $releaseText = Get-FHProperty $Record 'ReleaseTimestamp' }
    $periodEnd = if ($nodeHasValue) { Get-FHProperty $node 'PeriodEnd' } else { $null }
    if ($null -eq $periodEnd) { $periodEnd = Get-FHProperty $Record 'PeriodEnd' }
    $unit = if ($nodeHasValue) { Get-FHProperty $node 'Unit' } else { $null }
    if ([string]::IsNullOrWhiteSpace([string]$unit)) { $unit = Get-FHProperty $Definition 'unit' }
    $evidenceId = if ($nodeHasValue) { Get-FHProperty $node 'EvidenceId' } else { $null }

    $flags = [Collections.Generic.List[string]]::new()
    $available = $true
    if ($null -eq $value) {
        $available = $false
        $flags.Add('MISSING_VALUE')
    }
    $gates = Get-FHProperty $Config 'gates'
    if ([bool](Get-FHProperty $gates 'require_source') -and
        [string]::IsNullOrWhiteSpace([string]$source)) {
        $available = $false
        $flags.Add('MISSING_SOURCE')
    }
    $release = Convert-FHDateTimeOffset $releaseText
    if ([bool](Get-FHProperty $gates 'require_release_timestamp') -and $null -eq $release) {
        $available = $false
        $flags.Add('MISSING_RELEASE_TIMESTAMP')
    }
    if ([bool](Get-FHProperty $gates 'require_unit') -and
        [string]::IsNullOrWhiteSpace([string]$unit)) {
        $available = $false
        $flags.Add('MISSING_UNIT')
    }
    if ($null -eq $DecisionTime -and [bool](Get-FHProperty $gates 'require_decision_time')) {
        $available = $false
        $flags.Add('MISSING_DECISION_TIME')
    }

    $ageDays = $null
    $freshness = 0.0
    if ($null -ne $release -and $null -ne $DecisionTime) {
        if ($release -gt $DecisionTime) {
            $available = $false
            $flags.Add('LOOKAHEAD_RELEASE')
        } else {
            $ageDays = ($DecisionTime - $release).TotalDays
            $maxAge = Convert-FHNumber (Get-FHProperty $Definition 'max_age_days')
            if ($null -eq $maxAge) {
                $maxAge = Convert-FHNumber (Get-FHProperty $gates 'max_statement_age_days')
            }
            if ($null -ne $maxAge -and $maxAge -gt 0.0) {
                $freshness = [Math]::Max(0.0, [Math]::Min(1.0, 1.0 - ($ageDays / $maxAge)))
                if ($ageDays -gt $maxAge) {
                    $available = $false
                    $flags.Add('STALE_EVIDENCE')
                }
            } else {
                $freshness = 1.0
            }
        }
    }

    $clipped = $false
    if ($null -ne $value) {
        $floor = Convert-FHNumber (Get-FHProperty $Definition 'floor')
        $cap = Convert-FHNumber (Get-FHProperty $Definition 'cap')
        if ($null -ne $floor -and $value -lt $floor) {
            $value = $floor
            $clipped = $true
            $flags.Add('CLIPPED_TO_FLOOR')
        }
        if ($null -ne $cap -and $value -gt $cap) {
            $value = $cap
            $clipped = $true
            $flags.Add('CLIPPED_TO_CAP')
        }
    }
    $reason = if ($flags.Count -eq 0) { 'OK' } else { $flags -join ';' }
    return [pscustomobject]@{
        MetricId=$metricId
        Block=[string](Get-FHProperty $Definition 'block')
        Weight=Convert-FHNumber (Get-FHProperty $Definition 'weight')
        Critical=[bool](Get-FHProperty $Definition 'critical')
        Direction=Convert-FHNumber (Get-FHProperty $Definition 'direction')
        Mode=[string](Get-FHProperty $Definition 'mode')
        Value=$value
        RawValue=$rawValue
        Unit=[string]$unit
        Source=[string]$source
        EvidenceId=[string]$evidenceId
        PeriodEnd=[string]$periodEnd
        ReleaseTimestamp=if ($null -ne $release) { $release.ToString('o') } else { $null }
        AgeDays=$ageDays
        Freshness=$freshness
        Available=$available
        Clipped=$clipped
        Reason=$reason
    }
}

function Get-FHPercentile {
    param(
        [Parameter(Mandatory=$true)][double[]]$Values,
        [Parameter(Mandatory=$true)][double]$Value
    )
    $valid = @($Values | Where-Object {
        $number = [double]$_
        -not [double]::IsNaN($number) -and -not [double]::IsInfinity($number)
    })
    if ($valid.Count -le 1) { return 0.5 }
    $less = 0
    $equal = 0
    foreach ($item in $valid) {
        if ([double]$item -lt $Value) { $less++ }
        elseif ([double]$item -eq $Value) { $equal++ }
    }
    $percentile = ($less + (0.5 * $equal)) / [double]$valid.Count
    return [Math]::Max(0.0, [Math]::Min(1.0, $percentile))
}

function Get-FHMetricScore {
    param(
        [Parameter(Mandatory=$true)][object]$Evidence,
        [Parameter(Mandatory=$true)][double[]]$PeerValues
    )
    if (-not [bool]$Evidence.Available) { return $null }
    $direction = if ([double]$Evidence.Direction -lt 0.0) { -1.0 } else { 1.0 }
    if ([string]$Evidence.Mode -eq 'DIRECT') {
        $direct = [Math]::Max(0.0, [Math]::Min(100.0, [double]$Evidence.Value))
        if ($direction -lt 0.0) { $direct = 100.0 - $direct }
        return $direct
    }
    $percentile = Get-FHPercentile -Values $PeerValues -Value ([double]$Evidence.Value)
    $winsorized = [Math]::Max(0.05, [Math]::Min(0.95, $percentile))
    $score = 100.0 * (0.5 + $direction * ($winsorized - 0.5))
    return [Math]::Max(0.0, [Math]::Min(100.0, $score))
}

function Invoke-FundamentalHealthScore {
    [OutputType([pscustomobject])]
    param(
        [Parameter(Mandatory=$true)][object]$Record,
        [Parameter(Mandatory=$true)][object[]]$PeerRecords,
        [Parameter(Mandatory=$true)][object]$Config,
        [AllowNull()][string]$DecisionTime
    )
    $configObject = Get-FHConfigObject $Config
    $decision = Convert-FHDateTimeOffset $DecisionTime
    $profileName = Get-FHProfileName -Record $Record -Config $configObject
    $definitions = Get-FHMetricDefinitions -ProfileName $profileName -Config $configObject
    $sector = [string](Get-FHProperty $Record 'Sector')
    $targetSymbol = [string](Get-FHProperty $Record 'Symbol')

    $contexts = [Collections.Generic.List[object]]::new()
    foreach ($peer in @($PeerRecords)) {
        if ($null -eq $peer) { continue }
        $peerProfile = Get-FHProfileName -Record $peer -Config $configObject
        if ($peerProfile -ne $profileName) { continue }
        $peerSector = [string](Get-FHProperty $peer 'Sector')
        $peerEvidence = @{}
        foreach ($definition in $definitions) {
            $id = [string](Get-FHProperty $definition 'id')
            $peerEvidence[$id] = Get-FHMetricEvidence -Record $peer -Definition $definition -DecisionTime $decision -Config $configObject
        }
        $contexts.Add([pscustomobject]@{
            Record=$peer
            Sector=$peerSector
            Evidence=$peerEvidence
        })
    }
    if ($contexts.Count -eq 0) {
        $contexts.Add([pscustomobject]@{
            Record=$Record
            Sector=$sector
            Evidence=@{}
        })
    }

    $targetEvidence = @{}
    foreach ($definition in $definitions) {
        $id = [string](Get-FHProperty $definition 'id')
        $targetEvidence[$id] = Get-FHMetricEvidence -Record $Record -Definition $definition -DecisionTime $decision -Config $configObject
    }

    $blocksConfig = Get-FHProperty $configObject 'blocks'
    $blockResults = [Collections.Generic.List[object]]::new()
    $allMissing = [Collections.Generic.List[string]]::new()
    $allInvalid = [Collections.Generic.List[string]]::new()
    $allFlags = [Collections.Generic.List[string]]::new()
    $weightedBase = 0.0
    $availableBlockWeight = 0.0
    $coverageWeighted = 0.0
    $freshnessWeighted = 0.0
    $criticalMissingWeight = 0.0
    $criticalTotalWeight = 0.0

    foreach ($blockProperty in $blocksConfig.PSObject.Properties) {
        $blockName = [string]$blockProperty.Name
        $blockConfig = $blockProperty.Value
        $blockWeight = Convert-FHNumber (Get-FHProperty $blockConfig 'weight')
        $blockDefinitions = @($definitions | Where-Object {
            [string](Get-FHProperty $_ 'block') -eq $blockName
        })
        if ($blockDefinitions.Count -eq 0) {
            $blockResults.Add([pscustomobject]@{
                Block=$blockName;Weight=$blockWeight;Score=$null;Coverage=0.0;AvailableWeight=0.0
                Freshness=0.0;Status='NOT_APPLICABLE';Metrics=@()
            })
            continue
        }
        $availableWeight = 0.0
        $weightedScore = 0.0
        $freshnessSum = 0.0
        $metricResults = [Collections.Generic.List[object]]::new()
        $criticalBlockMissing = 0.0
        $criticalBlockTotal = 0.0
        foreach ($definition in $blockDefinitions) {
            $id = [string](Get-FHProperty $definition 'id')
            $weight = Convert-FHNumber (Get-FHProperty $definition 'weight')
            $evidence = $targetEvidence[$id]
            $peerContexts = @($contexts | Where-Object {
                $peerSector = [string]$_.Sector
                if (-not [string]::IsNullOrWhiteSpace($sector)) {
                    $peerSector -eq $sector
                } else {
                    $true
                }
            })
            $peerValues = @($peerContexts | ForEach-Object {
                $peerMetric = $_.Evidence[$id]
                if ($null -ne $peerMetric -and [bool]$peerMetric.Available) {
                    [double]$peerMetric.Value
                }
            })
            if ($peerValues.Count -eq 0 -and [bool]$evidence.Available) {
                $peerValues = @([double]$evidence.Value)
                $allFlags.Add("PEER_FALLBACK_$id")
            }
            $metricScore = Get-FHMetricScore -Evidence $evidence -PeerValues ([double[]]$peerValues)
            $metricResults.Add([pscustomobject]@{
                MetricId=$id
                Score=$metricScore
                Value=$evidence.Value
                Available=$evidence.Available
                Critical=$evidence.Critical
                Weight=$weight
                Freshness=$evidence.Freshness
                Reason=$evidence.Reason
                EvidenceId=$evidence.EvidenceId
                Source=$evidence.Source
                ReleaseTimestamp=$evidence.ReleaseTimestamp
                PeerCount=$peerValues.Count
            })
            if ($evidence.Critical) { $criticalTotalWeight += $weight }
            if (-not $evidence.Available) {
                $allMissing.Add($id)
                if ($evidence.Reason -ne 'MISSING_VALUE') { $allInvalid.Add("${id}:$($evidence.Reason)") }
                if ($evidence.Critical) { $criticalBlockMissing += $weight }
                $allFlags.Add("${id}:$($evidence.Reason)")
                continue
            }
            $availableWeight += $weight
            $weightedScore += [double]$metricScore * $weight
            $freshnessSum += $evidence.Freshness * $weight
        }
        $totalWeight = ($blockDefinitions | ForEach-Object { Convert-FHNumber (Get-FHProperty $_ 'weight') } | Measure-Object -Sum).Sum
        $coverage = if ($totalWeight -gt 0.0) { $availableWeight / [double]$totalWeight } else { 0.0 }
        $blockScore = if ($availableWeight -gt 0.0) { $weightedScore / $availableWeight } else { $null }
        $blockFreshness = if ($availableWeight -gt 0.0) { $freshnessSum / $availableWeight } else { 0.0 }
        $blockStatus = if ($availableWeight -le 0.0) { 'UNAVAILABLE' } elseif ($coverage -lt (Convert-FHNumber (Get-FHProperty $configObject.gates 'min_block_coverage'))) { 'PARTIAL' } else { 'AVAILABLE' }
        $blockResults.Add([pscustomobject]@{
            Block=$blockName
            Weight=$blockWeight
            Score=$blockScore
            Coverage=$coverage
            AvailableWeight=$availableWeight
            Freshness=$blockFreshness
            Status=$blockStatus
            Metrics=@($metricResults)
        })
        if ($null -ne $blockScore) {
            $weightedBase += $blockScore * $blockWeight
            $availableBlockWeight += $blockWeight
        }
        $coverageWeighted += $blockWeight * $coverage
        $freshnessWeighted += $blockWeight * $blockFreshness
        $criticalMissingWeight += $criticalBlockMissing
    }

    $baseScore = if ($availableBlockWeight -gt 0.0) { $weightedBase / $availableBlockWeight } else { $null }
    $coverageOverall = [Math]::Max(0.0, [Math]::Min(1.0, $coverageWeighted / 100.0))
    $freshnessOverall = [Math]::Max(0.0, [Math]::Min(1.0, $freshnessWeighted / 100.0))
    $confidence = $coverageOverall * $freshnessOverall
    $criticalFraction = if ($criticalTotalWeight -gt 0.0) { $criticalMissingWeight / $criticalTotalWeight } else { 0.0 }
    $criticalMax = Convert-FHNumber (Get-FHProperty (Get-FHProperty $configObject 'gates') 'critical_missing_max_fraction')
    $confidenceFloor = Convert-FHNumber (Get-FHProperty (Get-FHProperty $configObject 'gates') 'confidence_floor')
    $scoreCap = Convert-FHNumber (Get-FHProperty (Get-FHProperty $configObject 'gates') 'unverified_score_cap')
    $status = 'VERIFIED'
    $eligible = $true
    $score = $baseScore
    if ($null -eq $baseScore) {
        $status = 'INSUFFICIENT_DATA'
        $eligible = $false
        $score = $null
    } elseif ($criticalFraction -gt $criticalMax) {
        $status = 'INSUFFICIENT_DATA'
        $eligible = $false
        $score = $null
        $allFlags.Add('CRITICAL_MISSING_HARD_GATE')
    } elseif ($confidence -lt $confidenceFloor) {
        $status = 'UNVERIFIED'
        $eligible = $false
        $score = [Math]::Min($scoreCap, [double]$baseScore * $confidence)
        $allFlags.Add('LOW_EVIDENCE_CONFIDENCE')
    } elseif ($confidence -lt 0.999999) {
        $status = 'PARTIAL'
        $score = [double]$baseScore * $confidence
    }
    $symbol = if ([string]::IsNullOrWhiteSpace($targetSymbol)) { $null } else { $targetSymbol }
    return [pscustomobject]@{
        Protocol=[string](Get-FHProperty $configObject 'protocol')
        Symbol=$symbol
        Profile=$profileName
        Sector=if ([string]::IsNullOrWhiteSpace($sector)) { $null } else { $sector }
        DecisionTime=if ($null -ne $decision) { $decision.ToString('o') } else { $null }
        Status=$status
        Eligible=$eligible
        UnderlyingQualityScore=$score
        BaseScore=$baseScore
        DataConfidence=$confidence
        Coverage=$coverageOverall
        Freshness=$freshnessOverall
        CriticalMissingFraction=$criticalFraction
        MissingMetrics=@($allMissing | Select-Object -Unique)
        InvalidMetrics=@($allInvalid | Select-Object -Unique)
        Flags=@($allFlags | Select-Object -Unique)
        Blocks=@($blockResults)
        Evidence=@($definitions | ForEach-Object { $targetEvidence[[string](Get-FHProperty $_ 'id')] })
        PeerCount=$contexts.Count
        ScoreJoinStatus=if ([bool](Get-FHProperty $configObject 'production_join')) { 'ENABLED' } else { 'SHADOW_ONLY' }
    }
}

function Invoke-FundamentalHealthBatch {
    [OutputType([object[]])]
    param(
        [Parameter(Mandatory=$true)][object[]]$Records,
        [Parameter(Mandatory=$true)][object]$Config,
        [AllowNull()][string]$DecisionTime
    )
    $results = [Collections.Generic.List[object]]::new()
    foreach ($record in @($Records)) {
        $results.Add((Invoke-FundamentalHealthScore -Record $record -PeerRecords $Records -Config $Config -DecisionTime $DecisionTime))
    }
    return @($results)
}

function Get-RealGrowthExact {
    param(
        [AllowNull()][object]$NominalGrowth,
        [AllowNull()][object]$AlignedInflation
    )
    $nominal = Convert-FHNumber $NominalGrowth
    $inflation = Convert-FHNumber $AlignedInflation
    if ($null -eq $nominal -or $null -eq $inflation -or $inflation -le -1.0) { return $null }
    return ((1.0 + $nominal) / (1.0 + $inflation)) - 1.0
}

function Get-EarningsYield {
    param(
        [AllowNull()][object]$TtmEps,
        [AllowNull()][object]$Price
    )
    $eps = Convert-FHNumber $TtmEps
    $priceNumber = Convert-FHNumber $Price
    if ($null -eq $eps -or $null -eq $priceNumber -or $priceNumber -le 0.0) { return $null }
    return $eps / $priceNumber
}

function Get-PriceToEarnings {
    param(
        [AllowNull()][object]$TtmEps,
        [AllowNull()][object]$Price
    )
    $eps = Convert-FHNumber $TtmEps
    $priceNumber = Convert-FHNumber $Price
    if ($null -eq $eps -or $null -eq $priceNumber -or $eps -le 0.0) { return $null }
    return $priceNumber / $eps
}

function Get-DividendYield {
    param(
        [AllowNull()][object]$Dps,
        [AllowNull()][object]$Price
    )
    $dpsNumber = Convert-FHNumber $Dps
    $priceNumber = Convert-FHNumber $Price
    if ($null -eq $dpsNumber -or $null -eq $priceNumber -or $priceNumber -le 0.0) { return $null }
    return $dpsNumber / $priceNumber
}

function Get-ChartCoordinate {
    param(
        [AllowNull()][object]$Value,
        [AllowNull()][object[]]$Values,
        [double]$Epsilon=0.000000001
    )
    $valueNumber = Convert-FHNumber $Value
    $numbers = @($Values | ForEach-Object { Convert-FHNumber $_ } | Where-Object { $null -ne $_ })
    if ($null -eq $valueNumber -or $numbers.Count -eq 0) { return $null }
    $minimum = ($numbers | Measure-Object -Minimum).Minimum
    $maximum = ($numbers | Measure-Object -Maximum).Maximum
    $range = [double]$maximum - [double]$minimum
    if ([Math]::Abs($range) -lt $Epsilon) { return 92.5 }
    $normalized = ($valueNumber - $minimum) / [Math]::Max($range, $Epsilon)
    $normalized = [Math]::Max(0.0, [Math]::Min(1.0, $normalized))
    return 150.0 - (115.0 * $normalized)
}

Export-ModuleMember -Function *
