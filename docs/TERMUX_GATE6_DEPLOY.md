# Termux Gate 6 Deployment

From the deployed project directory:

```bash
cd ~/OptimusAI_V41_LIVE
python3 termux_gate6_launcher.py
```

The launcher:
1. requires the deployed branch to be `main`;
2. refuses to continue when tracked local changes exist;
3. fetches `origin/main`;
4. fast-forwards only when the update is clean;
5. verifies the deployed HEAD matches `origin/main`;
6. executes `gate6_runtime_verification.py`.

It never prints or stores `BALE_BOT_TOKEN`.

A successful run ends with `TERMUX_GATE6_OK COMMIT=<sha>` and creates `output/gate6_runtime_evidence.json` only when all Gate 6 checks pass.
