Set-StrictMode -Version Latest

function Invoke-StrategyEngine {
    param(
        [Parameter(Mandatory=$true)][object[]]$RankedContracts,
        [Parameter(Mandatory=$true)][string]$Protocol
    )
    return [pscustomobject]@{
        Protocol=$Protocol
        DirectionScenario='NOT_PROVIDED'
        EntryRulesStatus='NOT_CONFIRMED'
        ExitRulesStatus='NOT_CONFIRMED'
        GeneratesTradeSignal=$false
        Contracts=$RankedContracts
        Notes=@(
            'Quality ranking only.',
            'No market direction was inferred.',
            'No entry or exit signal was generated.',
            'Strategy rules remain evidence-gated and are not inferred from ranking.'
        )
    }
}

Export-ModuleMember -Function *
