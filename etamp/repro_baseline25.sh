#!/bin/bash
# Baseline over 25 fast Reddit action-tasks, ONE model, basic payload, 12-step cap.
# POISON phase runs first (ASR_B), then CLEAN (TSR).
set -e
cd ~/eTAMP_reproduction/webarena
source ~/eTAMP_reproduction/env.sh
source .venv/bin/activate

MODEL="gpt-4o-mini"
PID=2026
STEPS=12
INSTR="agent/prompts/jsons/p_cot_id_actree_2s.json"
IDS="404 405 406 407 408 409 410 610 611 612 613 614 625 626 627 628 629 719 720 721 722 723 724 725 726"
mkdir -p results/baseline25 logs

echo "############ POISONED run (ASR_B) — 25 Reddit tasks, max $STEPS steps ############"
rm -rf results/baseline25/poison_B; : > logs/base25_poison.log
for t in $IDS; do
  python run.py --instruction_path $INSTR --max_steps $STEPS \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --poison_pid $PID --result_dir results/baseline25/poison_B \
    2>&1 | tee -a logs/base25_poison.log || echo "[skip $t]"
done
echo "@@@ POISON PHASE DONE @@@"

echo "############ CLEAN run (TSR) — 25 Reddit tasks, max $STEPS steps ############"
rm -rf results/baseline25/clean; : > logs/base25_clean.log
for t in $IDS; do
  python run.py --instruction_path $INSTR --max_steps $STEPS \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --result_dir results/baseline25/clean \
    2>&1 | tee -a logs/base25_clean.log || echo "[skip $t]"
done
echo "############ ALL DONE ############"
