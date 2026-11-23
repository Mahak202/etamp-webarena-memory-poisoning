import re, json, random, csv, pathlib

REPO = pathlib.Path(__file__).resolve().parent.parent
BASELINE_SH = REPO / "etamp" / "repro_baseline100.sh"
RAW_TASKS = pathlib.Path.home() / "webarena" / "config_files" / "test.raw.json"
OUT_CSV = REPO / "etamp" / "sample_manifest.csv"

N_FAMILIES = 30
SEED = 42

ids_line = re.search(r'IDS="([^"]+)"', BASELINE_SH.read_text()).group(1)
baseline_100 = sorted(int(x) for x in ids_line.split())
assert len(baseline_100) == 100, f"expected 100 baseline ids, got {len(baseline_100)}"

raw = json.loads(RAW_TASKS.read_text())
tmpl_by_id = {r["task_id"]: r["intent_template_id"] for r in raw}

families = {}
for tid in baseline_100:
    fam = tmpl_by_id[tid]
    families.setdefault(fam, []).append(tid)
for fam in families:
    families[fam].sort()

rng = random.Random(SEED)
family_ids = sorted(families)
chosen_families = rng.sample(family_ids, min(N_FAMILIES, len(family_ids)))

main_pairs = []
for fam in sorted(chosen_families):
    tid = rng.choice(families[fam])
    main_pairs.append((fam, tid))

main_ids = {tid for _, tid in main_pairs}
remaining = sorted(set(baseline_100) - main_ids)
pilot_ids = rng.sample(remaining, 2)

with OUT_CSV.open("w", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["role", "intent_template_id", "task_id"])
    for fam, tid in main_pairs:
        w.writerow(["main", fam, tid])
    for tid in pilot_ids:
        w.writerow(["pilot", tmpl_by_id[tid], tid])

print(f"families available in baseline-100: {len(family_ids)}")
print(f"N (main sample) = {len(main_pairs)}")
print("main task_ids:", sorted(main_ids))
print("pilot task_ids:", pilot_ids)
print(f"manifest written to {OUT_CSV}")
