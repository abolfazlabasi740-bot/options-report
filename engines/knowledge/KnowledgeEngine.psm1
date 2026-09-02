Set-StrictMode -Version Latest

function Register-RawExperience {
    param(
        [Parameter(Mandatory=$true)][object]$LearningRecord,
        [Parameter(Mandatory=$true)][string]$RawExperienceDirectory
    )
    New-Item -ItemType Directory -Force -Path $RawExperienceDirectory|Out-Null
    $experience=[pscustomobject]@{
        ExperienceId='EXP_'+$LearningRecord.RunId
        ArtifactType='RAW_EXPERIENCE'
        Version='KNOWLEDGE_V3_2_0'
        RunId=$LearningRecord.RunId
        CreatedAt=(Get-Date).ToString('o')
        Status='RAW_UNVALIDATED'
        ReviewState='PENDING_VALIDATION'
        Evidence=$LearningRecord.Comparison
        SourceRuns=@($LearningRecord.RunId)
        SampleCount=1
        Confidence='NOT_VALIDATED'
        MarketRegime='UNKNOWN'
        EligibleForRuleChange=$false
        Reason='Validation and repeated observations are required.'
    }
    $path=Join-Path $RawExperienceDirectory ($experience.ExperienceId+'.json')
    $experience|ConvertTo-Json -Depth 8|Set-Content -Encoding UTF8 -LiteralPath $path
    return $path
}

Export-ModuleMember -Function *
