# Termux Runtime Verification Gate

Run `python3 runtime_verification.py` from the active project directory on Termux.

The script checks critical file presence, Python compilation, repository SHA when available, presence-only environment flags, and the latest audit-integrity artifact when available.

It never writes secret values. It records only booleans for environment variables such as BALE_BOT_TOKEN and BALE_CHAT_ID.

PASS means the local verification checks succeeded. It is runtime evidence only after the script is actually executed on the target Termux instance.