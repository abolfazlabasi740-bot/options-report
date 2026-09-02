Set-StrictMode -Version Latest

function Get-SevenDayWorkbookDate {
    param([Parameter(Mandatory=$true)][System.IO.FileInfo]$File)
    if ($File.Name -match 'optionschool24_all_(\d+)\.xlsx$') {
        try {
            $stamp = [int64]$Matches[1]
            if ($stamp -gt 100000000000) {
                return [DateTimeOffset]::FromUnixTimeMilliseconds($stamp).UtcDateTime.AddHours(3.5).Date
            }
            return [DateTimeOffset]::FromUnixTimeSeconds($stamp).UtcDateTime.AddHours(3.5).Date
        } catch {}
    }
    return $File.LastWriteTime.Date
}

function Get-SevenDayFiles {
    param(
        [Parameter(Mandatory=$true)][string]$RawDirectory,
        [AllowNull()][string]$CurrentWorkbookPath
    )
    $files = @()
    if (Test-Path -LiteralPath $RawDirectory -PathType Container) {
        $files += @(Get-ChildItem -LiteralPath $RawDirectory -File -Filter 'optionschool24_all_*.xlsx')
    }
    if (-not [string]::IsNullOrWhiteSpace($CurrentWorkbookPath) -and
        (Test-Path -LiteralPath $CurrentWorkbookPath -PathType Leaf)) {
        $files += @(Get-Item -LiteralPath $CurrentWorkbookPath)
    }
    $unique = @{}
    foreach ($file in $files) {
        $unique[$file.FullName.ToLowerInvariant()] = $file
    }
    return @($unique.Values)
}

function Get-SevenDayContractMap {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [Parameter(Mandatory=$true)][object]$Config
    )
    $parsed = Read-OptionsWorkbookWithOpenXml -ResolvedPath $Path -Config $Config
    $financial = Convert-ToFinancialContracts -Rows $parsed.Rows
    $map = @{}
    foreach ($contract in @($financial.Contracts)) {
        $map[[string]$contract.Symbol] = $contract
    }
    return $map
}

function Get-SevenDayCauseTags {
    param(
        [Parameter(Mandatory=$true)][object]$Previous,
        [Parameter(Mandatory=$true)][object]$Current,
        [AllowNull()][double]$UnderlyingReturnPct
    )
    $tags = [Collections.Generic.List[string]]::new()
    if ($null -ne $UnderlyingReturnPct -and
        [Math]::Abs($UnderlyingReturnPct) -ge 1.0 -and
        ([double]$Current.Last -gt [double]$Previous.Last) -eq ($UnderlyingReturnPct -gt 0)) {
        $tags.Add('UNDERLYING_MOVE_CORRELATED')
    }
    if ($null -ne $Current.Leverage -and [double]$Current.Leverage -ge 3.0) {
        $tags.Add('LEVERAGE_AMPLIFIER')
    }
    if ($null -ne $Previous.Volume -and [double]$Previous.Volume -gt 0 -and
        $null -ne $Current.Volume -and [double]$Current.Volume -gt 0) {
        $volumeChange = ([double]$Current.Volume / [double]$Previous.Volume) - 1.0
        if ($volumeChange -ge 0.50) { $tags.Add('VOLUME_FLOW_INCREASE') }
        elseif ($volumeChange -le -0.50) { $tags.Add('VOLUME_FLOW_CONTRACTED') }
    }
    if ($null -ne $Previous.IV -and $null -ne $Current.IV -and
        [double]$Previous.IV -gt 0) {
        $ivChange = ([double]$Current.IV / [double]$Previous.IV) - 1.0
        if ($ivChange -ge 0.15) { $tags.Add('IV_EXPANSION_CORRELATED') }
        elseif ($ivChange -le -0.15) { $tags.Add('IV_COMPRESSION') }
    }
    if ($null -ne $Current.SpreadRatio -and [double]$Current.SpreadRatio -gt 0.10) {
        $tags.Add('WIDE_SPREAD_EXECUTION_RISK')
    }
    if ($null -ne $Current.RemainingDays -and [double]$Current.RemainingDays -le 7) {
        $tags.Add('NEAR_EXPIRY_DECAY_RISK')
    }
    if ($tags.Count -eq 0) { $tags.Add('NO_SINGLE_FACTOR_IDENTIFIED') }
    return @($tags | Select-Object -Unique)
}

function Get-SevenDayLearningSummary {
    param(
        [Parameter(Mandatory=$true)][string]$RawDirectory,
        [Parameter(Mandatory=$true)][object]$Config,
        [AllowNull()][string]$CurrentWorkbookPath,
        [int]$TransitionCount = 7,
        [int]$TopCount = 25,
        [double]$MinimumLeverage = 0.0
    )
    $files = @(Get-SevenDayFiles -RawDirectory $RawDirectory -CurrentWorkbookPath $CurrentWorkbookPath)
    if ($files.Count -eq 0) {
        return [pscustomobject]@{
            Status='NO_SNAPSHOTS'; WindowStart=$null; WindowEnd=$null
            SnapshotFiles=@(); Transitions=@(); DailyTop=@(); CumulativeTop=@()
            Notes=@('No retained Optionschool workbooks were available for seven-day comparison.')
        }
    }

    $byDate = @{}
    foreach ($file in $files) {
        $date = Get-SevenDayWorkbookDate -File $file
        $key = $date.ToString('yyyy-MM-dd')
        if (-not $byDate.ContainsKey($key) -or
            $file.LastWriteTime -gt $byDate[$key].File.LastWriteTime) {
            $byDate[$key] = [pscustomobject]@{ Date=$date; File=$file }
        }
    }
    $ordered = @($byDate.Values | Sort-Object Date)
    if ($ordered.Count -gt ($TransitionCount + 1)) {
        $ordered = @($ordered | Select-Object -Last ($TransitionCount + 1))
    }

    $snapshots = @()
    foreach ($item in $ordered) {
        try {
            $snapshots += [pscustomobject]@{
                Date=$item.Date.ToString('yyyy-MM-dd')
                Path=$item.File.FullName
                FileName=$item.File.Name
                Rows=(Get-SevenDayContractMap -Path $item.File.FullName -Config $Config)
                Error=$null
            }
        } catch {
            $snapshots += [pscustomobject]@{
                Date=$item.Date.ToString('yyyy-MM-dd')
                Path=$item.File.FullName
                FileName=$item.File.Name
                Rows=@{}
                Error=$_.Exception.Message
            }
        }
    }

    $transitions = [Collections.Generic.List[object]]::new()
    for ($i=1; $i -lt $snapshots.Count; $i++) {
        $previous = $snapshots[$i-1]
        $current = $snapshots[$i]
        if ($previous.Error -or $current.Error) { continue }
        $calendarGapDays = ([datetime]$current.Date - [datetime]$previous.Date).Days
        foreach ($symbol in @($current.Rows.Keys)) {
            if (-not $previous.Rows.ContainsKey($symbol)) { continue }
            $old = $previous.Rows[$symbol]
            $new = $current.Rows[$symbol]
            if ([double]$old.Last -le 0 -or [double]$new.Last -le 0) { continue }
            $returnPct = (([double]$new.Last / [double]$old.Last) - 1.0) * 100.0
            $underlyingReturn = $null
            if ($null -ne $old.Underlying -and [double]$old.Underlying -gt 0 -and
                $null -ne $new.Underlying) {
                $underlyingReturn = (([double]$new.Underlying / [double]$old.Underlying) - 1.0) * 100.0
            }
            $transitions.Add([pscustomobject]@{
                From=$previous.Date; To=$current.Date; Symbol=$symbol
                CalendarGapDays=$calendarGapDays
                Type=$new.Type; PrevLast=[double]$old.Last; Last=[double]$new.Last
                ReturnPct=$returnPct
                UnderlyingPrev=$old.Underlying; UnderlyingLast=$new.Underlying
                UnderlyingReturnPct=$underlyingReturn
                Leverage=$new.Leverage; Volume=$new.Volume; TradeValue=$new.TradeValue
                SpreadRatio=$new.SpreadRatio; BSDiff=$new.BSDiff; IV=$new.IV
                Expiration=$new.Expiration; RemainingDays=$new.RemainingDays
                CauseTags=(Get-SevenDayCauseTags -Previous $old -Current $new -UnderlyingReturnPct $underlyingReturn)
            })
        }
    }

    $eligibleTransitions = @($transitions | Where-Object {
        $MinimumLeverage -le 0.0 -or
        ($null -ne $_.Leverage -and [double]$_.Leverage -ge $MinimumLeverage)
    })
    $dailyTop = @($eligibleTransitions | Sort-Object ReturnPct -Descending | Select-Object -First $TopCount)
    $cumulativeTop = @()
    if ($snapshots.Count -ge 2 -and -not $snapshots[0].Error -and -not $snapshots[-1].Error) {
        $cumulativeCalendarGapDays = ([datetime]$snapshots[-1].Date - [datetime]$snapshots[0].Date).Days
        foreach ($symbol in @($snapshots[-1].Rows.Keys)) {
            if (-not $snapshots[0].Rows.ContainsKey($symbol)) { continue }
            $old = $snapshots[0].Rows[$symbol]
            $new = $snapshots[-1].Rows[$symbol]
            if ([double]$old.Last -le 0 -or [double]$new.Last -le 0) { continue }
            if ($MinimumLeverage -gt 0.0 -and
                ($null -eq $new.Leverage -or [double]$new.Leverage -lt $MinimumLeverage)) { continue }
            $ret = (([double]$new.Last / [double]$old.Last) - 1.0) * 100.0
            $underlyingRet = $null
            if ($null -ne $old.Underlying -and [double]$old.Underlying -gt 0 -and
                $null -ne $new.Underlying) {
                $underlyingRet = (([double]$new.Underlying / [double]$old.Underlying) - 1.0) * 100.0
            }
            $cumulativeTop += [pscustomobject]@{
                From=$snapshots[0].Date; To=$snapshots[-1].Date; Symbol=$symbol
                CalendarGapDays=$cumulativeCalendarGapDays
                Type=$new.Type; PrevLast=[double]$old.Last; Last=[double]$new.Last
                ReturnPct=$ret; UnderlyingReturnPct=$underlyingRet
                Leverage=$new.Leverage; Volume=$new.Volume; TradeValue=$new.TradeValue
                SpreadRatio=$new.SpreadRatio; Expiration=$new.Expiration
                CauseTags=(Get-SevenDayCauseTags -Previous $old -Current $new -UnderlyingReturnPct $underlyingRet)
            }
        }
        $cumulativeTop = @($cumulativeTop | Sort-Object ReturnPct -Descending | Select-Object -First $TopCount)
    }

    $status = if ($snapshots.Count -lt 2) { 'INSUFFICIENT_SNAPSHOTS' }
        elseif ($eligibleTransitions.Count -eq 0) { 'NO_ELIGIBLE_CONTRACTS' }
        else { 'COMPARED' }
    return [pscustomobject]@{
        Status=$status
        WindowStart=$snapshots[0].Date
        WindowEnd=$snapshots[-1].Date
        SnapshotFiles=@($snapshots | ForEach-Object {
            [pscustomobject]@{Date=$_.Date; FileName=$_.FileName; Path=$_.Path; Error=$_.Error}
        })
        RawTransitionCount=$transitions.Count
        EligibleTransitionCount=$eligibleTransitions.Count
        MinimumLeverage=$MinimumLeverage
        Transitions=@($eligibleTransitions)
        DailyTop=$dailyTop
        CumulativeTop=$cumulativeTop
        SharpDaily=@($dailyTop | Where-Object { [double]$_.ReturnPct -ge 20.0 })
        SharpCumulative=@($cumulativeTop | Where-Object { [double]$_.ReturnPct -ge 50.0 })
        Notes=@(
            'CauseTags are correlation hypotheses from point-in-time fields, not proven causal attribution.'
            'Last-to-Last return excludes bid/ask execution, fees, slippage, contract size and exit timing.'
            'Seven-day window uses the latest retained workbook for each available calendar date; market holidays may reduce transitions.'
            "V4 learning output applies the same minimum leverage gate: $MinimumLeverage."
        )
    }
}

Export-ModuleMember -Function *
