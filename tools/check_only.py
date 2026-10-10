"""check_only.py DIR: run publish_shelf's export checks on DIR, write nothing (exit 1 on a failure)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_shelf import check  # noqa: E402

errs = check(Path(sys.argv[1]))
print("\n".join(errs[:10]) if errs else "", "REFUSED" if errs else "PASSED", sep="\n")
sys.exit(1 if errs else 0)
