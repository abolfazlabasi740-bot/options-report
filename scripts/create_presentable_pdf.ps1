param(
    [Parameter(Mandatory=$true)][string]$MarkdownPath,
    [string]$PdfPath
)
$ErrorActionPreference='Stop'
if([string]::IsNullOrWhiteSpace($PdfPath)){$PdfPath=[IO.Path]::ChangeExtension($MarkdownPath,'_rtl_bnazanin.pdf')}
$lines=Get-Content -LiteralPath $MarkdownPath -Raw -Encoding UTF8
$html='<html><head><meta charset="utf-8"><style>@page{size:A4;margin:1.3cm}body{font-family:"B Nazanin","BNazanin",Tahoma;direction:rtl;unicode-bidi:embed;text-align:right;font-size:12pt;line-height:1.35;color:#111}h1,h2,h3{font-family:"B Nazanin";color:#17365d;page-break-after:avoid}table{border-collapse:collapse;width:100%;direction:rtl;margin:8px 0;page-break-inside:auto}tr{page-break-inside:avoid}th,td{border:1px solid #6f7f8f;padding:5px;text-align:right;vertical-align:middle}th{background:#d9eaf7;font-weight:bold}p{margin:5px 0}code{font-family:"B Nazanin"}</style></head><body>'
$inTable=$false
foreach($line in ($lines -split "`r?`n")){
    $t=$line.Trim()
    if([string]::IsNullOrWhiteSpace($t)){continue}
    if($t -match '^\|(.+)\|$'){
        $cells=@($t.Trim('|').Split('|')|ForEach-Object{$_.Trim()})
        if($cells -match '^:?-+:?$'){continue}
        if(-not $inTable){$html+='<table>'; $inTable=$true; $tag='th'}else{$tag='td'}
        $html+='<tr>'
        foreach($c in $cells){$c=$c -replace '\*\*','' -replace '`','';$html+="<$tag>$([System.Net.WebUtility]::HtmlEncode($c))</$tag>"}
        $html+='</tr>'; continue
    } elseif($inTable){$html+='</table>'; $inTable=$false}
    if($t -match '^###\s+(.+)'){$html+="<h3>$([System.Net.WebUtility]::HtmlEncode($Matches[1]))</h3>";continue}
    if($t -match '^##\s+(.+)'){$html+="<h2>$([System.Net.WebUtility]::HtmlEncode($Matches[1]))</h2>";continue}
    if($t -match '^#\s+(.+)'){$html+="<h1>$([System.Net.WebUtility]::HtmlEncode($Matches[1]))</h1>";continue}
    $plain=$t -replace '\*\*','' -replace '`',''
    $html+="<p>$([System.Net.WebUtility]::HtmlEncode($plain))</p>"
}
if($inTable){$html+='</table>'};$html+='</body></html>'
$htmlPath=[IO.Path]::ChangeExtension($MarkdownPath,'.presentable.html')
Set-Content -LiteralPath $htmlPath -Value $html -Encoding UTF8
$word=$null;$doc=$null
try{
    $word=New-Object -ComObject Word.Application
    $word.Visible=$false
    $doc=$word.Documents.Open($htmlPath,$false,$true)
    $doc.ExportAsFixedFormat($PdfPath,17)
} finally {
    if($doc){$doc.Close($false)}
    if($word){$word.Quit()}
    if(Test-Path -LiteralPath $htmlPath){Remove-Item -LiteralPath $htmlPath -Force}
}
Write-Output $PdfPath
