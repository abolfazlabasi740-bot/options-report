Set-StrictMode -Version Latest

function New-FactorBreakdown {
    param(
        [Parameter(Mandatory=$true)][string]$Block,
        [Parameter(Mandatory=$true)][double]$BlockWeight,
        [Parameter(Mandatory=$true)][object[]]$Factors
    )
    $availableWeight = 0.0
    foreach ($factor in $Factors) {
        if ($null -ne $factor.Score) { $availableWeight += [double]$factor.Weight }
    }
    return @($Factors | ForEach-Object {
        $contribution = if ($null -ne $_.Score -and $availableWeight -gt 0.0) {
            $BlockWeight * ([double]$_.Score * [double]$_.Weight / $availableWeight)
        } else {
            $null
        }
        [pscustomobject]@{
            Block=$Block
            Factor=$_.Name
            RawValue=$_.RawValue
            NormalizedScore=$_.Score
            ConfiguredWeight=[double]$_.Weight
            AvailableBlockWeight=$availableWeight
            WeightedContribution=$contribution
            Missing=($null -eq $_.Score)
        }
    })
}

function Get-ApprovedStatusScore {
    param([AllowNull()][string]$Status,[Parameter(Mandatory=$true)][object]$Config)
    if ([string]::IsNullOrWhiteSpace($Status)) { return $null }
    $property = $Config.market_structure.status_scores.PSObject.Properties |
        Where-Object { $_.Name -eq $Status } |
        Select-Object -First 1
    if ($null -eq $property) { return $null }
    $score = [double]$property.Value
    if ($score -lt 0.0 -or $score -gt 1.0) {
        throw "Configured Status score must be between zero and one: $Status=$score"
    }
    return $score
}

function Invoke-V3Scoring {
    param(
        [Parameter(Mandatory=$true)][object[]]$Contracts,
        [Parameter(Mandatory=$true)][object]$Config
    )
    $metrics = @(
        'TradeValue','Volume','OI','SpreadRatio','Depth','BSDiff','IV','IVHV','TimeCost',
        'BEDistance','Leverage','StrikeDiff','TradingDays','CalendarDays','ThetaRatio',
        'Delta','Gamma','Vega','Rho','LastVsClosePct','IntradayRangePct'
    )
    $arrays = @{}
    foreach ($name in $metrics) {
        $arrays[$name] = @($Contracts | ForEach-Object { $_.$name } | Where-Object { $null -ne $_ })
    }
    $arrays.AbsDelta = @($Contracts | ForEach-Object { if ($null -ne $_.Delta) {[Math]::Abs($_.Delta)} })
    $arrays.AbsStrikeDiff = @($Contracts | ForEach-Object { if ($null -ne $_.StrikeDiff) {[Math]::Abs($_.StrikeDiff)} })
    $bw = $Config.block_weights
    $fw = $Config.factor_weights

    foreach ($x in $Contracts) {
        $p = @{}
        foreach ($name in $metrics) {
            $value = $x.$name
            $p[$name] = if ($null -ne $value) {
                Get-PercentileRank -Values $arrays[$name] -Value ([double]$value)
            } else {
                $null
            }
        }

        $valueScore = $p.TradeValue
        $volumeScore = $p.Volume
        $oiScore = if ($null -ne $p.OI) {$p.OI*[Math]::Sqrt($valueScore*$volumeScore)} else {$null}
        $spreadScore = if ($null -ne $p.SpreadRatio) {1.0-$p.SpreadRatio} else {$null}
        $liquidityFactors = @(
            [pscustomobject]@{Name='TradeValue';Weight=$fw.liquidity.trade_value;Score=$valueScore;RawValue=$x.TradeValue},
            [pscustomobject]@{Name='Volume';Weight=$fw.liquidity.volume;Score=$volumeScore;RawValue=$x.Volume},
            [pscustomobject]@{Name='OpenInterest';Weight=$fw.liquidity.open_interest;Score=$oiScore;RawValue=$x.OI},
            [pscustomobject]@{Name='Spread';Weight=$fw.liquidity.spread;Score=$spreadScore;RawValue=$x.SpreadRatio},
            [pscustomobject]@{Name='Depth';Weight=$fw.liquidity.depth;Score=$p.Depth;RawValue=$x.Depth}
        )
        $b1 = Get-WeightedBlock -BlockWeight $bw.liquidity -Factors $liquidityFactors

        $bsScore = if ($null -ne $p.BSDiff) {1.0-$p.BSDiff} else {$null}
        $ivScore = if ($null -ne $p.IV) {1.0-$p.IV} else {$null}
        $ivHvScore = if ($null -ne $p.IVHV) {1.0-$p.IVHV} else {$null}
        $timeCostScore = if ($null -ne $p.TimeCost) {1.0-$p.TimeCost} else {$null}
        $valuationFactors = @(
            [pscustomobject]@{Name='BlackScholesDifference';Weight=$fw.valuation.black_scholes_difference;Score=$bsScore;RawValue=$x.BSDiff},
            [pscustomobject]@{Name='IV';Weight=$fw.valuation.iv;Score=$ivScore;RawValue=$x.IV},
            [pscustomobject]@{Name='IVHV';Weight=$fw.valuation.iv_hv;Score=$ivHvScore;RawValue=$x.IVHV},
            [pscustomobject]@{Name='TimeValue';Weight=$fw.valuation.time_value;Score=$timeCostScore;RawValue=$x.TimeCost}
        )
        $b2 = Get-WeightedBlock -BlockWeight $bw.valuation -Factors $valuationFactors

        $beScore = 1.0-$p.BEDistance
        $levScore = Get-CenteredScore $p.Leverage
        $absDeltaP = if ($null -ne $x.Delta) {
            Get-PercentileRank $arrays.AbsDelta ([Math]::Abs($x.Delta))
        } else {$null}
        $deltaCenter = if ($null -ne $absDeltaP) {Get-CenteredScore $absDeltaP} else {$null}
        $absStrikeP = if ($null -ne $x.StrikeDiff) {
            Get-PercentileRank $arrays.AbsStrikeDiff ([Math]::Abs($x.StrikeDiff))
        } else {$null}
        $moneyness = if ($null -ne $absStrikeP -and $null -ne $deltaCenter) {
            ((1.0-$absStrikeP)+$deltaCenter)/2.0
        } elseif ($null -ne $absStrikeP) {
            1.0-$absStrikeP
        } else {
            $deltaCenter
        }
        $payoffFactors = @(
            [pscustomobject]@{Name='BreakevenDistance';Weight=$fw.payoff.breakeven_distance;Score=$beScore;RawValue=$x.BEDistance},
            [pscustomobject]@{Name='Leverage';Weight=$fw.payoff.leverage;Score=$levScore;RawValue=$x.Leverage},
            [pscustomobject]@{Name='Moneyness';Weight=$fw.payoff.moneyness;Score=$moneyness;RawValue=$x.StrikeDiff}
        )
        $b3 = Get-WeightedBlock -BlockWeight $bw.payoff -Factors $payoffFactors

        $tradingScore = if ($null -ne $p.TradingDays) {[Math]::Sqrt($p.TradingDays)} else {$null}
        $calendarScore = if ($null -ne $p.CalendarDays) {[Math]::Sqrt($p.CalendarDays)} else {$null}
        $thetaScore = if ($null -ne $p.ThetaRatio) {1.0-$p.ThetaRatio} else {$null}
        $timeFactors = @(
            [pscustomobject]@{Name='TradingDays';Weight=$fw.time.trading_days;Score=$tradingScore;RawValue=$x.TradingDays},
            [pscustomobject]@{Name='CalendarDays';Weight=$fw.time.calendar_days;Score=$calendarScore;RawValue=$x.CalendarDays},
            [pscustomobject]@{Name='Theta';Weight=$fw.time.theta;Score=$thetaScore;RawValue=$x.ThetaRatio}
        )
        $b4 = Get-WeightedBlock -BlockWeight $bw.time -Factors $timeFactors

        $gammaScore = if ($null -ne $p.Gamma) {
            if ($null -ne $tradingScore) {$p.Gamma*$tradingScore} else {$p.Gamma}
        } else {$null}
        $vegaScore = if ($null -ne $p.Vega) {
            if ($null -ne $ivScore) {$p.Vega*$ivScore} else {$p.Vega}
        } else {$null}
        $rhoScore = if ($null -ne $p.Rho) {Get-CenteredScore $p.Rho} else {$null}
        $greekFactors = @(
            [pscustomobject]@{Name='Delta';Weight=$fw.greeks.delta;Score=$deltaCenter;RawValue=$x.Delta},
            [pscustomobject]@{Name='Gamma';Weight=$fw.greeks.gamma;Score=$gammaScore;RawValue=$x.Gamma},
            [pscustomobject]@{Name='Vega';Weight=$fw.greeks.vega;Score=$vegaScore;RawValue=$x.Vega},
            [pscustomobject]@{Name='Rho';Weight=$fw.greeks.rho;Score=$rhoScore;RawValue=$x.Rho}
        )
        $b5 = Get-WeightedBlock -BlockWeight $bw.greeks -Factors $greekFactors

        $lastVsCloseScore = if ($null -ne $p.LastVsClosePct) {1.0-$p.LastVsClosePct} else {$null}
        $rangeScore = if ($null -ne $p.IntradayRangePct) {1.0-$p.IntradayRangePct} else {$null}
        $statusScore = Get-ApprovedStatusScore -Status $x.Status -Config $Config
        $marketFactors = @(
            [pscustomobject]@{Name='LastVsClose';Weight=$fw.market.last_vs_close;Score=$lastVsCloseScore;RawValue=$x.LastVsClosePct},
            [pscustomobject]@{Name='IntradayRange';Weight=$fw.market.intraday_range;Score=$rangeScore;RawValue=$x.IntradayRangePct},
            [pscustomobject]@{Name='Status';Weight=$fw.market.status;Score=$statusScore;RawValue=$x.Status}
        )
        $b6 = Get-WeightedBlock -BlockWeight $bw.market -Factors $marketFactors

        $blocks = @($b1,$b2,$b3,$b4,$b5,$b6)
        if (@($blocks | Where-Object {$null -eq $_}).Count -gt 0) {
            throw "A complete scoring block is unavailable for $($x.Symbol)."
        }
        $baseBeforeVolumePenalty = ($blocks | Measure-Object -Sum).Sum
        $volumePenalty = if ($null -ne $p.Volume) {
            $volumeScoreForPenalty = [Math]::Max(0.0,[Math]::Min(1.0,[double]$p.Volume))
            [double]$Config.liquidity_controls.low_volume_penalty.max_points *
                (1.0 - [Math]::Sqrt($volumeScoreForPenalty))
        } else {
            0.0
        }
        $base = [Math]::Max(0.0,$baseBeforeVolumePenalty-$volumePenalty)
        $breakdown = @(
            New-FactorBreakdown -Block 'Liquidity' -BlockWeight $bw.liquidity -Factors $liquidityFactors
            New-FactorBreakdown -Block 'Valuation' -BlockWeight $bw.valuation -Factors $valuationFactors
            New-FactorBreakdown -Block 'Payoff' -BlockWeight $bw.payoff -Factors $payoffFactors
            New-FactorBreakdown -Block 'Time' -BlockWeight $bw.time -Factors $timeFactors
            New-FactorBreakdown -Block 'Greeks' -BlockWeight $bw.greeks -Factors $greekFactors
            New-FactorBreakdown -Block 'MarketStructure' -BlockWeight $bw.market -Factors $marketFactors
        )
        $x | Add-Member BaseScore $base -Force
        $x | Add-Member BaseScoreBeforeVolumePenalty $baseBeforeVolumePenalty -Force
        $x | Add-Member LiquidityVolumeScore $p.Volume -Force
        $x | Add-Member LiquidityVolumePenalty $volumePenalty -Force
        $x | Add-Member BlockLiquidity $b1 -Force
        $x | Add-Member BlockValuation $b2 -Force
        $x | Add-Member BlockPayoff $b3 -Force
        $x | Add-Member BlockTime $b4 -Force
        $x | Add-Member BlockGreeks $b5 -Force
        $x | Add-Member BlockMarket $b6 -Force
        $x | Add-Member FactorBreakdown $breakdown -Force
        $x | Add-Member RiskPercentiles ([pscustomobject]@{
            Leverage=$p.Leverage
            TradingDays=$p.TradingDays
            ThetaRatio=$p.ThetaRatio
            IVHV=$p.IVHV
            BEDistance=$p.BEDistance
            Volume=$p.Volume
        }) -Force
    }
    return @($Contracts | Sort-Object @{Expression='BaseScore';Descending=$true},@{Expression='TradeValue';Descending=$true},@{Expression='Symbol';Descending=$false})
}

Export-ModuleMember -Function *
