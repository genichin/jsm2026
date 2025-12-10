"""Quick script to run execute_strategy once.

Usage:
    ENV=upbit python scripts/test_execute_strategy.py
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
    scheduler.execute_strategy()


if __name__ == "__main__":
    main()
