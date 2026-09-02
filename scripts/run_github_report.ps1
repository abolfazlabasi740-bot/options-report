param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [double]$MinLeverage = 3.0,
    [string]$InputWorkbook
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$pipeline = Join-Path $PSScriptRoot 'run_pipeline.ps1'

Write-Host "Starting governed Optionschool report (V4 Candidate, leverage >= $MinLeverage)..."
$pipelineArguments = @{
    ProjectRoot = $ProjectRoot
    V4Candidate = $true
    MinLeverage = $MinLeverage
    Quiet = $true
}
if (-not [string]::IsNullOrWhiteSpace($InputWorkbook)) {
    $pipelineArguments.InputWorkbook = $InputWorkbook
} else {
    $pipelineArguments.Download = $true
}
$items = @(& $pipeline @pipelineArguments)

# A few PowerShell versions can emit informational values from imported
# modules. Select the actual result object by its Status property.
$result = $items |
    Where-Object { $null -ne $_.PSObject.Properties['Status'] } |
    Select-Object -Last 1

if ($null -eq $result) {
    throw 'The pipeline returned no result object.'
}
if ([string]$result.Status -ne 'COMPLETED') {
    throw "The pipeline did not complete: $($result.Status)"
}
if (-not (Test-Path -LiteralPath $result.Report -PathType Leaf)) {
    throw "Markdown report was not created: $($result.Report)"
}
$reportText = Get-Content -Raw -Encoding UTF8 -LiteralPath $result.Report
$requiredHeader = '| رتبه | نماد | اعمال | آخرین | سر به سری | پایه | اهرم | فاصله سر به سری | سررسید | باقی مانده روز | امتیاز |'
if ($reportText -notmatch [regex]::Escape($requiredHeader)) {
    throw 'The mandatory 11-column V3 table header is missing from the report.'
}
foreach ($requiredSection in @('بحث آموزشی اجباری این اجرا', 'یادگیری هفت‌روزه و جهش‌های شارپ')) {
    if ($reportText -notmatch [regex]::Escape($requiredSection)) {
        throw "Required report section is missing: $requiredSection"
    }
}

$top = @($result.Top)
if ($top.Count -eq 0) {
    throw 'The V4 candidate filter returned no contracts.'
}
foreach ($contract in $top) {
    if ($null -eq $contract.Leverage -or [double]$contract.Leverage -lt $MinLeverage) {
        throw "V4 leverage gate violation for $($contract.Symbol)."
    }
}
$learningPathCandidate = [string]$result.Learning
if (Test-Path -LiteralPath $learningPathCandidate -PathType Leaf) {
    $learningText = Get-Content -Raw -Encoding UTF8 -LiteralPath $learningPathCandidate
    if ($learningText -match '"MinimumLeverage"\s*:\s*([0-9.]+)') {
        $learningMinimum = [double]$Matches[1]
        if ([Math]::Abs($learningMinimum - $MinLeverage) -gt 0.000001) {
            throw "Learning leverage gate mismatch: expected $MinLeverage, got $learningMinimum."
        }
    }
}

$reportPath = (Resolve-Path -LiteralPath $result.Report).Path
$reportDirectory = Split-Path -Parent $reportPath
$pdfPath = Join-Path $reportDirectory (
    [IO.Path]::GetFileNameWithoutExtension($reportPath) + '.rtl_bnazanin.pdf'
)

$outputValues = [ordered]@{
    run_id = [string]$result.RunId
    report_path = $reportPath
    pdf_path = $pdfPath
    workbook_path = [string]$result.Workbook
    audit_path = [string]$result.Audit
    learning_path = [string]$result.Learning
    ranking_snapshot_path = [string]$result.RankingSnapshot
    feature_snapshot_path = [string]$result.FeatureSnapshot
    hash_manifest_path = [string]$result.HashManifest
    top_count = [string]$top.Count
    deterministic_digest = [string]$result.DeterministicDigest
}

if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_OUTPUT)) {
    $utf8NoBom = [Text.UTF8Encoding]::new($false)
    foreach ($pair in $outputValues.GetEnumerator()) {
        [IO.File]::AppendAllText(
            $env:GITHUB_OUTPUT,
            "$($pair.Key)=$($pair.Value)`n",
            $utf8NoBom
        )
    }
}

if (-not [string]::IsNullOrWhiteSpace($env:GITHUB_STEP_SUMMARY)) {
    $summary = @(
        "## Optionschool V4 Candidate"
        ""
        "- Run ID: ``$($result.RunId)``"
        "- Workbook: ``$([IO.Path]::GetFileName([string]$result.Workbook))``"
        "- Valid contracts: $($result.Top.Count) in the leverage-gated top list"
        "- Minimum leverage: $($MinLeverage.ToString('0.00',[Globalization.CultureInfo]::InvariantCulture))"
        "- Deterministic digest: ``$($result.DeterministicDigest)``"
        "- Markdown: ``$reportPath``"
    )
    [IO.File]::WriteAllLines(
        $env:GITHUB_STEP_SUMMARY,
        $summary,
        [Text.UTF8Encoding]::new($false)
    )
}

[pscustomobject]$outputValues | Format-List
