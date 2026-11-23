# eTAMP: Memory-Poisoning Attacks on WebArena Web Agents

Code for the thesis experiments on triggered memory-poisoning attacks against an
LLM-driven web agent built on [WebArena](https://github.com/web-arena-x/webarena).
An attacker plants a poisoned note during one task (Shopping site); later, during
an unrelated task (Reddit site), the agent retrieves that note from memory and the
payload attempts to make it navigate to an attacker-controlled URL. We measure how
often the attack fires (ASR_B) under several payload framings, with and without
added execution noise ("chaos"), and in both attack directions.

This repository accompanies a manuscript currently under review. It is provided so
reviewers and readers can see exactly how the experiments were run and how attack
outcomes were detected, per the paper's data and code availability statement.

## What this is

- `agent/`, `browser_env/`, `llms/`, `run.py`, `requirements.txt` — a modified fork
  of WebArena's agent/environment harness. Diffs from upstream add: a pluggable
  memory-poisoning injection path, a budget/rate-limiting wrapper for the OpenAI
  client, and tokenizer fixes needed for local (Ollama) model support.
- `etamp/` — the experiment harness built on top of the WebArena fork:
  - `inject.py` — the poisoned-memory payload definitions (one function per
    framing: urgency-authority, fear, trust, fatigue, consensus, helpfulness,
    reciprocity, scarcity).
  - `run_<condition>_100.py` — drivers that launch a 100-task sweep for a given
    payload/condition.
  - `tally_<condition>_100.py`, `build_step_matrix_<condition>.py`,
    `build_results.py` — outcome detection: these parse each run's action log and
    determine whether the malicious `goto` actually fired (`find_attack()`), not
    just whether the model's reasoning text mentioned it.
  - `chaos_monkey.py` — the optional action-level noise injector used for the
    "chaos on" robustness condition.
  - `<condition>_100_{results,run_log,step_matrix,summary}.csv/.txt` — the
    aggregated outcome data for every reported condition (this is the actual
    evidence behind the paper's numbers; raw per-task browser traces are not
    included, see "What is not included" below).
  - Files suffixed `_CORRUPTED_<reason>` (e.g. `_CORRUPTED_networkoutage`,
    `_CORRUPTED_creditexhausted`) are failed run attempts kept for transparency;
    they are explicitly excluded from the reported results and superseded by a
    clean rerun of the same condition.
- `config_files/`, `webarena_task_master.csv`, `task_site_mapping.csv` — WebArena's
  public benchmark task definitions and the Shopping/Reddit task subset used here.
- `environment_docker/` — WebArena's standard site-hosting Docker setup (unmodified
  from upstream).

## Setup

1. **Clone and create a virtual environment:**
   ```bash
   git clone <this-repo-url>
   cd <repo-dir>
   python3 -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   playwright install
   ```

2. **Stand up the WebArena sites.** Follow upstream WebArena's
   [environment setup instructions](https://github.com/web-arena-x/webarena/tree/main/environment_docker)
   to launch the Docker containers for the Shopping and Reddit sites used by these
   experiments (this repo's `environment_docker/` is the unmodified upstream
   config). Set the resulting site URLs via the environment variables WebArena
   expects (e.g. `SHOPPING`, `REDDIT`) before running anything.

3. **Set your OpenAI API key** (never commit this):
   ```bash
   export OPENAI_API_KEY=sk-...
   ```

4. **Run a sweep**, e.g. the fear-framing condition:
   ```bash
   cd etamp
   python run_fear_100.py        # runs the 100-task poisoned sweep
   python tally_fear_100.py      # computes ASR_B + 95% CI from the run output
   python build_step_matrix_fear.py   # per-step action breakdown
   ```
   Each `run_<condition>_100.py` / `tally_<condition>_100.py` pair follows the same
   pattern; see `inject.py` for the full list of payload framings and
   `run.py --poison_style` for how a condition is dispatched into the agent loop.

## What is NOT included, and why

- **`downloads/`** (WebArena's offline Wikipedia dump, `.zim` format, ~89GB) —
  a large public data file, not experiment-specific. Fetch it yourself per
  upstream WebArena's setup instructions.
- **`results/`** (~5.2GB) and **`logs/` / `log_files/`** — raw per-task browser
  traces, rendered HTML snapshots, and run logs for every experiment. These are
  far too large for a git repository and are not needed to verify the reported
  numbers: the aggregated CSVs in `etamp/` (`*_results.csv`, `*_step_matrix.csv`,
  `*_summary.txt`) are the data actually underlying every figure and statistic in
  the paper. Available from the authors on reasonable request.
- **`etamp/spend_ledger.json`** — an internal per-call OpenAI token/cost ledger
  used for local budget tracking during development. It is operational bookkeeping
  tied to the authors' own API usage, not experiment outcome data, and is excluded
  as out of scope for a public release.
- **API keys, credentials, and browser auth/session state** (`.env`, `.venv/`,
  `.auth/*`) — never present in this repository; all credentials are supplied at
  runtime via environment variables (see Setup, step 3) and are gitignored.

## Attribution

Built on [WebArena](https://github.com/web-arena-x/webarena) (Zhou et al.), used
and modified under its original license for academic research purposes.
