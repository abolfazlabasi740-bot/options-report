param(
    [Parameter(Mandatory=$true)][string]$WorkbookPath,
    [string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot)
)
$ErrorActionPreference='Stop'
$pipeline=Join-Path $ProjectRoot 'scripts/run_pipeline.ps1'
$result=& $pipeline -InputWorkbook $WorkbookPath -ProjectRoot $ProjectRoot -Quiet
if($null-eq$result){throw 'Pipeline returned no result.'}
if($result.Status-ne'COMPLETED'){throw "Pipeline status was $($result.Status)."}
if($result.Top.Count-ne15){throw "Expected 15 top contracts, got $($result.Top.Count)."}
if(-not(Test-Path -LiteralPath $result.Report)){throw 'Report was not created.'}
if(-not(Test-Path -LiteralPath $result.Audit)){throw 'Audit record was not created.'}
if(-not(Test-Path -LiteralPath $result.HashManifest)){throw 'Hash manifest was not created.'}
if(-not(Test-Path -LiteralPath $result.FeatureSnapshot)){throw 'Feature snapshot was not created.'}
if(-not(Test-Path -LiteralPath $result.RankingSnapshot)){throw 'Ranking snapshot was not created.'}
if([string]::IsNullOrWhiteSpace($result.DeterministicDigest)){throw 'Deterministic digest was not returned.'}
if(-not(Test-Path -LiteralPath $result.Learning)){throw 'Learning record was not created.'}
$reportText=Get-Content -Raw -Encoding UTF8 -LiteralPath $result.Report
if($reportText -notmatch 'بحث آموزشی اجباری این اجرا'){throw 'Mandatory educational discussion is missing from report.'}
if($reportText -notmatch 'وضعیت ارتقای دانش'){throw 'Educational discussion status is missing from report.'}
if($reportText -notmatch 'اجزای امتیاز و جریمه ریسک'){throw 'V3 score-components table is missing from report.'}
if($reportText -notmatch 'کیفیت داده رتبه‌های برتر'){throw 'V3 data-quality table is missing from report.'}
$requiredV3Header='| رتبه | نماد | اعمال | آخرین | سر به سری | پایه | اهرم | فاصله سر به سری | سررسید | باقی مانده روز | امتیاز |'
if($reportText -notmatch [regex]::Escape($requiredV3Header)){throw 'The mandatory 11-column V3 header is missing or changed.'}
for($i=1;$i-lt$result.Top.Count;$i++){
    if($result.Top[$i-1].FinalScore-lt$result.Top[$i].FinalScore){throw 'Ranking is not descending.'}
}
foreach($x in $result.Top){
    $expected=if($x.Type-eq'Put'){$x.Strike-$x.Last}else{$x.Strike+$x.Last}
    if([Math]::Abs($expected-$x.Breakeven)-gt0.000001){throw "Breakeven mismatch: $($x.Symbol)"}
    if($x.BlockMarket-lt0-or$x.BlockMarket-gt10){throw "Market block is out of bounds: $($x.Symbol)"}
    $statusFactor=$x.FactorBreakdown|Where-Object{$_.Factor-eq'Status'}|Select-Object -First 1
    if($null-eq$statusFactor-or-not$statusFactor.Missing){throw "Status must remain Missing until mapping is approved: $($x.Symbol)"}
}
[pscustomobject]@{
    Status='PASS';RunId=$result.RunId;TopCount=$result.Top.Count;Report=$result.Report
    Audit=$result.Audit;HashManifest=$result.HashManifest;Digest=$result.DeterministicDigest
    RiskAlignment=$result.RiskAlignmentStatus
}|Format-List
