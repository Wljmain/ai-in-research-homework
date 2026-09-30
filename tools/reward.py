"""Prints the reward of the single trial in a Harbor job folder, or the error that stopped it.

Usage: python3 tools/reward.py jobs/<...>/<job-name>
Prints e.g. `1.0`, or `error: RewardFileNotFoundError: ...` and exits 2.
"""
import json
import sys
from pathlib import Path

job = Path(sys.argv[1])
trials = [p for p in job.glob("*/result.json")]
if not trials:
    print(f"error: no trial result in {job} (did the Docker build fail? see the log next to it)")
    sys.exit(2)
result = json.loads(trials[0].read_text())
rewards = (result.get("verifier_result") or {}).get("rewards") or {}
if "reward" in rewards:
    print(rewards["reward"])
    sys.exit(0)
error = result.get("exception_info") or {}
print(f"error: {error.get('exception_type', 'no reward')}: {str(error.get('exception_message', '')).splitlines()[0][:300] if error.get('exception_message') else ''}")
sys.exit(2)
