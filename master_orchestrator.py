# -*- coding: utf-8 -*-
import sys, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUNDLE_SRC = ROOT / "output" / "reports" / "market_analytics_bundle.json"
WWW_DIR = ROOT / "android_app" / "www"
WWW_DIR.mkdir(parents=True, exist_ok=True)

def main():
    print("🚀 [Master Orchestrator] Running build_validated_bundle.py...")
    res = subprocess.run([sys.executable, str(ROOT / "build_validated_bundle.py")], capture_output=True, text=True)
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr, file=sys.stderr)
        sys.exit(res.returncode)

    dst = WWW_DIR / "market_analytics_bundle.json"
    shutil.copy2(BUNDLE_SRC, dst)
    print(f"✅ Synchronized bundle directly to {dst}")

if __name__ == "__main__":
    main()
