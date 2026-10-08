#!/usr/bin/env python3
from __future__ import annotations
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if not os.environ.get("OPENAI_API_KEY"):
    raise SystemExit("OPENAI_API_KEY is not set")

task = os.environ.get("OPTIMUSAI_TASK", "").strip()
if not task:
    raise SystemExit("OPTIMUSAI_TASK is not set")

from agent.project_manager import main
main()
