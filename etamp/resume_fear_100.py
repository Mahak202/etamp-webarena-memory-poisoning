"""Resume the fear-payload N=100 run for only the task ids that never
completed before the background process was killed. Appends to the same
run log as run_fear_100.py so the eventual tally covers the full 100.
"""
import csv
import datetime
import sys

from run_fear_100 import run_one, RUN_LOG_CSV, RESULT_DIR

MISSING = [27, 401, 410, 580, 583, 596, 610, 626, 636, 639, 644, 646, 647, 719]


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    with RUN_LOG_CSV.open("a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        total = len(MISSING)
        for i, tid in enumerate(MISSING, start=1):
            started = datetime.datetime.now().isoformat()
            print(f"[resume {i}/{total}] task={tid} condition=poison style=fear chaos=off", flush=True)
            rc, elapsed, log_path = run_one(tid)
            w.writerow([tid, "poison", f"resume-{i}", rc, f"{elapsed:.1f}", started])
            f.flush()
            print(f"    -> exit={rc} elapsed={elapsed:.1f}s log={log_path}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
