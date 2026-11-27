"""Canonical end-to-end command: IRENA-only forecast and diagnostic tables. Export the figure separately."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

for script in ("run_pipeline.py", "calibration.py", "boundary_sensitivity.py",
               "model_sensitivity.py", "check_output_tables.py", "release_summary.py"):
    print(f"\n=== {script} ===", flush=True)
    subprocess.run([sys.executable, str(ROOT / "src" / script)], cwd=ROOT, check=True)
