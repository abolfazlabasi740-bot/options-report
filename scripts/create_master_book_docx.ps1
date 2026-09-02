param(
    [string]$MarkdownPath = (Join-Path (Split-Path -Parent $PSScriptRoot) '..\MASTER_PROJECT_BOOK_OPTIONS_V3_V4_FA.md'),
    [string]$DocxPath = (Join-Path (Split-Path -Parent $PSScriptRoot) '..\MASTER_PROJECT_BOOK_OPTIONS_V3_V4_FA.docx')
)
$ErrorActionPreference='Stop'
$md=Get-Content -LiteralPath (Resolve-Path $MarkdownPath) -Raw -Encoding UTF8
$html='<html><head><meta charset="utf-8"><style>@page{size:A4;margin:1.5cm}body{font-family:"B Nazanin","BNazanin",Tahoma;direction:rtl;unicode-bidi:embed;text-align:right;font-size:12pt;line-height:1.35}h1{font-size:21pt;color:#17365d}h2{font-size:17pt;color:#1f4e79;border-bottom:1px solid #9fbad0}h3{font-size:14pt;color:#1f4e79}table{border-collapse:collapse;width:100%;direction:rtl;margin:8px 0;page-break-inside:auto}tr{page-break-inside:avoid}th,td{border:1px solid #718096;padding:5px;text-align:right;vertical-align:middle}th{background:#d9eaf7;font-weight:bold}code{font-family:"B Nazanin"}p{margin:5px 0}li{margin:3px}</style></head><body>'
$inTable=$false;$listOpen=$false
foreach($line in ($md -split "`r?`n")){
    $t=$line.Trim()
    if([string]::IsNullOrWhiteSpace($t)){continue}
    if($t -match '^\|(.+)\|$'){
        if($listOpen){$html+='</ul>'; $listOpen=$false}
        $cells=@($t.Trim('|').Split('|')|ForEach-Object{$_.Trim()})
        if($cells -match '^:?-+:?$'){continue}
        if(-not $inTable){$html+='<table>'; $inTable=$true; $tag='th'}else{$tag='td'}
        $html+='<tr>'; foreach($c in $cells){$c=$c -replace '\*\*','' -replace '`','';$html+="<$tag>$([System.Net.WebUtility]::HtmlEncode($c))</$tag>"}; $html+='</tr>'; continue
    } elseif($inTable){$html+='</table>'; $inTable=$false}
    if($t -match '^\-\s+(.+)'){if(-not $listOpen){$html+='<ul>'; $listOpen=$true};$html+="<li>$([System.Net.WebUtility]::HtmlEncode(($Matches[1] -replace '\*\*','' -replace '`','')))</li>";continue}
    if($listOpen){$html+='</ul>'; $listOpen=$false}
    if($t -match '^###\s+(.+)'){$html+="<h3>$([System.Net.WebUtility]::HtmlEncode($Matches[1]))</h3>";continue}
    if($t -match '^##\s+(.+)'){$html+="<h2>$([System.Net.WebUtility]::HtmlEncode($Matches[1]))</h2>";continue}
    if($t -match '^#\s+(.+)'){$html+="<h1>$([System.Net.WebUtility]::HtmlEncode($Matches[1]))</h1>";continue}
    $plain=$t -replace '\*\*','' -replace '`',''
    $html+="<p>$([System.Net.WebUtility]::HtmlEncode($plain))</p>"
}
if($inTable){$html+='</table>'};if($listOpen){$html+='</ul>'};$html+='</body></html>'
$htmlPath=[IO.Path]::ChangeExtension((Resolve-Path $MarkdownPath),'.masterbook.html')
Set-Content -LiteralPath $htmlPath -Value $html -Encoding UTF8
$word=$null;$doc=$null
try{$word=New-Object -ComObject Word.Application;$word.Visible=$false;$doc=$word.Documents.Open($htmlPath,$false,$true);$doc.SaveAs2((Resolve-Path (Split-Path $DocxPath -Parent)).Path+'\'+(Split-Path $DocxPath -Leaf),16);$doc.Close($false)}
finally{if($word){$word.Quit()};if(Test-Path $htmlPath){Remove-Item $htmlPath -Force}}
Write-Output (Resolve-Path $DocxPath)
