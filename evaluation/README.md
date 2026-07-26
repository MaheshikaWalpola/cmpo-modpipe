# evaluation/ — file map

Two kinds of files live here. The first six are the frozen results of the
submitted paper (tag `v2.0.2`); they are never edited, only reproduced. The
rest are extension experiments prepared after submission on the
`camera-ready/extensions` branch; each is labeled with its status.

## Released results (frozen with tag v2.0.2)

| File | What it is |
|---|---|
| `results_v2.json` | E1–E3 results reported in the paper: gate run, seeded-error study (seed 42), competency questions. Written by `modpipe/evaluate_v2.py`. |
| `multiseed_e2_results.json` | Seeded-error study repeated under seeds 7 and 123; reproduces the seed-42 detection counts. |
| `baseline_sosashacl_results.json` | External SOSA-SHACL baseline (as published and type-materialized). |
| `baseline_punningfix_results.json` | The punning-fix baseline condition. |
| `generation_stats.json` | Pipeline generation statistics. |
| `profile.json` | Source-data profile of the PHM CSVs. |

## Extension experiments (camera-ready branch; not part of tag v2.0.2)

### R7: data-derived range rule (status: pilot, completed 2026-07-24)

| File | What it is |
|---|---|
| `range_bounds.csv` | Frozen per-property intervals derived from the clean evaluation subgraph before any seeded run (34 properties). |
| `range_rule_results.json` | Detection results with the added R7 condition: T7 25/50, T5 23/100, other rows unchanged, 0 clean-graph violations. |
| `range_rule_note.md` | Results note: setup, prediction comparison, the zero-value T7 finding, the hash-seed reproducibility finding, honesty cautions. |
| `../modpipe/range_rule_experiment.py` | The experiment script (pins `PYTHONHASHSEED=0`). |

Two independent implementations of this experiment produced identical
numbers; the bounds are circular by construction (derived from the same
subgraph the errors are seeded into), which is why R7e below exists.

### R7e: expert-limit range rule (status: preregistration draft, awaiting limits)

| File | What it is |
|---|---|
| `range_rule_expert_prereg.md` | Preregistration draft for the non-circular rerun with expert-stated operating limits. Predictions are filled and frozen before the run. |
| `expert_limits_template.csv` | One row per observed property; to be filled with the limits confirmed by the process/machine experts, with source and sign-off columns. |

### Graph-grounded 20-question suite (status: completed 2026-07-24)

| File | What it is |
|---|---|
| `graph_grounded_shapes.ttl` | The 20 expert-confirmed validation statements as hand-written SHACL; every target verified non-vacuous against the released graph before writing. |
| `graph_grounded_sparql_audit.rq` | The same 20 checks as SPARQL audit queries (runnable directly in GraphDB Workbench). |
| `graph_grounded_results_2026-07-24.md` | Results: all four preregistered firings confirmed exactly (20/4/1/3), all sixteen other statements pass non-vacuously; plus the portal-compiler comparison findings. |

## Conventions

- Frozen files are listed in `../SHA256SUMS`; extension files are added to
  the checksum list only when a release tags them.
- Every experiment records its inputs by SHA-256 and its RNG seeds inside
  its own results file or note.
- Prediction-first: expected outcomes are written down and committed before
  a run; deviations are reported, not tuned away.
