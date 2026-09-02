Set-StrictMode -Version Latest

function Test-XlsxFile {
    param([Parameter(Mandatory=$true)][string]$Path, [int64]$MinimumBytes=5000)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    $file = Get-Item -LiteralPath $Path
    if ($file.Length -lt $MinimumBytes) { return $false }
    $stream = [IO.File]::OpenRead($file.FullName)
    try {
        return ($stream.ReadByte() -eq 0x50 -and $stream.ReadByte() -eq 0x4B)
    } finally {
        $stream.Dispose()
    }
}

function Get-LatestOptionWorkbook {
    param([Parameter(Mandatory=$true)][string]$Directory, [Parameter(Mandatory=$true)][string]$Pattern)
    return Get-ChildItem -LiteralPath $Directory -File -Filter $Pattern |
        Where-Object { $_.Name -notlike '~$*' } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

function Receive-OptionschoolWorkbook {
    param(
        [Parameter(Mandatory=$true)][string]$Endpoint,
        [Parameter(Mandatory=$true)][string]$DestinationDirectory,
        [int64]$MinimumBytes=5000
    )
    New-Item -ItemType Directory -Force -Path $DestinationDirectory | Out-Null
    $temporary = Join-Path $DestinationDirectory ('.download_' + [guid]::NewGuid().ToString('N') + '.tmp')
    $httpClient = $null
    $response = $null
    $responseStream = $null
    $fileStream = $null
    try {
        # HttpClient is more reliable than Invoke-WebRequest for PowerShell 7
        # on GitHub's Ubuntu runner and still lets us validate the server
        # supplied filename before moving the workbook into the archive.
        $httpClient = [System.Net.Http.HttpClient]::new()
        $httpClient.Timeout = [TimeSpan]::FromSeconds(90)
        $httpClient.DefaultRequestHeaders.UserAgent.ParseAdd('OptionschoolV4-GitHub/1.0')
        $response = $httpClient.GetAsync($Endpoint, [System.Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
        $response.EnsureSuccessStatusCode()
        $responseStream = $response.Content.ReadAsStreamAsync().GetAwaiter().GetResult()
        $fileStream = [IO.File]::Open($temporary, [IO.FileMode]::Create, [IO.FileAccess]::Write, [IO.FileShare]::None)
        $responseStream.CopyTo($fileStream)
        $fileStream.Flush()
        $fileStream.Dispose()
        $fileStream = $null
        if (-not (Test-Path -LiteralPath $temporary -PathType Leaf)) {
            throw 'Optionschool download completed without creating the temporary file.'
        }
        if (-not (Test-XlsxFile -Path $temporary -MinimumBytes $MinimumBytes)) {
            throw 'Optionschool response is not a complete XLSX file.'
        }
        $disposition = [string]$response.Content.Headers.ContentDisposition
        $name = $null
        if ($disposition -match "filename\*=UTF-8''([^;]+)") { $name = [uri]::UnescapeDataString($Matches[1].Trim('"')) }
        elseif ($disposition -match 'filename="?([^";]+)"?') { $name = $Matches[1] }
        if ([string]::IsNullOrWhiteSpace($name)) {
            throw 'Content-Disposition did not provide a verified filename.'
        }
        $name = [IO.Path]::GetFileName($name)
        if ($name -notlike 'optionschool24_all_*.xlsx') { throw "Unexpected Optionschool filename: $name" }
        $target = Join-Path $DestinationDirectory $name
        if (Test-Path -LiteralPath $target) {
            Remove-Item -LiteralPath $temporary -Force
            return [pscustomobject]@{ Path=$target; FileName=$name; IsNew=$false; Status='AlreadyExists' }
        }
        Move-Item -LiteralPath $temporary -Destination $target
        return [pscustomobject]@{ Path=$target; FileName=$name; IsNew=$true; Status='Downloaded' }
    } catch {
        if (Test-Path -LiteralPath $temporary) { Remove-Item -LiteralPath $temporary -Force }
        throw
    } finally {
        if ($fileStream) { $fileStream.Dispose() }
        if ($responseStream) { $responseStream.Dispose() }
        if ($response) { $response.Dispose() }
        if ($httpClient) { $httpClient.Dispose() }
    }
}

Export-ModuleMember -Function *
