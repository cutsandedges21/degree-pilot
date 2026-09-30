"""Where DegreePilot keeps things on disk.

Large or private files (test documents, downloads, checkpoints) live under the data
directory, which is gitignored. Set DP_DATA_DIR to move it, e.g. outside OneDrive.
"""
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / "contracts"


def data_dir() -> Path:
    """DP_DATA_DIR if set, else <repo>/data. Read on every call so tests can change it."""
    return Path(os.environ.get("DP_DATA_DIR", REPO_ROOT / "data"))


def testsets_dir() -> Path:
    return data_dir() / "testsets"
