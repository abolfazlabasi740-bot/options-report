Set-StrictMode -Version Latest

function Invoke-TsetmcJson {
    param([Parameter(Mandatory=$true)][string]$Uri)
    $headers=@{'User-Agent'='Mozilla/5.0'}
    return Invoke-RestMethod -Uri $Uri -Headers $headers -Method Get -TimeoutSec 25
}

function Get-TsetmcInstrument {
    param([Parameter(Mandatory=$true)][string]$Symbol)
    $encoded=[Uri]::EscapeDataString($Symbol)
    $response=Invoke-TsetmcJson "https://cdn.tsetmc.com/api/Instrument/GetInstrumentSearch/$encoded"
    $items=@($response.instrumentSearch)
    if($items.Count -eq 0){return $null}
    return $items|Where-Object{$_.lVal18AFC -eq $Symbol}|Select-Object -First 1
}

function Get-RatioOrNull {
    param([AllowNull()][object]$Numerator,[AllowNull()][object]$Denominator)
    if($null -eq $Numerator -or $null -eq $Denominator -or [double]$Denominator -eq 0){return $null}
    return [double]$Numerator/[double]$Denominator
}

function Get-Rsi14 {
    param([double[]]$Closes)
    $values=@($Closes|Where-Object{$null -ne $_})
    if($values.Count -lt 15){return $null}
    $gains=0.0;$losses=0.0
    for($i=1;$i -le 14;$i++){
        $delta=$values[$i-1]-$values[$i]
        if($delta -gt 0){$gains+=$delta}else{$losses+=[Math]::Abs($delta)}
    }
    if($losses -eq 0){return 100.0}
    $rs=($gains/14.0)/($losses/14.0)
    return 100.0-(100.0/(1.0+$rs))
}

function Get-TsetmcUnderlyingSnapshot {
    [OutputType([pscustomobject])]
    param([Parameter(Mandatory=$true)][string]$Symbol)
    try{
        $instrument=Get-TsetmcInstrument -Symbol $Symbol
        if($null -eq $instrument){return [pscustomobject]@{Symbol=$Symbol;Status='NOT_FOUND';Error='Instrument not found'}}
        $insCode=[string]$instrument.insCode
        $quote=(Invoke-TsetmcJson "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceInfo/$insCode").closingPriceInfo
        $client=(Invoke-TsetmcJson "https://cdn.tsetmc.com/api/ClientType/GetClientType/$insCode/1/0").clientType
        $history=@((Invoke-TsetmcJson "https://cdn.tsetmc.com/api/ClosingPrice/GetClosingPriceDailyList/$insCode/0").closingPriceDaily)
        $history=$history|Where-Object{$null -ne $_.pDrCotVal -and [double]$_.pDrCotVal -gt 0}|Sort-Object dEven -Descending
        $closes=@($history|ForEach-Object{[double]$_.pDrCotVal})
        $latest=[double]$closes[0]
        $close5=if($closes.Count -ge 6){[double]$closes[5]}else{$null}
        $close20=if($closes.Count -ge 20){[double]$closes[19]}else{$null}
        $sma5=if($closes.Count -ge 5){($closes[0..4]|Measure-Object -Average).Average}else{$null}
        $sma20=if($closes.Count -ge 20){($closes[0..19]|Measure-Object -Average).Average}else{$null}
        $ret5=if($null -ne $close5 -and $close5 -gt 0){($latest/$close5-1.0)*100.0}else{$null}
        $rsi=Get-Rsi14 -Closes $closes
        $individualRatio=Get-RatioOrNull $client.buy_I_Volume $client.sell_I_Volume
        $legalRatio=Get-RatioOrNull $client.buy_N_Volume $client.sell_N_Volume
        $flow=if($null -ne $client.buy_I_Volume -and $null -ne $client.sell_I_Volume){[double]$client.buy_I_Volume-[double]$client.sell_I_Volume}else{$null}
        $trendPoints=0
        if($null -ne $ret5){if($ret5 -gt 3){$trendPoints++}elseif($ret5 -lt -3){$trendPoints--}}
        if($null -ne $sma5){if($latest -gt $sma5){$trendPoints++}else{$trendPoints--}}
        if($null -ne $sma20){if($latest -gt $sma20){$trendPoints++}else{$trendPoints--}}
        if($null -ne $rsi){if($rsi -ge 55){$trendPoints++}elseif($rsi -le 45){$trendPoints--}}
        $bias=if($trendPoints -ge 2){'BULLISH'}elseif($trendPoints -le -2){'BEARISH'}else{'NEUTRAL'}
        $messages=@()
        try{$messages=@((Invoke-TsetmcJson "https://cdn.tsetmc.com/api/Msg/GetMsgByInsCode/$insCode").msg|Select-Object -First 5)}catch{$messages=@()}
        return [pscustomobject]@{
            Symbol=$Symbol;InstrumentCode=$insCode;InstrumentName=$instrument.lVal30;Status='OK'
            AsOf=[string]$quote.dEven;Price=$latest;PriceYesterday=$quote.priceYesterday
            Return5D=$ret5;SMA5=$sma5;SMA20=$sma20;RSI14=$rsi;TrendPoints=$trendPoints;TrendBias=$bias
            IndividualBuySellVolumeRatio=$individualRatio;LegalBuySellVolumeRatio=$legalRatio
            IndividualNetVolume=$flow;IndividualBuyCount=$client.buy_CountI;IndividualSellCount=$client.sell_CountI
            LegalBuyCount=$client.buy_CountN;LegalSellCount=$client.sell_CountN
            Messages=$messages;MessageCount=$messages.Count;Source='TSETMC CDN API'
        }
    }catch{
        return [pscustomobject]@{Symbol=$Symbol;Status='ERROR';Error=$_.Exception.Message;Source='TSETMC CDN API'}
    }
}

Export-ModuleMember -Function *
