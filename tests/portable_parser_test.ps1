param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$CompareWithExcelCom
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
Import-Module -Force (Join-Path $ProjectRoot 'engines/common/CommonEngine.psm1')
Import-Module -Force (Join-Path $ProjectRoot 'engines/parsing/ParsingEngine.psm1')

$config = Read-ProjectConfig (Join-Path $ProjectRoot 'configs/project.json')
$workbook = Get-ChildItem -LiteralPath (Join-Path $ProjectRoot 'data/raw') `
    -File -Filter 'optionschool24_all_*.xlsx' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $workbook) { throw 'No Optionschool workbook was found.' }

$openXml = Read-OptionsWorkbookWithOpenXml -ResolvedPath $workbook.FullName -Config $config
if ($openXml.Headers.Count -ne 38) { throw "Expected 38 headers, got $($openXml.Headers.Count)." }
if ($openXml.SourceRows -le 0) { throw 'OpenXML parser returned no rows.' }
foreach ($row in @($openXml.Rows | Select-Object -First 3)) {
    if ([string]::IsNullOrWhiteSpace([string]$row.C1)) {
        throw "OpenXML parser returned an empty symbol at source row $($row.SourceRow)."
    }
}

if ($CompareWithExcelCom) {
    $com = Read-OptionsWorkbook -WorkbookPath $workbook.FullName -Config $config
    if ($com.SourceRows -ne $openXml.SourceRows) {
        throw "Parser row-count mismatch: COM=$($com.SourceRows), OpenXML=$($openXml.SourceRows)."
    }
    for ($rowIndex = 0; $rowIndex -lt $com.Rows.Count; $rowIndex++) {
        for ($column = 1; $column -le 38; $column++) {
            $propertyName = "C$column"
            $left = [string]$com.Rows[$rowIndex].PSObject.Properties[$propertyName].Value
            $right = [string]$openXml.Rows[$rowIndex].PSObject.Properties[$propertyName].Value
            if ($left -cne $right) {
                throw "Parser value mismatch at source row $($rowIndex + 2), column $column."
            }
        }
    }
}

[pscustomobject]@{
    Status = 'PASS'
    Parser = $openXml.Parser
    Workbook = $workbook.Name
    Headers = $openXml.Headers.Count
    Rows = $openXml.SourceRows
    ComparedWithExcelCom = [bool]$CompareWithExcelCom
} | Format-List
