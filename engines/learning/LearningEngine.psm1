Set-StrictMode -Version Latest

function Get-LearningProperty {
    param([AllowNull()][object]$Object,[Parameter(Mandatory=$true)][string]$Name)
    if ($null -eq $Object) { return $null }
    $property = $Object.PSObject.Properties[$Name]
    if ($null -eq $property) { return $null }
    return $property.Value
}

function Get-PreviousRun {
    param([Parameter(Mandatory=$true)][string]$RunDirectory,[string]$ExcludeRunId)
    if(-not(Test-Path -LiteralPath $RunDirectory)){return $null}
    $file=Get-ChildItem -LiteralPath $RunDirectory -File -Filter '*.json'|
        Where-Object{$_.BaseName-ne$ExcludeRunId}|Sort-Object LastWriteTime -Descending|Select-Object -First 1
    if($null-eq$file){return $null}
    return Get-Content -Raw -Encoding UTF8 -LiteralPath $file.FullName|ConvertFrom-Json
}

function Compare-WithPreviousRun {
    param(
        [AllowNull()][object]$Previous,
        [Parameter(Mandatory=$true)][object[]]$CurrentTop,
        [AllowNull()][object]$CurrentRun
    )
    if($null-eq$Previous){
        return [pscustomobject]@{
            Status='NO_PREVIOUS_RUN';CommonContracts=0;RankChanges=@()
            ScoreChanges=@();MaxAbsFinalScoreDelta=$null;MaxAbsBaseScoreDelta=$null
            ModelDriftStatus='NOT_AVAILABLE';AuditStatus='NO_PREVIOUS_RUN'
            OutcomeValidation='NOT_AVAILABLE';OutcomeHorizon='NEXT_RUN'
            PreviousTopOutcomes=@();OutcomeSummary=[pscustomobject]@{
                Evaluated=0;Positive=0;Negative=0;Unchanged=0
                AverageReturnPct=$null;TotalPriceDelta=$null
            }
            ErrorClassification='NOT_AVAILABLE'
        }
    }
    $rankChanges=@()
    $scoreChanges=@()
    $previousBySymbol=@{}
    foreach($item in @($Previous.Top)){ $previousBySymbol[[string]$item.Symbol]=$item }
    $common=0
    $maxFinal=0.0
    $maxBase=0.0
    $currentBySymbol=@{}
    foreach($item in @($CurrentTop)){ $currentBySymbol[[string]$item.Symbol]=$item }
    $outcomes=@()
    $previousTopFive=@($Previous.Top|Select-Object -First 5)
    for($previousIndex=0;$previousIndex-lt$previousTopFive.Count;$previousIndex++){
        $oldItem=$previousTopFive[$previousIndex]
        $symbol=[string]$oldItem.Symbol
        if(-not $currentBySymbol.ContainsKey($symbol)){continue}
        $newItem=$currentBySymbol[$symbol]
        $oldLast=[double]$oldItem.Last
        $newLast=[double]$newItem.Last
        if($oldLast -le 0){continue}
        $delta=$newLast-$oldLast
        $returnPct=($delta/$oldLast)*100.0
        $status=if($returnPct -gt 0.000001){'POSITIVE'}elseif($returnPct -lt -0.000001){'NEGATIVE'}else{'UNCHANGED'}
        $outcomes+=[pscustomobject]@{
            PreviousRank=$previousIndex+1;Symbol=$symbol
            PreviousLast=$oldLast;CurrentLast=$newLast
            PriceDelta=$delta;ReturnPct=$returnPct;OutcomeStatus=$status
        }
    }
    for($i=0;$i-lt$CurrentTop.Count;$i++){
        $symbol=$CurrentTop[$i].Symbol
        if($previousBySymbol.ContainsKey([string]$symbol)){
            $common++
            $oldItem=$previousBySymbol[[string]$symbol]
            $oldRank=@($Previous.Top|ForEach-Object{$_.Symbol}).IndexOf($symbol)+1
            $rankChanges+=[pscustomobject]@{Symbol=$symbol;PreviousRank=$oldRank;CurrentRank=$i+1;Change=$oldRank-($i+1)}
            $finalDelta=[double]$CurrentTop[$i].FinalScore-[double]$oldItem.FinalScore
            $baseDelta=[double]$CurrentTop[$i].BaseScore-[double]$oldItem.BaseScore
            $maxFinal=[Math]::Max($maxFinal,[Math]::Abs($finalDelta))
            $maxBase=[Math]::Max($maxBase,[Math]::Abs($baseDelta))
            $scoreChanges+=[pscustomobject]@{
                Symbol=$symbol;PreviousFinal=[double]$oldItem.FinalScore;CurrentFinal=[double]$CurrentTop[$i].FinalScore
                FinalDelta=$finalDelta;PreviousBase=[double]$oldItem.BaseScore;CurrentBase=[double]$CurrentTop[$i].BaseScore
                BaseDelta=$baseDelta;RiskPenaltyDelta=([double]$CurrentTop[$i].RiskPenalty-[double]$oldItem.RiskPenalty)
            }
        }
    }
    $previousConfigHash=[string](Get-LearningProperty $Previous 'ConfigSha256')
    $currentConfigHash=[string](Get-LearningProperty $CurrentRun 'ConfigSha256')
    $previousCodeHash=[string](Get-LearningProperty $Previous 'CodeManifestSha256')
    $currentCodeHash=[string](Get-LearningProperty $CurrentRun 'CodeManifestSha256')
    $configChanged=($null -ne $CurrentRun -and -not [string]::IsNullOrWhiteSpace($previousConfigHash) -and $previousConfigHash -ne $currentConfigHash)
    $codeChanged=($null -ne $CurrentRun -and -not [string]::IsNullOrWhiteSpace($previousCodeHash) -and $previousCodeHash -ne $currentCodeHash)
    $largeScoreShift=@($scoreChanges|Where-Object{[Math]::Abs([double]$_.FinalDelta)-ge5.0}).Count
    $largeRankShift=@($rankChanges|Where-Object{[Math]::Abs([int]$_.Change)-ge3}).Count
    return [pscustomobject]@{
        Status='COMPARED'
        PreviousRunId=$Previous.RunId
        CommonContracts=$common
        RankChanges=$rankChanges
        ScoreChanges=$scoreChanges
        MaxAbsFinalScoreDelta=$maxFinal
        MaxAbsBaseScoreDelta=$maxBase
        LargeScoreShiftCount=$largeScoreShift
        LargeRankShiftCount=$largeRankShift
        ConfigChanged=$configChanged
        CodeChanged=$codeChanged
        ModelDriftStatus=if($configChanged-or$codeChanged){'IMPLEMENTATION_OR_CONFIG_CHANGED'}else{'NO_HASH_DRIFT'}
        AuditStatus=if($largeScoreShift-gt0-or$largeRankShift-gt0-or$configChanged-or$codeChanged){'REVIEW_REQUIRED'}else{'PASS'}
        OutcomeValidation=if($outcomes.Count -gt 0){'EVALUATED_AGAINST_NEXT_RUN'}else{'NO_COMMON_TOP5_CONTRACTS'}
        OutcomeHorizon='NEXT_RUN'
        PreviousTopOutcomes=$outcomes
        OutcomeSummary=[pscustomobject]@{
            Evaluated=$outcomes.Count
            Positive=@($outcomes|Where-Object{$_.OutcomeStatus -eq 'POSITIVE'}).Count
            Negative=@($outcomes|Where-Object{$_.OutcomeStatus -eq 'NEGATIVE'}).Count
            Unchanged=@($outcomes|Where-Object{$_.OutcomeStatus -eq 'UNCHANGED'}).Count
            AverageReturnPct=if($outcomes.Count -gt 0){($outcomes|Measure-Object ReturnPct -Average).Average}else{$null}
            TotalPriceDelta=if($outcomes.Count -gt 0){($outcomes|Measure-Object PriceDelta -Sum).Sum}else{$null}
        }
        ErrorClassification=if($largeScoreShift-gt0-or$largeRankShift-gt0){'RANK_OR_SCORE_DRIFT_REQUIRES_REVIEW'}else{'NOT_ASSERTED_WITHOUT_ACTUAL_OUTCOME'}
    }
}

function Get-LearningDiscussion {
    param(
        [Parameter(Mandatory=$true)][object[]]$CurrentTop,
        [AllowNull()][object]$Comparison,
        [Parameter(Mandatory=$true)][object]$Run
    )
    $lessons = [Collections.Generic.List[object]]::new()
    $actions = [Collections.Generic.List[string]]::new()
    $evidence = [Collections.Generic.List[string]]::new()
    $missingIv = @($CurrentTop | Where-Object { $null -eq $_.IV }).Count
    $wideSpread = @($CurrentTop | Where-Object { $null -ne $_.SpreadRatio -and $_.SpreadRatio -gt 0.10 }).Count
    $invalidTimeCost = @($CurrentTop | Where-Object { $null -ne $_.TimeCost -and $_.TimeCost -lt 0.0 }).Count
    $extremeLeverage = @($CurrentTop | Where-Object { $null -ne $_.Leverage -and $_.Leverage -gt 20.0 }).Count

    if ($null -eq $Comparison -or $Comparison.Status -eq 'NO_PREVIOUS_RUN') {
        $lessons.Add([pscustomobject]@{
            Claim='این اجرا هنوز outcome قابل‌مقایسه ندارد؛ هیچ رابطه علّی از رتبه و بازده ادعا نمی‌شود.'
            Evidence='NO_PREVIOUS_RUN'
            Confidence='HIGH'
            Disconfirming='اجرای بعدی باید با داده point-in-time و quote قابل‌اجرا بررسی شود.'
            Action='ثبت این اجرا به‌عنوان baseline و عدم تغییر Rule/Weight.'
        })
    } else {
        $outcomeCount = [int]$Comparison.OutcomeSummary.Evaluated
        $lessons.Add([pscustomobject]@{
            Claim='بازده فعلی فقط hypothetical Last-to-Last است و معیار موفقیت معاملاتی نیست.'
            Evidence="Evaluated=$outcomeCount; Horizon=$($Comparison.OutcomeHorizon)"
            Confidence='HIGH'
            Disconfirming='bid/ask، کارمزد، اسلیپیج، حجم و خروج/سررسید باید در label آینده وارد شوند.'
            Action='نگه‌داشتن برچسب PENDING تا تکمیل outcome اجرایی.'
        })
        if ([string]$Comparison.ModelDriftStatus -ne 'NO_HASH_DRIFT') {
            $lessons.Add([pscustomobject]@{
                Claim='تغییر کد یا تنظیمات، مقایسه بازده را آلوده می‌کند.'
                Evidence=[string]$Comparison.ModelDriftStatus
                Confidence='HIGH'
                Disconfirming='تأیید digest یکسان برای config و code manifest.'
                Action='بازبینی جداگانه و عدم نسبت‌دادن outcome به مدل.'
            })
        }
    }
    if ($missingIv -gt 0) {
        $lessons.Add([pscustomobject]@{
            Claim='فقدان IV نباید مزیت رتبه‌بندی ایجاد کند.'
            Evidence="TopMissingIV=$missingIv/$($CurrentTop.Count)"
            Confidence='HIGH'
            Disconfirming='مقایسه همسان با قرارداد دارای IV و اعمال eligibility/missingness cap.'
            Action='ثبت به‌عنوان هشدار V3.2.1؛ score بنیادی/اختیاری وارد رتبه تولیدی نشود.'
        })
        $actions.Add('Missingness را در confidence و eligibility وارد کن؛ بازتوزیع کور وزن ممنوع.')
    }
    if ($wideSpread -gt 0) {
        $lessons.Add([pscustomobject]@{
            Claim='جهش قیمت با spread بزرگ، بازده قابل‌معامله محسوب نمی‌شود.'
            Evidence="TopWideSpread=$wideSpread/$($CurrentTop.Count)"
            Confidence='HIGH'
            Disconfirming='وجود bid/ask معتبر و حجم کافی در همان event time.'
            Action='دو رتبه جدا: فرصت نظری و فرصت قابل‌اجرا.'
        })
        $actions.Add('quote validation و liquidity censoring را قبل از label اعمال کن.')
    }
    if ($invalidTimeCost -gt 0) {
        $lessons.Add([pscustomobject]@{
            Claim='TimeCost منفی نشانه quote نامعتبر/زیر ارزش ذاتی یا stale است، نه مزیت valuation.'
            Evidence="TopNegativeTimeCost=$invalidTimeCost/$($CurrentTop.Count)"
            Confidence='HIGH'
            Disconfirming='تأیید bid/ask و invariant بدون‌آربیتراژ.'
            Action='پرچم‌گذاری و حذف از scoring valuation تا رفع quote.'
        })
    }
    if ($extremeLeverage -gt 0) {
        $lessons.Add([pscustomobject]@{
            Claim='اهرم قیمت‌محور بالا، بدون delta-adjustment، الزاماً فرصت نیست.'
            Evidence="TopExtremeLeverage=$extremeLeverage/$($CurrentTop.Count)"
            Confidence='MEDIUM'
            Disconfirming='delta-adjusted elasticity و سناریوی P&L.'
            Action='جداکردن Fragility از Opportunity در مدل کاندید.'
        })
    }
    $evidence.Add("Run=$($Run.RunId)")
    $evidence.Add("Protocol=$($Run.Protocol)")
    return [pscustomobject]@{
        Required=$true
        Status='EDUCATIONAL_DISCUSSION_ATTACHED'
        Lessons=@($lessons)
        Actions=@($actions | Select-Object -Unique)
        Evidence=@($evidence)
        AutomaticModelChange=$false
        KnowledgePromotion='NOT_ALLOWED_WITHOUT_VALIDATION'
    }
}

function Write-LearningRecord {
    param([Parameter(Mandatory=$true)][object]$Record,[Parameter(Mandatory=$true)][string]$Directory)
    New-Item -ItemType Directory -Force -Path $Directory|Out-Null
    $path=Join-Path $Directory ($Record.RunId+'.json')
    $Record|ConvertTo-Json -Depth 9|Set-Content -Encoding UTF8 -LiteralPath $path
    return $path
}

Export-ModuleMember -Function *
