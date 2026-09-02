Set-StrictMode -Version Latest

function Convert-ToFinancialContracts {
    param([Parameter(Mandatory=$true)][object[]]$Rows)
    $contracts = [Collections.Generic.List[object]]::new()
    $removed = [ordered]@{
        MissingSymbol=0; MissingStrike=0; MissingUnderlying=0; MissingExpiration=0;
        InvalidLast=0; InvalidVolume=0; InvalidTradeValue=0; CalculationError=0
    }
    $callChar=[char]0x0636
    $putChar=[char]0x0637
    foreach ($row in $Rows) {
        $symbol=([string]$row.C1).Trim()
        if ([string]::IsNullOrWhiteSpace($symbol)) {$removed.MissingSymbol++;continue}
        $strike=Convert-OptionNumber $row.C2
        if ($null-eq$strike -or $strike-le0) {$removed.MissingStrike++;continue}
        $underlying=Convert-OptionNumber $row.C3
        if ($null-eq$underlying -or $underlying-le0) {$removed.MissingUnderlying++;continue}
        $expiration=([string]$row.C5).Trim()
        if ([string]::IsNullOrWhiteSpace($expiration)) {$removed.MissingExpiration++;continue}
        $last=Convert-OptionNumber $row.C11
        if ($null-eq$last -or $last-le0) {$removed.InvalidLast++;continue}
        $volume=Convert-OptionNumber $row.C9
        if ($null-eq$volume -or $volume-le0) {$removed.InvalidVolume++;continue}
        $tradeValue=Convert-OptionNumber $row.C10
        if ($null-eq$tradeValue -or $tradeValue-le0) {$removed.InvalidTradeValue++;continue}
        $type='Unknown'
        if ($symbol[0]-eq$callChar) {$type='Call'} elseif ($symbol[0]-eq$putChar) {$type='Put'}
        if ($type-eq'Unknown') {$removed.CalculationError++;continue}
        if ($type-eq'Put') {
            $breakeven=$strike-$last
            $beDistance=($underlying-$breakeven)/$underlying
        } else {
            $breakeven=$strike+$last
            $beDistance=($breakeven-$underlying)/$underlying
        }
        $leverage=$underlying/$last
        if ([double]::IsNaN($leverage)-or[double]::IsInfinity($leverage)) {$removed.CalculationError++;continue}
        $calendar=Convert-OptionNumber $row.C6
        $trading=Convert-OptionNumber $row.C7
        $remaining=if($null-ne$calendar){[int][Math]::Round($calendar-1.0)}else{$null}
        $oi=Convert-OpenInterest $row.C8
        $spread=Convert-OptionNumber $row.C32
        $bidVolume=Convert-OptionNumber $row.C26
        $askVolume=Convert-OptionNumber $row.C28
        $askPrice=Convert-OptionNumber $row.C29
        $iv=Convert-OptionNumber $row.C23
        $hv=Convert-OptionNumber $row.C24
        $timeValue=Convert-OptionNumber $row.C16
        $bsDiff=Convert-OptionNumber $row.C20
        $strikeDiff=Convert-OptionNumber $row.C4
        $delta=Convert-OptionNumber $row.C34
        $theta=Convert-OptionNumber $row.C35
        $gamma=Convert-OptionNumber $row.C36
        $vega=Convert-OptionNumber $row.C37
        $rho=Convert-OptionNumber $row.C38
        $close=Convert-OptionNumber $row.C13
        $lastPct=Convert-OptionNumber $row.C12
        $closePct=Convert-OptionNumber $row.C14
        $low=Convert-OptionNumber $row.C30
        $high=Convert-OptionNumber $row.C31
        $status=([string]$row.C21).Trim()
        if([string]::IsNullOrWhiteSpace($status)){$status=$null}
        $lastVsClosePct=if($null-ne$lastPct-and$null-ne$closePct){[Math]::Abs($lastPct-$closePct)}else{$null}
        $intradayRangePct=if($null-ne$low-and$null-ne$high-and$last-gt0){[Math]::Abs($high-$low)/$last}else{$null}
        $contracts.Add([pscustomobject]@{
            SourceRow=$row.SourceRow;Symbol=$symbol;Type=$type;Strike=$strike;Underlying=$underlying;
            Expiration=$expiration;Last=$last;Breakeven=$breakeven;BEDistance=$beDistance;Leverage=$leverage;
            CalendarDays=$calendar;RemainingDays=$remaining;TradingDays=$trading;OI=$oi;Volume=$volume;TradeValue=$tradeValue;
            SpreadRatio=if($null-ne$spread){[Math]::Abs($spread)/$last}else{$null};
            Depth=if($null-ne$bidVolume-and$null-ne$askVolume){[Math]::Min($bidVolume,$askVolume)}else{$null};
            IV=$iv;HV=$hv;IVHV=if($null-ne$iv-and$null-ne$hv-and$hv-gt0){$iv/$hv}else{$null};
            TimeCost=if($null-ne$timeValue){$timeValue/$last}else{$null};BSDiff=$bsDiff;StrikeDiff=$strikeDiff;
            Delta=$delta;ThetaRatio=if($null-ne$theta){[Math]::Abs($theta)/$last}else{$null};
            Gamma=$gamma;Vega=$vega;Rho=$rho;
            AskGap=if($null-ne$askPrice-and$askPrice-gt0){[Math]::Abs($askPrice-$last)/$askPrice}else{$null};
            CloseGap=if($null-ne$close-and$close-gt0){[Math]::Abs($last-$close)/$close}else{$null};
            RangeRatio=$intradayRangePct;ChangeGap=$lastVsClosePct;
            LastVsClosePct=$lastVsClosePct;IntradayRangePct=$intradayRangePct;Status=$status
        })
    }
    return [pscustomobject]@{ Contracts=$contracts; RemovedByReason=[pscustomobject]$removed; RemovedRows=($removed.Values|Measure-Object -Sum).Sum }
}

Export-ModuleMember -Function *
