Set-StrictMode -Version Latest

function Invoke-DecisionEngine {
    param(
        [Parameter(Mandatory=$true)][object[]]$RankedContracts,
        [Parameter(Mandatory=$true)][int]$TopCount,
        [Parameter(Mandatory=$true)][object]$Config
    )
    $top=@($RankedContracts|Select-Object -First $TopCount)
    foreach($contract in $top){
        $contract|Add-Member -NotePropertyName DecisionType -NotePropertyValue 'QUALITY_REVIEW_CANDIDATE' -Force
        $contract|Add-Member -NotePropertyName DecisionScenario -NotePropertyValue 'DIRECTION_NOT_PROVIDED' -Force
        $contract|Add-Member -NotePropertyName Classification -NotePropertyValue 'THRESHOLD_NOT_CONFIRMED' -Force
        $contract|Add-Member -NotePropertyName DecisionGateStatus -NotePropertyValue 'REVIEW_REQUIRED' -Force
    }
    return [pscustomobject]@{
        Top=$top
        GeneratesBuySignal=$false
        GeneratesSellSignal=$false
        Scenario='Quality-only ranking'
        ClassificationStatus='Numeric thresholds are not approved.'
        GateSequence=@($Config.decision.gate_sequence)
        GateResults=@(
            [pscustomobject]@{Gate='DATA_QUALITY';Status='EVALUATED';Evidence='DataConfidence, MissingData, Flags'},
            [pscustomobject]@{Gate='LIQUIDITY';Status='SCORED';Evidence='Liquidity block'},
            [pscustomobject]@{Gate='CONTRACT_QUALITY';Status='REVIEW_REQUIRED';Evidence='No approved threshold'},
            [pscustomobject]@{Gate='UNDERLYING_QUALITY';Status='NOT_IMPLEMENTED';Evidence='No approved underlying rule'},
            [pscustomobject]@{Gate='RISK';Status='TRANSITIONAL';Evidence='Risk alignment flag'},
            [pscustomobject]@{Gate='VALUATION';Status='SCORED';Evidence='Valuation block'},
            [pscustomobject]@{Gate='SCENARIO';Status='NOT_PROVIDED';Evidence='No market direction'}
        )
    }
}

Export-ModuleMember -Function *
