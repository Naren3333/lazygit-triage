"""Make the stdlib-only scripts importable as plain modules in tests."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "metrics"))
sys.path.insert(0, str(ROOT / ".claude" / "skills" / "lazygit-triage" / "scripts"))
sys.path.insert(0, str(ROOT / "evals" / "golden"))
