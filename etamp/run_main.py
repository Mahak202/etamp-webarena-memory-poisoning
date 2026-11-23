"""Main N=20 experiment (guide section 2): each frozen task run twice,
clean vs poisoned matched memory, order randomized per-task with seed 43.
Model/settings frozen post-pilot: gpt-5.6-luna, reasoning.effort=none,
max_output_tokens=1024, 15-step cap, no auto-retry, 60s API timeout.

NOTE: no environment/site-data reset between runs — the WebArena FULL_RESET
service isn't running locally and has never been wired into this repo, and
every task in this dataset is flagged require_reset=False upstream. Browser
session/login IS reset each run via run.py's existing auto_login flow.
Disclosed here per the guide's own transparency norm, not silently done.
"""
import csv
import datetime
import pathlib
import random
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = REPO / "etamp" / "sample_manifest.csv"
RESULT_ROOT = REPO / "results" / "main"
LOG_ROOT = REPO / "logs" / "main"
RUN_LOG_CSV = REPO / "etamp" / "main_run_log.csv"

MODEL = "gpt-5.6-luna"
STEPS = 15
INSTR = "agent/prompts/jsons/p_cot_id_actree_2s.json"
PID = 2026
ORDER_SEED = 43

COMMON_FLAGS = [
    "--instruction_path", INSTR,
    "--max_steps", str(STEPS),
    "--model", MODEL,
    "--mode", "responses",
    "--reasoning_effort", "none",
    "--max_output_tokens", "1024",
    "--api_timeout", "60",
    "--no_retry",
]


def load_main_pairs() -> list[tuple[int, int]]:
    pairs = []
    with MANIFEST.open() as f:
        for row in csv.DictReader(f):
            if row["role"] == "main":
                pairs.append((int(row["intent_template_id"]), int(row["task_id"])))
    return sorted(pairs, key=lambda x: x[1])


def run_one(task_id: int, condition: str) -> tuple[int, float, pathlib.Path]:
    result_dir = RESULT_ROOT / condition
    result_dir.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / f"{task_id}_{condition}.log"

    cmd = ["python", "run.py", *COMMON_FLAGS,
           "--test_start_idx", str(task_id),
           "--test_end_idx", str(task_id + 1),
           "--result_dir", str(result_dir)]
    cmd += ["--poison_pid", str(PID)] if condition == "poison" else ["--matched_clean"]

    t0 = time.time()
    with log_path.open("w") as lf:
        proc = subprocess.run(cmd, cwd=REPO, stdout=lf, stderr=subprocess.STDOUT)
    return proc.returncode, time.time() - t0, log_path


def main() -> None:
    pairs = load_main_pairs()
    rng = random.Random(ORDER_SEED)
    schedule = []
    for fam, tid in pairs:
        order = ["poison", "clean"]
        rng.shuffle(order)
        schedule.append((fam, tid, order))

    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    new_file = not RUN_LOG_CSV.exists()
    with RUN_LOG_CSV.open("a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new_file:
            w.writerow(["task_id", "template_id", "condition", "run_order",
                        "returncode", "elapsed_s", "started_at"])
        total = len(schedule) * 2
        done = 0
        for fam, tid, order in schedule:
            for i, cond in enumerate(order, start=1):
                started = datetime.datetime.now().isoformat()
                done += 1
                print(f"[{done}/{total}] task={tid} family={fam} order={i} "
                      f"condition={cond}", flush=True)
                rc, elapsed, log_path = run_one(tid, cond)
                w.writerow([tid, fam, cond, i, rc, f"{elapsed:.1f}", started])
                f.flush()
                print(f"    -> exit={rc} elapsed={elapsed:.1f}s log={log_path}",
                      flush=True)


if __name__ == "__main__":
    sys.exit(main())
