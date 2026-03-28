"""
Helper script to auto-generate an Alembic migration from model changes.

Usage:
    python scripts/generate_migration.py "add user avatar column"
"""
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    message = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "auto migration"
    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", message],
        cwd=str(Path(__file__).parent.parent),
    )
    sys.exit(result.returncode)
