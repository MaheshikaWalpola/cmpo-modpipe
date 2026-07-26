# R7 range-rule experiment — results note (2026-07-24)

Camera-ready material only. Nothing here touches the submitted paper.
Run by Claude (agent) on the frozen protocol in
`hiwi_t7_range_experiment_protocol.md`; script, bounds, and raw results are
in `modpipe/range_rule_experiment.py`, `evaluation/range_bounds.csv`, and
`evaluation/range_rule_results.json`.

## Setup

Bounds were derived from the clean E2 evaluation subgraph (seed 42, same
RNG stream as the harness) for all 34 observed properties present in it,
widened to [min - 0.5*span, max + 0.5*span], and frozen to CSV before any
seeded run. R7 is one SPARQL audit query in the TIER2_QUERIES style; the
harness functions were imported from `evaluate_v2.py`, not copied.

Sanity check (protocol step 3): R7 on the clean subgraph reports 0
violations, as required by construction.

## Fourth-condition detection row (seed 42, PYTHONHASHSEED=0)

| Error class | seeded | tier1 | tier1+2 | tier1+2+R7 |
|---|---|---|---|---|
| T1 missing value | 50 | 50 | 50 | 50 |
| T2 datatype | 50 | 50 | 50 | 50 |
| T3 negative value | 50 | 0 | 50 | 50 |
| T4 dangling FoI | 50 | 50 | 50 | 50 |
| T5 plausible swap | 100 | 0 | 0 | **23** |
| T6 undeclared property | 50 | 0 | 50 | 50 |
| T7 unit scale | 50 | 0 | 0 | **25** |
| T8 duplicate wafer | 4 | 0 | 4 | 4 |

The tier1 and tier1+2 columns reproduce `results_v2.json` exactly, which
confirms the rerun used the same subgraph and mutation stream as the
released harness.

## Comparison with the pre-registered expectation

Expected: T7 flips to detected, T5 stays undetected, all other rows
unchanged. Two of three parts held; two deviations are findings.

1. **T7 flips, but only partially: 25 of 50.** The 6.895x scaling cannot
   move a zero: 20 of the 50 sampled pressure values were exactly 0 psi
   (idle zones are common in the PHM logs), and 0 x 6.895 = 0 remains
   inside every window. The remaining 5 misses are small nonzero values
   whose scaled result stays under the widened upper bound (for example
   CenterAirBagPressure: clean max 137.8, upper bound 206.7, so any value
   below about 30 psi survives scaling). Diagnostic check: exactly the 25
   seeded observations whose post-mutation value lies outside their frozen
   window are the 25 detected — R7 catches everything it can see, and
   what it cannot see is a property of the error model, not of the rule.
2. **T5 does not stay at zero: 23 of 100 detected.** The protocol's
   rationale ("swapped values are inside the ranges by construction")
   holds only for swaps within one property. The harness swaps values
   across the whole pressure family, so a value can land in a different
   property whose window it violates. R7 therefore catches cross-property
   swaps as a side effect. This is a deviation from the prediction and a
   positive one.
3. All other rows are unchanged, as predicted.

## Reproducibility finding (applies to the harness, not the paper)

The harness samples T3/T5/T7 targets by RNG-shuffling rdflib SPARQL result
rows, and the ORDER of those rows depends on the Python process hash seed.
The submitted paper's E2 numbers are immune: its detections are 0, 50, or
all-seeded for every class, whichever observations get sampled. R7
detection counts are not immune: across hash seeds tried this session, T7
ranged 25-29 and T5 18-27 (mechanism identical throughout; only the sample
changes). The script now pins PYTHONHASHSEED=0 and re-executes itself, so
the numbers above are stable run-to-run; the canonical values are the
pinned ones. Worth remembering for any future experiment that, unlike the
published ones, is sensitive to which observations get sampled.

## Honesty cautions for the eventual write-up (from the protocol, confirmed)

The bounds are derived from the same clean data the errors are seeded
into, so R7 is a data-derived screen, not an engineering-spec constraint.
Real operating windows from process engineers replace these bounds later.
R7 was designed after the submitted paper's taxonomy was frozen and must
be reported as an extension, never merged into Table 2's original
conditions. Add to that the two findings above: a fair write-up reports
T7 detection as partial with the zero-value floor stated, and reports the
T5 side catch as a cross-property effect, not as detection of true
same-range swaps.

Provenance: all numbers from `modpipe/range_rule_experiment.py` at seed 42,
PYTHONHASHSEED=0, rdflib 7.x / pyshacl on the released kg_cmpo_v2.0.2.ttl
and cmpo-v2.0.2.ttl, run 2026-07-24. Nothing in the submitted paper was
modified.
