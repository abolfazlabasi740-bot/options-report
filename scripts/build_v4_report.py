"""Compatibility entry point.

V4 is not an approved executable protocol. This wrapper preserves the old
command name while producing the Master Project Book governed V3 report.
"""

from __future__ import annotations

import sys

from build_master_report import main


if __name__ == "__main__":
    print(
        "WARNING: V4 is Candidate only; generating the Master Project Book V3 baseline report.",
        file=sys.stderr,
    )
    main()
