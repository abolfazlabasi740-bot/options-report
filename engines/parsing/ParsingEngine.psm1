Set-StrictMode -Version Latest

function Convert-ExcelColumnNumber {
    param([Parameter(Mandatory=$true)][string]$Reference)
    $letters = ([regex]::Match($Reference, '^[A-Za-z]+')).Value.ToUpperInvariant()
    if ([string]::IsNullOrWhiteSpace($letters)) { return $null }
    $number = 0
    foreach ($character in $letters.ToCharArray()) {
        $number = ($number * 26) + ([int][char]$character - [int][char]'A' + 1)
    }
    return $number
}

function Get-ZipEntryText {
    param(
        [Parameter(Mandatory=$true)][object]$Zip,
        [Parameter(Mandatory=$true)][string]$Name
    )
    $entry = $Zip.GetEntry($Name)
    if ($null -eq $entry) { throw "XLSX entry was not found: $Name" }
    $stream = $null
    $reader = $null
    try {
        $stream = $entry.Open()
        $reader = [IO.StreamReader]::new($stream, [Text.Encoding]::UTF8, $true)
        return $reader.ReadToEnd()
    } finally {
        if ($reader) { $reader.Dispose() }
        elseif ($stream) { $stream.Dispose() }
    }
}

function Get-OpenXmlCellValue {
    param(
        [Parameter(Mandatory=$true)][object]$Cell,
        [Parameter(Mandatory=$true)][object[]]$SharedStrings
    )
    $type = [string]$Cell.GetAttribute('t')
    $valueNode = $Cell.SelectSingleNode('./*[local-name()="v"]')
    $raw = if ($null -ne $valueNode) { [string]$valueNode.InnerText } else { $null }
    switch ($type) {
        's' {
            $index = 0
            if ([int]::TryParse($raw, [ref]$index) -and $index -ge 0 -and $index -lt $SharedStrings.Count) {
                return [string]$SharedStrings[$index]
            }
            return $null
        }
        'inlineStr' {
            $textNodes = @($Cell.SelectNodes('.//*[local-name()="t"]'))
            return (($textNodes | ForEach-Object { [string]$_.InnerText }) -join '')
        }
        'str' { return $raw }
        'b' {
            if ($raw -eq '1') { return 'TRUE' }
            return 'FALSE'
        }
        default { return $raw }
    }
}

function Read-OptionsWorkbookWithOpenXml {
    param(
        [Parameter(Mandatory=$true)][string]$ResolvedPath,
        [Parameter(Mandatory=$true)][object]$Config
    )
    try { Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop } catch {}
    $zip = $null
    try {
        $zip = [System.IO.Compression.ZipFile]::OpenRead($ResolvedPath)
        $sharedStrings = @()
        $sharedEntry = $zip.GetEntry('xl/sharedStrings.xml')
        if ($null -ne $sharedEntry) {
            $sharedXml = [xml](Get-ZipEntryText -Zip $zip -Name 'xl/sharedStrings.xml')
            $sharedStrings = @(
                $sharedXml.SelectNodes('//*[local-name()="sst"]/*[local-name()="si"]') |
                    ForEach-Object {
                        $textNodes = @($_.SelectNodes('.//*[local-name()="t"]'))
                        (($textNodes | ForEach-Object { [string]$_.InnerText }) -join '')
                    }
            )
        }
        $sheetEntry = $zip.GetEntry('xl/worksheets/sheet1.xml')
        if ($null -eq $sheetEntry) {
            $sheetEntry = @($zip.Entries | Where-Object {
                $_.FullName -match '^xl/worksheets/[^/]+\.xml$'
            } | Select-Object -First 1)
        }
        if ($null -eq $sheetEntry -or @($sheetEntry).Count -eq 0) {
            throw 'The first worksheet XML was not found in the XLSX archive.'
        }
        if ($sheetEntry -is [array]) { $sheetEntry = $sheetEntry[0] }
        $sheetXml = [xml](Get-ZipEntryText -Zip $zip -Name ([string]$sheetEntry.FullName))
        $rowNodes = @($sheetXml.SelectNodes('//*[local-name()="sheetData"]/*[local-name()="row"]'))
        if ($rowNodes.Count -eq 0) { throw 'Optionschool workbook contains no worksheet rows.' }

        $headerCells = @($rowNodes[0].SelectNodes('./*[local-name()="c"]'))
        $maxColumn = 0
        foreach ($cell in $headerCells) {
            $column = Convert-ExcelColumnNumber -Reference ([string]$cell.GetAttribute('r'))
            if ($null -ne $column) { $maxColumn = [Math]::Max($maxColumn, [int]$column) }
        }
        $headers = [Array]::CreateInstance([object], $maxColumn)
        foreach ($cell in $headerCells) {
            $column = Convert-ExcelColumnNumber -Reference ([string]$cell.GetAttribute('r'))
            if ($null -ne $column -and $column -gt 0) {
                $headers[$column - 1] = [string](Get-OpenXmlCellValue -Cell $cell -SharedStrings $sharedStrings)
            }
        }
        $headers = @($headers | ForEach-Object { ([string]$_).Trim() })
        $expected = @($Config.expected_headers | ForEach-Object { ([string]$_).Trim() })
        if ($headers.Count -ne $expected.Count) {
            throw 'Optionschool schema differs from the approved 38-column schema.'
        }
        for ($i = 0; $i -lt $expected.Count; $i++) {
            if ($headers[$i] -ne $expected[$i]) {
                throw 'Optionschool schema differs from the approved 38-column schema.'
            }
        }

        $rows = [Collections.Generic.List[object]]::new()
        $sequence = 2
        foreach ($rowNode in ($rowNodes | Select-Object -Skip 1)) {
            $record = [ordered]@{ SourceRow = $sequence }
            $cells = @($rowNode.SelectNodes('./*[local-name()="c"]'))
            foreach ($cell in $cells) {
                $column = Convert-ExcelColumnNumber -Reference ([string]$cell.GetAttribute('r'))
                if ($null -ne $column -and $column -le $expected.Count) {
                    $record["C$column"] = Get-OpenXmlCellValue -Cell $cell -SharedStrings $sharedStrings
                }
            }
            for ($column = 1; $column -le $expected.Count; $column++) {
                if (-not $record.Contains("C$column")) { $record["C$column"] = $null }
            }
            $rows.Add([pscustomobject]$record)
            $sequence++
        }
        return [pscustomobject]@{
            WorkbookPath=$ResolvedPath; SheetName='Sheet1'; Headers=$headers
            SourceRows=$rows.Count; Rows=$rows; SchemaChanged=$false; Parser='OpenXML'
        }
    } finally {
        if ($zip) { $zip.Dispose() }
    }
}

function Read-OptionsWorkbookWithImportExcel {
    param(
        [Parameter(Mandatory=$true)][string]$ResolvedPath,
        [Parameter(Mandatory=$true)][object]$Config
    )
    if (-not (Get-Command Import-Excel -ErrorAction SilentlyContinue)) {
        try { Import-Module ImportExcel -ErrorAction Stop }
        catch { throw 'Excel COM is unavailable and the ImportExcel PowerShell module is not installed.' }
    }
    $rowsFromExcel = @(Import-Excel -Path $ResolvedPath -ErrorAction Stop)
    if ($rowsFromExcel.Count -eq 0) { throw 'Optionschool workbook contains no data rows.' }
    $headers = @($rowsFromExcel[0].PSObject.Properties | ForEach-Object { ([string]$_.Name).Trim() })
    $expected = @($Config.expected_headers | ForEach-Object { ([string]$_).Trim() })
    if ($headers.Count -ne $expected.Count) { throw 'Optionschool schema differs from the approved 38-column schema.' }
    for ($i=0; $i -lt $expected.Count; $i++) {
        if ($headers[$i] -ne $expected[$i]) { throw 'Optionschool schema differs from the approved 38-column schema.' }
    }
    $rows = [Collections.Generic.List[object]]::new()
    $sourceRow = 2
    foreach ($source in $rowsFromExcel) {
        $record = [ordered]@{ SourceRow = $sourceRow }
        for ($column=1; $column -le $headers.Count; $column++) {
            $property = $source.PSObject.Properties[$headers[$column-1]]
            $record["C$column"] = if ($null -ne $property) { $property.Value } else { $null }
        }
        $rows.Add([pscustomobject]$record)
        $sourceRow++
    }
    return [pscustomobject]@{
        WorkbookPath=$ResolvedPath; SheetName='Sheet1'; Headers=$headers
        SourceRows=$rows.Count; Rows=$rows; SchemaChanged=$false; Parser='ImportExcel'
    }
}

function Read-OptionsWorkbook {
    param(
        [Parameter(Mandatory=$true)][string]$WorkbookPath,
        [Parameter(Mandatory=$true)][object]$Config
    )
    $resolved = (Resolve-Path -LiteralPath $WorkbookPath).Path
    $excel=$null; $workbook=$null; $worksheet=$null; $used=$null
    try {
        if ($env:OPTIONS_FORCE_OPENXML -eq '1') {
            return Read-OptionsWorkbookWithOpenXml -ResolvedPath $resolved -Config $Config
        }
        try {
            $excel = New-Object -ComObject Excel.Application -ErrorAction Stop
        } catch {
            try {
                return Read-OptionsWorkbookWithOpenXml -ResolvedPath $resolved -Config $Config
            } catch {
                return Read-OptionsWorkbookWithImportExcel -ResolvedPath $resolved -Config $Config
            }
        }
        $excel.Visible = $false
        $excel.DisplayAlerts = $false
        $excel.ScreenUpdating = $false
        $workbook = $excel.Workbooks.Open($resolved, 0, $true)
        $worksheet = $workbook.Worksheets.Item(1)
        $used = $worksheet.UsedRange
        $values = $used.Value2
        $headers = @()
        for ($column=1; $column -le $used.Columns.Count; $column++) {
            $headers += ([string]$values[1,$column]).Trim()
        }
        $expected = @($Config.expected_headers)
        $schemaChanged = ($headers.Count -ne $expected.Count)
        if (-not $schemaChanged) {
            for ($i=0; $i -lt $expected.Count; $i++) {
                if ($headers[$i] -ne [string]$expected[$i]) { $schemaChanged=$true; break }
            }
        }
        if ($schemaChanged) { throw 'Optionschool schema differs from the approved 38-column schema.' }
        $rows = [Collections.Generic.List[object]]::new()
        for ($row=2; $row -le $used.Rows.Count; $row++) {
            $record = [ordered]@{ SourceRow=$row }
            for ($column=1; $column -le $headers.Count; $column++) {
                $record["C$column"] = $values[$row,$column]
            }
            $rows.Add([pscustomobject]$record)
        }
        return [pscustomobject]@{
            WorkbookPath=$resolved
            SheetName=$worksheet.Name
            Headers=$headers
            SourceRows=$rows.Count
            Rows=$rows
            SchemaChanged=$false
            Parser='ExcelCOM'
        }
    } finally {
        if ($workbook) { $workbook.Close($false) }
        if ($excel) { $excel.Quit() }
        foreach ($item in @($used,$worksheet,$workbook,$excel)) {
            if ($item) { try {[void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($item)} catch {} }
        }
        [GC]::Collect()
        [GC]::WaitForPendingFinalizers()
    }
}

Export-ModuleMember -Function *
