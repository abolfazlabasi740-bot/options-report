# OptimusAI V4.1 — Pre-Limit-Up Screening V1

Status: VALIDATED_SHADOW

This layer is an evidence-only TSETMC screening layer. Historical retained data does not preserve the historical exchange static-limit table, so the historical label is explicitly a strong-upper-move proxy and never an exact historical limit-up label.

## Historical event
- Event: next retained TSETMC session high is at least 5.5% above the entry close.
- Matching: chronological observations from retained TSETMC underlying histories.
- Split: first 70% chronological observations for threshold derivation; final 30% held out.
- Thresholds: training-only P75 for 5-session return, 5/20 volume ratio and 20-session range position.
- Trigger: at least 2 of 3 conditions.
- OOS metrics: persisted in output/pre_limit_up_validation.json.

## Current-session alert
- Source: TSETMC instrument-info static upper limit plus current retained observation.
- Rule: upper-limit headroom <= 0.5%.
- Purpose: descriptive proximity alert, not a prediction.
- If current-session evidence is unavailable, no alert is claimed.

Production BUY/SELL remains forbidden.
