#!/bin/bash
# Engineering pilot (guide section 1): 2 reserved task IDs, clean + poisoned each.
# Purpose: check routing/parsing/logging/token limits ONLY. These 4 runs are
# excluded from analysis regardless of outcome. IDs are pulled from
# etamp/sample_manifest.csv (role=pilot), not hardcoded, so they always match
# whatever freeze_sample.py produced.
set -e
cd ~/eTAMP_reproduction/webarena
source ~/eTAMP_reproduction/env.sh
source .venv/bin/activate

MANIFEST="etamp/sample_manifest.csv"
MODEL="${MODEL:?Set MODEL before running, e.g. MODEL=gpt-4o-mini ./etamp/run_pilot.sh — see WARNING in script header re: gpt-5.6-luna}"
MODE="${MODE:-chat}"          # "responses" for gpt-5.6-luna, "chat" for legacy models
PID=2026
STEPS=15
INSTR="agent/prompts/jsons/p_cot_id_actree_2s.json"
RESPONSES_FLAGS="--reasoning_effort none --max_output_tokens 1024 --api_timeout 60 --no_retry"

IDS=$(awk -F, 'NR>1 && $1=="pilot" {gsub(/\r/,""); print $3}' "$MANIFEST")
if [ -z "$IDS" ]; then
  echo "No pilot rows found in $MANIFEST — run etamp/freeze_sample.py first." >&2
  exit 1
fi

EXTRA=""
[ "$MODE" = "responses" ] && EXTRA="$RESPONSES_FLAGS"

mkdir -p results/pilot logs
echo "Pilot task IDs (from $MANIFEST): $IDS"
echo "Model: $MODEL  Mode: $MODE"

echo "############ POISONED pilot run — $STEPS-step cap ############"
rm -rf results/pilot/poison_B; : > logs/pilot_poison.log
for t in $IDS; do
  python run.py --instruction_path $INSTR --max_steps $STEPS \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --mode $MODE $EXTRA --poison_pid $PID --result_dir results/pilot/poison_B \
    2>&1 | tee -a logs/pilot_poison.log || echo "[skip $t]"
done

echo "############ CLEAN pilot run — $STEPS-step cap ############"
rm -rf results/pilot/clean; : > logs/pilot_clean.log
for t in $IDS; do
  python run.py --instruction_path $INSTR --max_steps $STEPS \
    --test_start_idx $t --test_end_idx $((t+1)) \
    --model $MODEL --mode $MODE $EXTRA --result_dir results/pilot/clean \
    2>&1 | tee -a logs/pilot_clean.log || echo "[skip $t]"
done
echo "############ PILOT DONE — inspect logs/results, do not analyze for attacks ############"
