# evaluation/ — file map

Raw results of every experiment reported in the SemIIM 2026 paper. Files under
a released tag are never edited, only reproduced. The portal compilation study
(E4) has its own folder, `../portal_study/`.

## E1–E3: gate run, seeded-error study, competency questions

| File | What it is |
|---|---|
| `results_v2.json` | E1–E3 results as reported: gate run, seeded-error study (seed 42), competency questions. Written by `modpipe/evaluate_v2.py`. |
| `multiseed_e2_results.json` | The seeded-error study repeated under seeds 7 and 123; both reproduce the seed-42 detection counts exactly. |
| `baseline_sosashacl_results.json` | The external SOSA-SHACL baseline, as published and with types materialized. |
| `baseline_punningfix_results.json` | The punning-fix condition: each punned parameter class additionally asserted as a `sosa:ObservableProperty` individual. |
| `generation_stats.json` | Pipeline generation statistics. |
| `profile.json` | Source-data profile of the PHM CSVs. |

## R7: data-derived range bounds (Table 3)

| File | What it is |
|---|---|
| `range_bounds.csv` | The per-property intervals, derived from the clean evaluation subgraph and frozen before any seeded run (34 properties). |
| `range_rule_results.json` | Detection with the added R7 condition: T7 25 of 50, T5 23 of 100, all other rows unchanged, zero clean-graph violations. |
| `range_rule_transfer.json` | How often the same bounds fire on clean data they were not derived from: held-out observations of the same wafers, and leave-one-wafer-out. |
| `range_rule_sensitivity.json` | Sweeps of the two free parameters (seeding size, widening constant) plus the full census over every eligible observation. |
| `range_rule_note.md` | Setup, comparison against the frozen predictions, the zero-value T7 finding, the hash-seed reproducibility finding, and the cautions carried into the paper. |
| `../modpipe/range_rule_experiment.py` | The experiment (pins `PYTHONHASHSEED=0` and re-executes itself). |
| `../modpipe/range_rule_transfer.py`, `../modpipe/range_rule_sensitivity.py` | The transfer study and the sweep. |

The bounds are derived from the same subgraph the errors are seeded into, so
they are a proof of mechanism rather than a validated operating range. The
transfer study measures how far that reaches, and the answer is: not far enough
for an unseen wafer. Operating limits stated by process engineers, rather than
inferred from the data, are the next step for this rule and are not part of
this release.

## Conventions

- Files pinned by a release are listed in `../SHA256SUMS`.
- Every experiment records its inputs and its RNG seeds inside its own results
  file or note.
- Prediction first: expected outcomes are written down and committed before a
  run, and deviations are reported rather than tuned away. Both R7 deviations
  in `range_rule_note.md` are reported this way.
