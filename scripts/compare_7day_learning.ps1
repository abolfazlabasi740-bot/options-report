param([string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot),[int]$TopN=50)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Read-Text($zip,$name) {
    $e=$zip.GetEntry($name); if(!$e){return $null}
    $r=[IO.StreamReader]::new($e.Open()); try{$r.ReadToEnd()}finally{$r.Dispose()}
}
function Col([string]$ref) {
    $n=0; foreach($c in ($ref -replace '\d','').ToCharArray()){$n=$n*26+([int][char]$c-64)}; $n-1
}
function Num($x) {
    if($null -eq $x -or [string]::IsNullOrWhiteSpace([string]$x)){return $null}
    $s=([string]$x).Trim().Replace(',','')
    if($s.EndsWith('M')){return [double]$s.TrimEnd('M')*1e6}
    if($s.EndsWith('B')){return [double]$s.TrimEnd('B')*1e9}
    try{[double]$s}catch{$null}
}
function Read-Workbook($path) {
    $zip=[IO.Compression.ZipFile]::OpenRead($path)
    try {
        [xml]$sheet=Read-Text $zip 'xl/worksheets/sheet1.xml'
        $ns=[Xml.XmlNamespaceManager]::new($sheet.NameTable)
        $ns.AddNamespace('m','http://schemas.openxmlformats.org/spreadsheetml/2006/main')
        $shared=@(); $sharedText=Read-Text $zip 'xl/sharedStrings.xml'
        if($sharedText){[xml]$sx=$sharedText;$sn=[Xml.XmlNamespaceManager]::new($sx.NameTable);$sn.AddNamespace('m','http://schemas.openxmlformats.org/spreadsheetml/2006/main');$shared=@($sx.SelectNodes('//m:si',$sn)|%{$_.InnerText})}
        $out=@()
        $rows=$sheet.SelectNodes('//m:sheetData/m:row',$ns)
        for($i=1;$i -lt $rows.Count;$i++){
            $v=New-Object object[] 38
            foreach($cell in $rows[$i].SelectNodes('m:c',$ns)){
                $vn=$cell.SelectSingleNode('m:v',$ns);$x=if($vn){$vn.InnerText}else{''}
                if($cell.t -eq 's' -and $x -ne ''){$x=$shared[[int]$x]}
                if($cell.t -eq 'inlineStr'){$tn=$cell.SelectSingleNode('m:is/m:t',$ns);if($tn){$x=$tn.InnerText}}
                $v[(Col $cell.r)]=$x
            }
            $out += [pscustomobject]@{
                Symbol=([string]$v[0]).Trim(); Strike=Num $v[1]; Underlying=Num $v[2]; Expiration=$v[4]
                CalendarDays=Num $v[5]; OI=[string]$v[7]; Volume=Num $v[8]; TradeValue=Num $v[9]
                Last=Num $v[10]; Close=Num $v[12]; BSDiff=Num $v[19]; Status=[string]$v[20]
                IV=Num $v[22]; HV=Num $v[23]; Spread=Num $v[31]
            }
        }
        return $out
    } finally {$zip.Dispose()}
}

$root=(Resolve-Path $ProjectRoot).Path
$files=Get-ChildItem -File -Recurse -Path (Split-Path $root -Parent) -Include *.xlsx,*.xlsm |
    Where-Object {$_.LastWriteTime.Date -ge [datetime]'2026-08-17' -and $_.LastWriteTime.Date -le [datetime]'2026-08-25'} |
    Group-Object {$_.LastWriteTime.ToString('yyyy-MM-dd')} |
    ForEach-Object {$_.Group|Sort-Object LastWriteTime -Descending|Select-Object -First 1}
$snap=[ordered]@{}
foreach($f in ($files|Sort-Object LastWriteTime)){
    $d=$f.LastWriteTime.ToString('yyyy-MM-dd');$m=@{}
    foreach($r in (Read-Workbook $f.FullName)){if($r.Symbol){$m[$r.Symbol]=$r}}
    $snap[$d]=[pscustomobject]@{Path=$f.FullName;Rows=$m}
}
$dates=@($snap.Keys);$daily=@()
for($i=1;$i -lt $dates.Count;$i++){
    $a=$snap[$dates[$i-1]].Rows;$b=$snap[$dates[$i]].Rows
    foreach($s in $b.Keys){if(!$a.ContainsKey($s)){continue};$p=$a[$s];$c=$b[$s];if($p.Last-le0-or$c.Last-le0){continue}
        $daily += [pscustomobject]@{From=$dates[$i-1];To=$dates[$i];Symbol=$s;PrevLast=$p.Last;Last=$c.Last;ReturnPct=(($c.Last/$p.Last)-1)*100;UnderlyingPrev=$p.Underlying;UnderlyingLast=$c.Underlying;Volume=$c.Volume;TradeValue=$c.TradeValue;Spread=$c.Spread;BSDiff=$c.BSDiff;Expiration=$c.Expiration;Status=$c.Status}
    }
}
$first=$snap[$dates[0]].Rows;$last=$snap[$dates[$dates.Count-1]].Rows;$cum=@()
foreach($s in $last.Keys){if(!$first.ContainsKey($s)){continue};$p=$first[$s];$c=$last[$s];if($p.Last-le0-or$c.Last-le0){continue}
    $cum += [pscustomobject]@{Symbol=$s;FirstLast=$p.Last;Last=$c.Last;ReturnPct=(($c.Last/$p.Last)-1)*100;UnderlyingFirst=$p.Underlying;UnderlyingLast=$c.Underlying;Volume=$c.Volume;TradeValue=$c.TradeValue;Spread=$c.Spread;BSDiff=$c.BSDiff;Expiration=$c.Expiration;Status=$c.Status}
}
$report=[ordered]@{Protocol='PROTOCOL_OPTIONS_RANKING_V3';WindowStart=$dates[0];WindowEnd=$dates[$dates.Count-1];SnapshotFiles=@($dates|%{[pscustomobject]@{Date=$_;Path=$snap[$_].Path}});DailyTop=@($daily|Where-Object {$_.ReturnPct -ge 20}|Sort-Object ReturnPct -Descending|Select-Object -First $TopN);CumulativeTop=@($cum|Where-Object {$_.ReturnPct -ge 50}|Sort-Object ReturnPct -Descending|Select-Object -First $TopN);DailyAll=@($daily|Sort-Object To,ReturnPct -Descending)}
$out=Join-Path $root ("reports\7day_learning_{0}_{1}.json" -f (($dates[0])-replace '-',''),(($dates[$dates.Count-1])-replace '-',''))
$report|ConvertTo-Json -Depth 6|Set-Content -Encoding UTF8 -LiteralPath $out
$report|ConvertTo-Json -Depth 6
