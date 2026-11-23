#!/bin/bash
# Minimal eTAMP reproduction: ONE portion (Shopping -> Reddit), ONE model.
# Computes the raw material for ASR_B, ASR_A, and TSR.
#
# Task B (activation, Reddit "post a review" tasks): 610 611 612 613 614
# Task A (poisoning-side stealth check, Shopping search tasks): 275 276 277 278 279
# Product id used in the payload:
set -e
cd ~/eTAMP_reproduction/webarena
source ~/eTAMP_reproduction/env.sh
source .venv/bin/activate

MODEL="gpt-4o-mini"
PID=2026
INSTR="agent/prompts/jsons/p_cot_id_actree_2s.json"
mkdir -p results/portion logs

echo "############ STEP 0: health check ############"
curl -s -o /dev/null -w "shopping(7770): %{http_code}\n" http://localhost:7770
curl -s -o /dev/null -w "reddit  (9999): %{http_code}\n" http://localhost:9999

echo "############ STEP 1: CLEAN run on Task B (for TSR baseline) ############"
rm -rf results/portion/clean
for t in 610 611 612 613 614; do
  python run.py --instruction_path $INSTR \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --result_dir results/portion/clean 2>&1 | tee -a logs/clean.log
done

echo "############ STEP 2: POISONED run on Task B (for ASR_B + TSR-under-attack) ############"
rm -rf results/portion/poison_B
for t in 610 611 612 613 614; do
  python run.py --instruction_path $INSTR \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --poison_pid $PID --result_dir results/portion/poison_B 2>&1 | tee -a logs/poison_B.log
done

echo "############ STEP 3: POISONED run on Task A / Shopping (for ASR_A stealth check) ############"
rm -rf results/portion/poison_A
for t in 275 276 277 278 279; do
  python run.py --instruction_path $INSTR \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --poison_pid $PID --result_dir results/portion/poison_A 2>&1 | tee -a logs/poison_A.log
done

echo "############ DONE. Now run:  python etamp/tally_metrics.py ############"
