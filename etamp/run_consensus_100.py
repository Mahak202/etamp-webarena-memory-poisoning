"""Consensus/social-proof payload, Shopping -> Reddit, chaos-off, N=100
poison-only attack run -- same mechanism, task list, model, and config as
run_helpfulness_100.py; only --poison_style consensus differs. Same attack
target URL signature, so the existing forward detector (ATTACK_RE /
build_results.find_attack) applies unchanged.
"""
import csv
import datetime
import pathlib
import random
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
RESULT_DIR = REPO / "results" / "consensus_100" / "poison"
LOG_ROOT = REPO / "logs" / "consensus_100"
RUN_LOG_CSV = REPO / "etamp" / "consensus_100_run_log.csv"

MODEL = "gpt-5.6-luna"
STEPS = 15
INSTR = "agent/prompts/jsons/p_cot_id_actree_2s.json"
PID = 2026
ORDER_SEED = 500

TASK_IDS = [int(x) for x in (
    "27 28 29 30 31 66 67 68 69 399 400 401 402 403 404 405 406 407 408 409 410 "
    "580 581 582 583 584 595 596 597 598 599 600 601 602 603 604 605 606 607 608 "
    "609 610 611 612 613 614 615 616 617 618 619 620 621 622 623 624 625 626 627 "
    "628 629 630 631 632 633 634 635 636 637 638 639 640 641 642 643 644 645 646 "
    "647 648 649 650 651 652 714 715 716 717 718 719 720 721 722 723 724 725 726 "
    "727 728 729"
).split()]
assert len(TASK_IDS) == 100

COMMON_FLAGS = [
    "--instruction_path", INSTR,
    "--max_steps", str(STEPS),
    "--model", MODEL,
    "--mode", "responses",
    "--reasoning_effort", "none",
    "--max_output_tokens", "1024",
    "--api_timeout", "60",
    "--no_retry",
    "--poison_pid", str(PID),
    "--poison_style", "consensus",
]


def run_one(task_id: int) -> tuple[int, float, pathlib.Path]:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = LOG_ROOT / f"{task_id}_poison.log"

    cmd = ["python", "run.py", *COMMON_FLAGS,
           "--test_start_idx", str(task_id),
           "--test_end_idx", str(task_id + 1),
           "--result_dir", str(RESULT_DIR)]

    t0 = time.time()
    with log_path.open("w") as lf:
        proc = subprocess.run(cmd, cwd=REPO, stdout=lf, stderr=subprocess.STDOUT)
    return proc.returncode, time.time() - t0, log_path


def main() -> None:
    rng = random.Random(ORDER_SEED)
    order = list(TASK_IDS)
    rng.shuffle(order)

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    new_file = not RUN_LOG_CSV.exists()
    with RUN_LOG_CSV.open("a", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new_file:
            w.writerow(["task_id", "condition", "run_order_idx",
                        "returncode", "elapsed_s", "started_at"])
        total = len(order)
        for i, tid in enumerate(order, start=1):
            started = datetime.datetime.now().isoformat()
            print(f"[{i}/{total}] task={tid} condition=poison style=consensus chaos=off", flush=True)
            rc, elapsed, log_path = run_one(tid)
            w.writerow([tid, "poison", i, rc, f"{elapsed:.1f}", started])
            f.flush()
            print(f"    -> exit={rc} elapsed={elapsed:.1f}s log={log_path}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
