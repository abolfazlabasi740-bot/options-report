param(
    [string]$InputWorkbook,
    [switch]$Download,
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [switch]$Quiet,
    [double]$MinLeverage = 0.0,
    [switch]$V4Candidate,
    [string]$SymbolPrefix,
    [int]$TopCount = 0
)

$ErrorActionPreference='Stop'
$ProjectRoot=(Resolve-Path -LiteralPath $ProjectRoot).Path
$moduleRoot=Join-Path $ProjectRoot 'engines'
$modules=@(
    'common/CommonEngine.psm1',
    'data/DataEngine.psm1',
    'parsing/ParsingEngine.psm1',
    'financial/FinancialEngine.psm1',
    'analytics/AnalyticsEngine.psm1',
    'scoring/ScoringEngine.psm1',
    'risk/RiskEngine.psm1',
    'underlying/TsetmcUnderlyingEngine.psm1',
    'strategy/StrategyEngine.psm1',
    'decision/DecisionEngine.psm1',
    'reporting/ReportingEngine.psm1',
    'audit/AuditEngine.psm1',
    'learning/LearningEngine.psm1',
    'learning/SevenDayLearningEngine.psm1',
    'knowledge/KnowledgeEngine.psm1'
)
foreach($module in $modules){Import-Module -Force (Join-Path $moduleRoot $module)}

$paths=[ordered]@{
    Config=Join-Path $ProjectRoot 'configs/project.json'
    FeatureRegistry=Join-Path $ProjectRoot 'configs/feature_registry.json'
    VersionRecord=Join-Path $ProjectRoot ([string](Read-ProjectConfig (Join-Path $ProjectRoot 'configs/project.json')).version_record)
    Raw=Join-Path $ProjectRoot 'data/raw'
    Processed=Join-Path $ProjectRoot 'data/processed'
    Snapshots=Join-Path $ProjectRoot 'data/snapshots'
    RunSnapshots=Join-Path $ProjectRoot 'data/snapshots/runs'
    FeatureSnapshots=Join-Path $ProjectRoot 'data/snapshots/features'
    RankingSnapshots=Join-Path $ProjectRoot 'data/snapshots/rankings'
    Archive=Join-Path $ProjectRoot 'data/archive'
    Logs=Join-Path $ProjectRoot 'logs'
    Reports=Join-Path $ProjectRoot 'reports'
    Audit=Join-Path $ProjectRoot 'logs/audit'
    HashManifests=Join-Path $ProjectRoot 'logs/audit/hash_manifests'
    Learning=Join-Path $ProjectRoot 'library/reports'
    RawExperience=Join-Path $ProjectRoot 'library/raw_experience'
    ValidatedKnowledge=Join-Path $ProjectRoot 'library/validated_knowledge'
    FailedRules=Join-Path $ProjectRoot 'library/failed_rules'
    SuccessfulPatterns=Join-Path $ProjectRoot 'library/successful_patterns'
    MarketRegimes=Join-Path $ProjectRoot 'library/market_regimes'
    FeatureKnowledge=Join-Path $ProjectRoot 'library/feature_knowledge'
    StrategyKnowledge=Join-Path $ProjectRoot 'library/strategy_knowledge'
    Experiments=Join-Path $ProjectRoot 'library/experiments'
    Versions=Join-Path $ProjectRoot 'library/versions'
}
foreach($path in $paths.Values){
    if([IO.Path]::GetExtension([string]$path)-eq''){New-Item -ItemType Directory -Force -Path $path|Out-Null}
}

$config=Read-ProjectConfig $paths.Config
$configValidation=Assert-ProjectConfig -Config $config -ProjectRoot $ProjectRoot
$runId=New-RunId
$startTimestamp=(Get-Date).ToString('o')
$logPath=Join-Path $paths.Logs 'pipeline.jsonl'
Write-ProcessingLog $logPath $runId 'START' 'OK' 'Pipeline started with Master Project Book governance validation.'

try{
    if($Download -or [string]::IsNullOrWhiteSpace($InputWorkbook)){
        Write-ProcessingLog $logPath $runId 'DATA' 'STARTED' 'Downloading approved Optionschool endpoint (automatic default).'
        $received=Receive-OptionschoolWorkbook -Endpoint $config.data_source.endpoint -DestinationDirectory $paths.Raw -MinimumBytes $config.data_source.minimum_bytes
        $workbookPath=$received.Path
        Write-ProcessingLog $logPath $runId 'DATA' 'OK' $received.Status
    } elseif(-not[string]::IsNullOrWhiteSpace($InputWorkbook)){
        $workbookPath=(Resolve-Path -LiteralPath $InputWorkbook).Path
        if(-not(Test-XlsxFile $workbookPath $config.data_source.minimum_bytes)){throw 'Input workbook is not a valid XLSX file.'}
        Write-ProcessingLog $logPath $runId 'DATA' 'OK' 'Using user-supplied local Optionschool workbook.'
    } else {
        $candidate=Get-LatestOptionWorkbook -Directory (Split-Path -Parent $ProjectRoot) -Pattern $config.data_source.file_pattern
        if($null-eq$candidate){throw 'No Optionschool workbook was found.'}
        $workbookPath=$candidate.FullName
        Write-ProcessingLog $logPath $runId 'DATA' 'OK' 'Using latest local Optionschool workbook.'
    }

    $parsed=Read-OptionsWorkbook -WorkbookPath $workbookPath -Config $config
    $schemaHash=Get-StringSha256 (($parsed.Headers|ForEach-Object{[string]$_})-join"`n")
    Write-ProcessingLog $logPath $runId 'PARSING' 'OK' "Parsed $($parsed.SourceRows) source rows; schema hash=$schemaHash."

    $financial=Convert-ToFinancialContracts -Rows $parsed.Rows
    if($financial.Contracts.Count-eq0){throw 'No valid contracts remained after hard filters.'}
    Write-ProcessingLog $logPath $runId 'FINANCIAL' 'OK' "Valid contracts: $($financial.Contracts.Count)."

    $analyzed=Add-ContractAnalytics -Contracts $financial.Contracts
    $baseScored=Invoke-V3Scoring -Contracts $analyzed -Config $config
    $ranked=Invoke-V3Risk -ScoredContracts $baseScored -Config $config
    $reportUniverse=@($ranked)
    if($V4Candidate -or $MinLeverage -gt 0.0){
        if($MinLeverage -le 0.0){$MinLeverage=3.0}
        $reportUniverse=@($ranked|Where-Object{$null -ne $_.Leverage -and [double]$_.Leverage -ge $MinLeverage})
        if($reportUniverse.Count -eq 0){throw "No contracts met the V4 candidate leverage gate >= $MinLeverage."}
    }
    if(-not [string]::IsNullOrWhiteSpace($SymbolPrefix)){
        $reportUniverse=@($reportUniverse|Where-Object{([string]$_.Symbol).StartsWith($SymbolPrefix)})
        if($reportUniverse.Count -eq 0){throw "No contracts matched the requested underlying prefix: $SymbolPrefix."}
    }
    $effectiveTopCount=if($TopCount -gt 0){$TopCount}else{[int]$config.report.top_count}
    $strategy=Invoke-StrategyEngine -RankedContracts $reportUniverse -Protocol $config.protocol
    $decision=Invoke-DecisionEngine -RankedContracts $strategy.Contracts -TopCount $effectiveTopCount -Config $config
    Write-ProcessingLog $logPath $runId 'SCORING' 'OK' "V3 scoring completed; risk mode=$($config.risk.execution_mode); alignment=$($config.risk.alignment_status)."

    $featureCatalog=Get-FeatureCatalog -RegistryPath $paths.FeatureRegistry
    $codeManifest=Get-CodeManifest -ProjectRoot $ProjectRoot
    $codeManifestCanonical=($codeManifest|ConvertTo-Json -Compress -Depth 8)
    $codeManifestSha256=Get-StringSha256 $codeManifestCanonical
    $previous=Get-PreviousRun -RunDirectory $paths.RunSnapshots -ExcludeRunId $runId
    $currentRunContext=[pscustomobject]@{
        RunId=$runId
        ConfigSha256=Get-FileSha256 $paths.Config
        CodeManifestSha256=$codeManifestSha256
    }
    $comparison=Compare-WithPreviousRun -Previous $previous -CurrentTop $decision.Top -CurrentRun $currentRunContext
    $currentRunContext|Add-Member -NotePropertyName Protocol -NotePropertyValue $config.protocol -Force
    $education=Get-LearningDiscussion -CurrentTop $decision.Top -Comparison $comparison -Run $currentRunContext
    $sevenDayLearning=Get-SevenDayLearningSummary `
        -RawDirectory $paths.Raw `
        -Config $config `
        -CurrentWorkbookPath $workbookPath `
        -TransitionCount 7 `
        -TopCount $(if($TopCount -gt 0){$TopCount}else{25}) `
        -MinimumLeverage $(if($V4Candidate -or $MinLeverage -gt 0.0){$MinLeverage}else{0.0})
    $masterPath=$configValidation.MasterProjectBook

    $featureSnapshotPath=Join-Path $paths.FeatureSnapshots ($runId+'.json')
    $featureSnapshot=@($ranked|ForEach-Object{
        [pscustomobject]@{
            SourceRow=$_.SourceRow
            Symbol=$_.Symbol
            Type=$_.Type
            Raw=[pscustomobject]@{
                Strike=$_.Strike;Underlying=$_.Underlying;Expiration=$_.Expiration;Last=$_.Last
                CalendarDays=$_.CalendarDays;TradingDays=$_.TradingDays;OI=$_.OI;Volume=$_.Volume
                TradeValue=$_.TradeValue;IV=$_.IV;HV=$_.HV;BSDiff=$_.BSDiff;StrikeDiff=$_.StrikeDiff
                Delta=$_.Delta;Gamma=$_.Gamma;ThetaRatio=$_.ThetaRatio;Vega=$_.Vega;Rho=$_.Rho;Status=$_.Status
            }
            Derived=[pscustomobject]@{
                Breakeven=$_.Breakeven;BEDistance=$_.BEDistance;Leverage=$_.Leverage;RemainingDays=$_.RemainingDays
                SpreadRatio=$_.SpreadRatio;Depth=$_.Depth;IVHV=$_.IVHV;TimeCost=$_.TimeCost
                LastVsClosePct=$_.LastVsClosePct;IntradayRangePct=$_.IntradayRangePct
            }
            Scoring=[pscustomobject]@{
                BaseScoreBeforeVolumePenalty=$_.BaseScoreBeforeVolumePenalty
                LiquidityVolumeScore=$_.LiquidityVolumeScore
                LiquidityVolumePenalty=$_.LiquidityVolumePenalty
                BaseScore=$_.BaseScore
            }
            Quality=[pscustomobject]@{Confidence=$_.DataConfidence;Missing=$_.MissingData;Flags=$_.Flags}
            FactorBreakdown=$_.FactorBreakdown
            RiskPercentiles=$_.RiskPercentiles
        }
    })
    $featureSnapshot|ConvertTo-Json -Depth 12|Set-Content -Encoding UTF8 -LiteralPath $featureSnapshotPath

    $rankingSnapshotPath=Join-Path $paths.RankingSnapshots ($runId+'.json')
    $rankingSnapshot=@()
    $rankNumber=0
    foreach($item in $ranked){
        $rankNumber++
        $rankingSnapshot+=[pscustomobject]@{
            Rank=$rankNumber
            Symbol=$item.Symbol
            BaseScore=$item.BaseScore
            BaseScoreBeforeVolumePenalty=$item.BaseScoreBeforeVolumePenalty
            LiquidityVolumeScore=$item.LiquidityVolumeScore
            LiquidityVolumePenalty=$item.LiquidityVolumePenalty
            RiskPenalty=$item.RiskPenalty
            FinalScore=$item.FinalScore
            TradeValue=$item.TradeValue
            Blocks=[pscustomobject]@{
                Liquidity=$item.BlockLiquidity;Valuation=$item.BlockValuation;Payoff=$item.BlockPayoff
                Time=$item.BlockTime;Greeks=$item.BlockGreeks;Market=$item.BlockMarket
            }
            RiskModel=$item.RiskModel
            RiskAlignmentStatus=$item.RiskAlignmentStatus
        }
    }
    $rankingSnapshot|ConvertTo-Json -Depth 7|Set-Content -Encoding UTF8 -LiteralPath $rankingSnapshotPath
    $deterministicDigest=Get-FileSha256 $rankingSnapshotPath

    $learning=[pscustomobject]@{
        RunId=$runId
        Timestamp=$startTimestamp
        Comparison=$comparison
        Education=$education
        SevenDayLearning=$sevenDayLearning
        ActualOutcome='PENDING_NEXT_REAL_DATA'
        AutomaticRuleChangeAllowed=$false
        ProposedChanges=@()
        ValidationStatus='COLLECTING_EVIDENCE'
        MinimumValidationSamples=[int]$config.learning.minimum_validation_samples
        ProductionMutationPerformed=$false
    }
    $learningPath=Write-LearningRecord -Record $learning -Directory $paths.Learning
    $experiencePath=Register-RawExperience -LearningRecord $learning -RawExperienceDirectory $paths.RawExperience

    $endTimestamp=(Get-Date).ToString('o')
    $run=[pscustomobject]@{
        RunId=$runId
        StartTimestamp=$startTimestamp
        EndTimestamp=$endTimestamp
        Timestamp=$startTimestamp
        Protocol=$config.protocol
        ReportVariant=if($V4Candidate -or $MinLeverage -gt 0.0){'V4_CANDIDATE_LEVERAGE_GATE'}else{'V3_BASELINE'}
        MinLeverage=if($V4Candidate -or $MinLeverage -gt 0.0){$MinLeverage}else{$null}
        SymbolPrefix=if([string]::IsNullOrWhiteSpace($SymbolPrefix)){$null}else{$SymbolPrefix}
        TopCount=$effectiveTopCount
        CandidateProtocol=$config.candidate_protocol
        Version=$config.version
        ReleaseStatus=$config.release_status
        Versions=$config.versions
        FileName=[IO.Path]::GetFileName($workbookPath)
        FilePath=$workbookPath
        FileSha256=Get-FileSha256 $workbookPath
        SchemaHash=$schemaHash
        ConfigSha256=Get-FileSha256 $paths.Config
        CodeManifestSha256=$codeManifestSha256
        FeatureRegistrySha256=Get-FileSha256 $paths.FeatureRegistry
        MasterProjectBook=$masterPath
        MasterProjectBookSha256=$configValidation.MasterSha256
        VersionRecord=$configValidation.VersionRecord
        VersionRecordSha256=$configValidation.VersionRecordSha256
        SourceRows=$parsed.SourceRows
        ValidRows=$financial.Contracts.Count
        RemovedRows=$financial.RemovedRows
        RemovedByReason=$financial.RemovedByReason
        Calls=@($financial.Contracts|Where-Object{$_.Type-eq'Call'}).Count
        Puts=@($financial.Contracts|Where-Object{$_.Type-eq'Put'}).Count
        UnknownType=@($financial.Contracts|Where-Object{$_.Type-eq'Unknown'}).Count
        GeneratesTradeSignal=$false
        RiskModel=$config.risk.execution_mode
        RiskAlignmentStatus=$config.risk.alignment_status
        KnownGaps=@($config.known_gaps)
        DeterministicDigest=$deterministicDigest
        FeatureSnapshotPath=$featureSnapshotPath
        RankingSnapshotPath=$rankingSnapshotPath
        Top=$decision.Top
        FeatureCatalog=$featureCatalog
        CodeManifest=$codeManifest
        LearningDiscussion=$education
        SevenDayLearning=$sevenDayLearning
    }

    $reportSuffix=if($V4Candidate -or $MinLeverage -gt 0.0){'_options_report_v4.md'}else{'_options_report.md'}
    $reportPath=Join-Path $paths.Reports ($runId+$reportSuffix)
    $underlyingAnalysis=$null
    if($V4Candidate -or $MinLeverage -gt 0.0){
        $underlyingMap=[ordered]@{
            'ضخود'='خودرو'
            'ضسپا'='خساپا'
            'ضملت'='وبملت'
            'ضصاد'='وبصادر'
            'ضتجارت'='وتجارت'
            'ضجار'='وتجارت'
            'ضهمن'='خبهمن'
            'ضبساما'='سامان'
            'ضستا'='شستا'
            'ضشنا'='شپنا'
            'ضفلا'='فولاد'
            'ضملی'='فملی'
            'ضهرم'='هرمز'
            'ضذوب'='ذوب'
            'ضفرابورس'='فرابورس'
            'ضفزر'='فزر'
            'ضتوان'='توان'
            'ضاطلس'='اطلس'
            'ضجوا'='جواهر'
            'ضطعام'='طعام'
        }
        $underlyingNames=@()
        foreach($item in @($decision.Top)){
            foreach($prefix in $underlyingMap.Keys){
                if(([string]$item.Symbol).StartsWith($prefix)){ $underlyingNames += $underlyingMap[$prefix]; break }
            }
        }
        $underlyingSnapshots=@()
        foreach($name in @($underlyingNames|Select-Object -Unique)){
            $underlyingSnapshots += Get-TsetmcUnderlyingSnapshot -Symbol $name
        }
        $asOfValues=@($underlyingSnapshots | Where-Object {
            $_.Status -eq 'OK' -and -not [string]::IsNullOrWhiteSpace([string]$_.AsOf)
        } | ForEach-Object { [string]$_.AsOf } | Sort-Object -Descending)
        $underlyingAsOf=if($asOfValues.Count -gt 0){$asOfValues[0]}else{(Get-Date).ToString('yyyyMMdd')}
        $underlyingAnalysis=[pscustomobject]@{
            AsOf=$underlyingAsOf
            SourceStatus='TSETMC_POINT_IN_TIME'
            Notes=@(
                'Underlying news and fundamental review is separate from option score; V3 weights remain unchanged.'
                'TSETMC/Codal point-in-time evidence must be checked before any directional conclusion.'
                'Option rows remain the primary ranking input; underlying metrics are advisory context for V4 Candidate.'
            )
            Underlyings=@($underlyingSnapshots)
        }
        $run|Add-Member -NotePropertyName UnderlyingAnalysis -NotePropertyValue $underlyingAnalysis -Force
    }
    $report=New-OptionsMarkdownReport `
        -Run $run `
        -Top $decision.Top `
        -Comparison $comparison `
        -Learning $learning `
        -UnderlyingAnalysis $underlyingAnalysis `
        -SevenDayLearning $sevenDayLearning `
        -OutputPath $reportPath

    $runSnapshot=Join-Path $paths.RunSnapshots ($runId+'.json')
    $run|ConvertTo-Json -Depth 14|Set-Content -Encoding UTF8 -LiteralPath $runSnapshot

    $hashManifestPath=Join-Path $paths.HashManifests ($runId+'.json')
    $audit=[pscustomobject]@{
        RunId=$runId
        StartTimestamp=$startTimestamp
        EndTimestamp=$endTimestamp
        RunManifest=[pscustomobject]@{
            Protocol=$run.Protocol;CandidateProtocol=$run.CandidateProtocol;ProjectVersion=$run.Version
            Versions=$run.Versions;ReleaseStatus=$run.ReleaseStatus;DeterministicDigest=$deterministicDigest
        }
        Input=[pscustomobject]@{
            Workbook=$workbookPath;Sha256=$run.FileSha256;Bytes=(Get-Item -LiteralPath $workbookPath).Length
            Source=$config.data_source.name;SchemaHash=$schemaHash;Config=$paths.Config;ConfigSha256=$run.ConfigSha256
            MasterProjectBook=$masterPath;MasterProjectBookSha256=$run.MasterProjectBookSha256
            VersionRecord=$run.VersionRecord;VersionRecordSha256=$run.VersionRecordSha256
        }
        Processing=[pscustomobject]@{
            SourceRows=$run.SourceRows;ValidRows=$run.ValidRows;RemovedRows=$run.RemovedRows
            RemovedByReason=$run.RemovedByReason
        }
        Features=[pscustomobject]@{
            RegistryPath=$paths.FeatureRegistry;RegistrySha256=$run.FeatureRegistrySha256
            SnapshotPath=$featureSnapshotPath;Catalog=$run.FeatureCatalog
            MissingDataSummary=@($decision.Top|ForEach-Object{
                [pscustomobject]@{Symbol=$_.Symbol;Confidence=$_.DataConfidence;Missing=$_.MissingData;Flags=$_.Flags}
            })
        }
        Scores=@($decision.Top|ForEach-Object{
            [pscustomobject]@{
                Symbol=$_.Symbol;Base=$_.BaseScore;Penalty=$_.RiskPenalty;Final=$_.FinalScore
                BaseBeforeVolumePenalty=$_.BaseScoreBeforeVolumePenalty
                LiquidityVolumeScore=$_.LiquidityVolumeScore;LiquidityVolumePenalty=$_.LiquidityVolumePenalty
                RiskModel=$_.RiskModel;RiskAlignmentStatus=$_.RiskAlignmentStatus;RiskFlags=$_.RiskFlags
                Blocks=[pscustomobject]@{
                    Liquidity=$_.BlockLiquidity;Valuation=$_.BlockValuation;Payoff=$_.BlockPayoff
                    Time=$_.BlockTime;Greeks=$_.BlockGreeks;Market=$_.BlockMarket
                }
                Factors=$_.FactorBreakdown
            }
        })
        Risk=[pscustomobject]@{
            ExecutionMode=$config.risk.execution_mode
            MasterTargetMode=$config.risk.master_target_mode
            AlignmentStatus=$config.risk.alignment_status
            ApprovedThresholds=$config.risk.approved_unfavorable_thresholds
            KnownGap='RISK_V3_UNFAVORABLE_PERCENTILE_THRESHOLDS_NOT_PRESENT_IN_MASTER'
        }
        Decision=$decision
        Strategy=$strategy
        ReportPath=$reportPath
        SevenDayLearning=$sevenDayLearning
        Outcome='PENDING_NEXT_REAL_DATA'
        LearningPath=$learningPath
        KnowledgeExperiencePath=$experiencePath
        RunSnapshotPath=$runSnapshot
        RankingSnapshotPath=$rankingSnapshotPath
        HashManifestPath=$hashManifestPath
        Governance=[pscustomobject]@{
            Baseline='V3';Candidate='V4';V4ProductionApproved=$false
            VersionRecord=$run.VersionRecord;VersionRecordSha256=$run.VersionRecordSha256
            KnownGaps=@($config.known_gaps);ConfigValidation=$configValidation
        }
    }
    $auditPath=Write-AuditRecord -Record $audit -AuditDirectory $paths.Audit

    $artifactPaths=@(
        $workbookPath,$paths.Config,$paths.FeatureRegistry,$paths.VersionRecord,$masterPath,$featureSnapshotPath,$rankingSnapshotPath,
        $learningPath,$experiencePath,$reportPath,$runSnapshot,$auditPath
    )
    $hashManifest=[pscustomobject]@{
        RunId=$runId
        CreatedAt=(Get-Date).ToString('o')
        Artifacts=@($artifactPaths|ForEach-Object{
            $item=Get-Item -LiteralPath $_
            [pscustomobject]@{Path=$item.FullName;Sha256=Get-FileSha256 $item.FullName;Bytes=$item.Length}
        })
        Code=$codeManifest
    }
    $hashManifest|ConvertTo-Json -Depth 7|Set-Content -Encoding UTF8 -LiteralPath $hashManifestPath

    Write-ProcessingLog $logPath $runId 'COMPLETE' 'OK' "Report=$reportPath Audit=$auditPath HashManifest=$hashManifestPath"

    $marker=Join-Path (Split-Path -Parent $ProjectRoot) '.options_report_last_processed.txt'
    [IO.File]::WriteAllText($marker,$run.FileName,[Text.UTF8Encoding]::new($false))

    $result=[pscustomobject]@{
        Status='COMPLETED'
        RunId=$runId
        Workbook=$workbookPath
        Report=$reportPath
        Audit=$auditPath
        HashManifest=$hashManifestPath
        FeatureSnapshot=$featureSnapshotPath
        RankingSnapshot=$rankingSnapshotPath
        Learning=$learningPath
        RawExperience=$experiencePath
        DeterministicDigest=$deterministicDigest
        RiskAlignmentStatus=$run.RiskAlignmentStatus
        Top=$decision.Top
        Markdown=$report.Markdown
    }
    if(-not$Quiet){$report.Markdown}
    return $result
} catch {
    Write-ProcessingLog $logPath $runId 'FAILED' 'ERROR' $_.Exception.Message
    throw
}
