param([string]$ProjectRoot=(Split-Path -Parent $PSScriptRoot))

$ErrorActionPreference='Stop'
$ProjectRoot=(Resolve-Path -LiteralPath $ProjectRoot).Path
Import-Module -Force (Join-Path $ProjectRoot 'engines/common/CommonEngine.psm1')

$configPath=Join-Path $ProjectRoot 'configs/project.json'
$config=Read-ProjectConfig $configPath
$validation=Assert-ProjectConfig -Config $config -ProjectRoot $ProjectRoot

if($validation.Status-ne'PASS'){throw 'Master governance validation failed.'}
if($config.master_project_book.baseline-ne'V3'){throw 'V3 must be the executable baseline.'}
if($config.master_project_book.candidate-ne'V4'){throw 'V4 must remain the candidate.'}
if([bool]$config.master_project_book.v4_production_approved){throw 'V4 cannot be Production.'}
if($config.market_structure.status_rule_status-ne'UNKNOWN_NOT_APPROVED'){throw 'Status mapping must remain unapproved.'}
if($config.risk.alignment_status-ne'KNOWN_GAP_THRESHOLDS_NOT_AVAILABLE'){throw 'Risk threshold gap must be explicit.'}
if(-not(Test-Path -LiteralPath $validation.VersionRecord)){throw 'Version Record is missing.'}

$marketTotal=0.0
foreach($property in $config.factor_weights.market.PSObject.Properties){$marketTotal+=[double]$property.Value}
if([Math]::Abs($marketTotal-10.0)-gt0.000001){throw "Market weights must sum to 10; received $marketTotal."}

[pscustomobject]@{
    Status='PASS'
    Master=$validation.MasterProjectBook
    MasterSha256=$validation.MasterSha256
    ProjectVersion=$config.version
    Protocol=$config.protocol
    Candidate=$config.candidate_protocol
    VersionRecord=$validation.VersionRecord
    RiskAlignment=$config.risk.alignment_status
}|Format-List
