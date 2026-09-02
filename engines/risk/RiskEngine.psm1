Set-StrictMode -Version Latest

function Invoke-V3Risk {
    param(
        [Parameter(Mandatory=$true)][object[]]$ScoredContracts,
        [Parameter(Mandatory=$true)][object]$Config
    )
    $mode = [string]$Config.risk.execution_mode
    foreach ($contract in $ScoredContracts) {
        $p = $contract.RiskPercentiles
        if ($mode -eq 'STEP_COUNT_V3') {
            if ($null -eq $Config.risk.approved_unfavorable_thresholds) {
                throw 'STEP_COUNT_V3 requires approved unfavorable percentile thresholds. Master Project Book does not provide them.'
            }
            $thresholds = $Config.risk.approved_unfavorable_thresholds
            $states = @(
                ([double]$p.Leverage -ge [double]$thresholds.leverage_high),
                ([double]$p.TradingDays -le [double]$thresholds.trading_days_low),
                ([double]$p.ThetaRatio -ge [double]$thresholds.theta_high),
                ([double]$p.IVHV -ge [double]$thresholds.iv_hv_high),
                ([double]$p.BEDistance -ge [double]$thresholds.breakeven_distance_high)
            )
            $count = @($states | Where-Object { $_ }).Count
            $penalty = switch ($count) {
                5 { [double]$Config.risk.step_penalties.'5' }
                4 { [double]$Config.risk.step_penalties.'4' }
                3 { [double]$Config.risk.step_penalties.'3' }
                default { [double]$Config.risk.step_penalties.less_than_3 }
            }
            $alignment = 'MASTER_TARGET'
            $riskFlags = @("UNFAVORABLE_STATE_COUNT_$count")
        } elseif ($mode -eq 'PAIRWISE_PERCENTILE_TRANSITIONAL') {
            $levRisk = [Math]::Max(0.0,(2.0*[double]$p.Leverage)-1.0)
            $timeRisk = if($null-ne$p.TradingDays){1.0-[double]$p.TradingDays}else{0.0}
            $thetaRisk = if($null-ne$p.ThetaRatio){[double]$p.ThetaRatio}else{0.0}
            $ivHvRisk = if($null-ne$p.IVHV){[double]$p.IVHV}else{0.0}
            $distanceRisk = if($null-ne$p.BEDistance){[double]$p.BEDistance}else{0.0}
            $riskIndex = Get-PairwiseRisk @($levRisk,$timeRisk,$thetaRisk,$ivHvRisk,$distanceRisk)
            $penalty = [Math]::Min([double]$Config.risk.maximum_penalty,[double]$contract.BaseScore*$riskIndex)
            $alignment = [string]$Config.risk.alignment_status
            $riskFlags = @('RISK_MODEL_TRANSITIONAL','MASTER_STEP_THRESHOLDS_NOT_AVAILABLE')
        } else {
            throw "Unsupported risk execution mode: $mode"
        }
        $final = [Math]::Max(0.0,[double]$contract.BaseScore-$penalty)
        $contract | Add-Member RiskPenalty $penalty -Force
        $contract | Add-Member FinalScore $final -Force
        $contract | Add-Member RiskModel $mode -Force
        $contract | Add-Member RiskAlignmentStatus $alignment -Force
        $contract | Add-Member RiskFlags $riskFlags -Force
    }
    return @($ScoredContracts | Sort-Object @{Expression='FinalScore';Descending=$true},@{Expression='TradeValue';Descending=$true},@{Expression='Symbol';Descending=$false})
}

Export-ModuleMember -Function *
