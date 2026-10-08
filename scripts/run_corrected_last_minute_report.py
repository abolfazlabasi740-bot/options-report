#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bale_listener import generate_report

if __name__ == "__main__":
    report = generate_report("فرصت‌لحظه‌آخری‌آپشن")
    print(report)
