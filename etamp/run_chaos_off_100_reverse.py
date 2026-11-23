"""Reverse-direction (Reddit -> Shopping), chaos-off, N=100 poison-only
attack run -- mirrors run_chaos_off_100.py but with poison_direction set to
reddit2shop and a fresh set of 100 shopping-only task ids (the first 100 of
the 190 shopping-only WebArena tasks, by id -- same selection rule the
original 100-reddit-task list used). Model/settings match both earlier runs
for direct comparability: gpt-5.6-luna, reasoning.effort=none,
max_output_tokens=1024, 15-step cap, no auto-retry, 60s API timeout.
chaos is off (no --chaos flag passed at all).
"""
import csv
import datetime
import pathlib
import random
import subprocess
import sys
import time

REPO = pathlib.Path(__file__).resolve().parent.parent
RESULT_DIR = REPO / "results" / "chaos_off_100_reverse" / "poison"
LOG_ROOT = REPO / "logs" / "chaos_off_100_reverse"
RUN_LOG_CSV = REPO / "etamp" / "chaos_off_100_reverse_run_log.csv"

MODEL = "gpt-5.6-luna"
STEPS = 15
INSTR = "agent/prompts/jsons/p_cot_id_actree_2s.json"
PID = 2026
ORDER_SEED = 200

TASK_IDS = [int(x) for x in (
    "21 22 23 24 25 26 47 48 49 50 51 96 117 118 124 125 126 141 142 143 144 145 "
    "146 147 148 149 150 158 159 160 161 162 163 164 165 166 167 188 189 190 191 "
    "192 225 226 227 228 229 230 231 232 233 234 235 238 239 240 241 242 260 261 "
    "262 263 264 269 270 271 272 273 274 275 276 277 278 279 280 281 282 283 284 "
    "285 286 298 299 300 301 302 313 319 320 321 322 323 324 325 326 327 328 329 "
    "330 331"
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
    "--poison_direction", "reddit2shop",
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
            print(f"[{i}/{total}] task={tid} condition=poison direction=reddit2shop chaos=off", flush=True)
            rc, elapsed, log_path = run_one(tid)
            w.writerow([tid, "poison", i, rc, f"{elapsed:.1f}", started])
            f.flush()
            print(f"    -> exit={rc} elapsed={elapsed:.1f}s log={log_path}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
