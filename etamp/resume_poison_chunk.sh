#!/bin/bash
# Resume the poisoned phase of repro_baseline100_gemma3_4b.sh for a specific
# subset of task IDs (passed as args), appending to the existing result dir/log.
cd ~/eTAMP_reproduction/webarena
source ~/eTAMP_reproduction/env.sh
export OPENAI_API_BASE="http://localhost:11434/v1"
source .venv/bin/activate

MODEL="gemma3:4b"
PID=2026
STEPS=15
INSTR="agent/prompts/jsons/p_cot_id_actree_2s.json"

for t in "$@"; do
  next=$((t+1))
  echo "=== task $t ===" | tee -a logs/gemma3_4b_baseline100_poison.log
  python run.py --instruction_path "$INSTR" --max_steps $STEPS \
    --test_start_idx "$t" --test_end_idx "$next" \
    --model "$MODEL" --poison_pid $PID --result_dir results/gemma3_4b_baseline100/poison_B \
    2>&1 | grep -E "\[Intent\]|\[Result\]|Average score|Traceback|Error" | tee -a logs/gemma3_4b_baseline100_poison.log \
    || echo "[skip $t]" | tee -a logs/gemma3_4b_baseline100_poison.log
done
echo "@@@ CHUNK DONE @@@"
