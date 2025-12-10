"""Quick script to run sync_balance once.

Usage:
    ENV=upbit python scripts/test_sync_balance.py
"""

import logging
import sys
from pathlib import Path

# Ensure project root on sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import DaemonScheduler  # noqa: E402
from config import settings  # noqa: E402


def main():
    logging.basicConfig(level=settings.log_level)
    scheduler = DaemonScheduler()
    scheduler.sync_balance()


if __name__ == "__main__":
    main()
