Import-Module -Force (Join-Path $PSScriptRoot '..\engines\underlying\TsetmcUnderlyingEngine.psm1')
$symbols = @(
    -join ([char]0x0648, [char]0x0628, [char]0x0645, [char]0x0644, [char]0x062A),
    -join ([char]0x0648, [char]0x0628, [char]0x0635, [char]0x0627, [char]0x062F, [char]0x0631),
    -join ([char]0x0648, [char]0x062A, [char]0x062C, [char]0x0627, [char]0x0631, [char]0x062A),
    -join ([char]0x0633, [char]0x0627, [char]0x0645, [char]0x0627, [char]0x0646)
)
foreach($symbol in $symbols){
    try {
        $x = Get-TsetmcUnderlyingSnapshot -Symbol $symbol
        [pscustomobject]@{
            Symbol=$x.Symbol; Status=$x.Status; Price=$x.Price; Return5D=$x.Return5D
            RSI14=$x.RSI14; SMA5=$x.SMA5; SMA20=$x.SMA20
            IndividualRatio=$x.IndividualBuySellVolumeRatio
            LegalRatio=$x.LegalBuySellVolumeRatio
            Trend=$x.TrendBias; MessageCount=$x.MessageCount; AsOf=$x.AsOf
        } | ConvertTo-Json -Compress
    } catch {
        [pscustomobject]@{Symbol=$symbol;Status='ERROR';Error=$_.Exception.Message} | ConvertTo-Json -Compress
    }
}
