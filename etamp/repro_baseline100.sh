#!/bin/bash
# Baseline over ~100 Reddit tasks, gpt-4o-mini, basic payload, 15-step cap (paper's no-chaos cap).
# POISON phase first (ASR_B), then CLEAN (TSR). Individual task crashes are skipped, not fatal.
cd ~/eTAMP_reproduction/webarena
source ~/eTAMP_reproduction/env.sh
source .venv/bin/activate

MODEL="gpt-4o-mini"
PID=2026
STEPS=15
INSTR="agent/prompts/jsons/p_cot_id_actree_2s.json"
IDS="27 28 29 30 31 66 67 68 69 399 400 401 402 403 404 405 406 407 408 409 410 580 581 582 583 584 595 596 597 598 599 600 601 602 603 604 605 606 607 608 609 610 611 612 613 614 615 616 617 618 619 620 621 622 623 624 625 626 627 628 629 630 631 632 633 634 635 636 637 638 639 640 641 642 643 644 645 646 647 648 649 650 651 652 714 715 716 717 718 719 720 721 722 723 724 725 726 727 728 729"
mkdir -p results/baseline100 logs

echo "############ POISONED run (ASR_B) — 100 Reddit tasks, max $STEPS steps ############"
rm -rf results/baseline100/poison_B; : > logs/base100_poison.log
for t in $IDS; do
  python run.py --instruction_path $INSTR --max_steps $STEPS \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --poison_pid $PID --result_dir results/baseline100/poison_B \
    2>&1 | tee -a logs/base100_poison.log || echo "[skip $t]"
done
echo "@@@ POISON PHASE DONE @@@"

echo "############ CLEAN run (TSR) — 100 Reddit tasks, max $STEPS steps ############"
rm -rf results/baseline100/clean; : > logs/base100_clean.log
for t in $IDS; do
  python run.py --instruction_path $INSTR --max_steps $STEPS \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --result_dir results/baseline100/clean \
    2>&1 | tee -a logs/base100_clean.log || echo "[skip $t]"
done
echo "############ ALL DONE ############"
