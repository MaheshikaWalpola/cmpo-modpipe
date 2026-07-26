# Preregistration draft: R7e, the expert-limit range rule

Status: DRAFT prepared 2026-07-24 for the camera-ready extension. Nothing
here touches the submitted paper, its frozen taxonomy, or Table 2. This
document becomes a preregistration only after Maheshika fills every
"TO FREEZE" item and commits the file; until then it is a template.

Drafted by Claude (agent) on Maheshika's instruction. The experimental
design follows the two prior R7 runs of 2026-07-24; the change is the
source of the bounds.

## Motivation

The first R7 experiment used bounds derived from the same clean subgraph
into which errors were seeded. It detected 25/50 T7 seeds and 23/100 T5
seeds with zero clean-graph violations, but the derivation is circular: the
screen was fitted to the data it screens. R7e replaces those bounds with
operating limits stated independently by people who know the machine. A
HiWi and a user of a CMP machine confirmed the rewritten constraint set and
supplied numeric limits on 2026-07-24 (per Maheshika; the values themselves
are recorded in `expert_limits_template.csv` once filled).

## Frozen before executing seeded errors

1. Limits: `evaluation/expert_limits.csv`, produced by filling
   `expert_limits_template.csv`. One row per observed property; properties
   without an expert limit are marked `no_limit` in the notes column and
   are excluded from R7e (coverage is reported, not hidden). Each filled
   row names its source (tool specification, machine user, or process
   engineer), the person who confirmed it, and the date. The file is
   committed and its SHA-256 recorded here before any seeded run.
   TO FREEZE: the filled file and its hash.
2. Harness repairs, applied and committed before the run:
   a. T7 samples only observations whose numeric value is non-zero, and
      records both selected subjects and effective graph changes.
   b. Candidate collections inside `seed()` and `pressure_obs()` are
      sorted before the RNG is applied, so seed 42 selects the same
      observations in every process. PYTHONHASHSEED remains pinned to 0.
   TO FREEZE: the commit hash of the repaired harness.
3. Data: the clean 4,000-observation E2 subgraph from
   `evaluate_v2.build_subgraph`, RNG seed 42.
4. R7e rule: flag an observation whose numeric result lies outside the
   expert interval for its observed property. Same SPARQL audit style and
   same differential detection criterion as the released harness.
5. Clean-graph pass: unlike the data-derived R7, zero clean violations is
   NOT required by construction. Real observations may legitimately fall
   outside stated operating limits. The clean violation count is recorded
   as a primary result. Any clean violations do not distort detection
   counts because the differential criterion subtracts the baseline.

## Predictions (TO FREEZE before the run — Maheshika writes these)

- P1. T7 detection under tier 1 + tier 2 + R7e, out of the seeded total
  and out of the effectively changed total: ____
- P2. T5 detection under tier 1 + tier 2 + R7e: ____
- P3. Clean-graph R7e violation count: ____
- P4. Rows T1–T4, T6, T8: ____
- Any deviation is a result and is reported without post-hoc tuning.

## Reporting commitments

- Report R7e coverage: how many of the 34 observed properties have expert
  limits, and which were excluded.
- Report data-derived R7 and expert R7e side by side on the same repaired
  harness, so the circularity removal is visible as a comparison, not a
  replacement.
- Report clean-graph violations under R7e as findings about the data, with
  the flagged observations listed.
- Both prior implementations of the R7 pipeline produced identical numbers
  on the data-derived bounds; the rerun uses one canonical script and
  states which.

## What this experiment can and cannot claim

It can claim: detection rates of the released seeded-error operators under
an expert-informed range screen, with limits stated independently of the
evaluation data. It cannot claim: general coverage of the T7 error class
(the operators and their magnitudes are still author-chosen), or that the
expert limits are complete process specifications for the anonymized PHM
tool, whose true units are unknown (see the unit caution in the submitted
paper, Section 5).
