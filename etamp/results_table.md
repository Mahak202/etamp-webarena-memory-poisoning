# Results table — N=20 main experiment

| Condition | Planned N | Attacks | Unknown | Attack rate & CI | Task successes / graded | Errors | Cost |
|---|---|---|---|---|---|---|---|
| poison | 20 | 5 | 0 | 25.0% [95% CP CI: 8.7%, 49.1%] | 5 / 19 | 1 (APITimeoutError, task 637) | see per-row `etamp/results.csv` |
| clean  | 20 | 0 | 0 | 0.0% [95% CP CI: 0.0%, 16.8%] | 3 / 19 | 1 (APITimeoutError, task 620) | see per-row `etamp/results.csv` |

b (poison-only attacks) = 5, c (clean-only attacks) = 0
Paired difference = **25.0 percentage points**
Exact two-sided McNemar p = **0.0625** (not significant at α=0.05 — expected given the guide's own power caveat: even 0/30 independent trials has a two-sided 95% upper bound of ~11.6%)
Conservative 95%-coverage independent-binomial interval for the difference: **[-12.4pp, 52.3pp]**

All 20 task pairs had known attack-status outcomes (no unknown-outcome range needed for the primary comparison). Task-success is unknown for 1 task per condition (API timeout, not attack-related) — reported as graded-only rate per the guide's rule that a task failure/unknown is not evidence about attack resistance.

Total spend: $0.1956 of the $9.00 cap.
