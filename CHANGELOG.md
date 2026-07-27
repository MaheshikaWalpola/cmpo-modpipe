# Changelog

Versioning covers two things at once: the CMPO ontology (file names carry the
version, e.g. `ontology/schema_v2.1.ttl`) and this repository as the paper's
artifact (git tags, e.g. `v2.1`). The two move together: a tagged repository
state contains exactly one ontology version, the knowledge graph generated
from it, and the evaluation results produced against that pair.

## Unreleased (branch `camera-ready/extensions`)

Post-submission extension experiments; see `evaluation/README.md` for the
per-file status. None of this changes the tagged v2.0.2 artifact.

- R7 data-derived range-rule pilot: frozen per-property bounds, seeded-error
  rerun with a fourth condition (T7 25/50, T5 23/100, clean graph 0
  violations), results note with preregistration comparison and the
  Python-hash-seed reproducibility finding.
- R7e preregistration draft and expert-limits template for the non-circular
  rerun with expert-stated operating limits.
- Graph-grounded 20-question suite: hand-written SHACL and SPARQL audit
  versions, run against the released graph; all four preregistered firings
  confirmed exactly, sixteen statements pass non-vacuously.
- Repository housekeeping: `.gitignore`, `evaluation/README.md`.

## v2.1.2 — 2026-07-27 (artifact revision; version reported in the SemIIM 2026 paper)

Artifact revision only. The ontology and the knowledge graph are byte-identical
to v2.1 / v2.1.1; no term was added, removed or renamed, and no reported
detection count changed.

Evaluation:
- Added `modpipe/range_rule_transfer.py` and `evaluation/range_rule_transfer.json`.
  The R7 detection counts in `range_rule_results.json` are measured on the same
  4,000-observation subgraph the bounds were derived from, so every uncorrupted
  value lies inside them by construction. The new script measures the separate
  question an adopter would ask: how often the same bounds fire on clean data
  they were not derived from. Two conditions, both false-positive rates:
  held-out observations of the same four wafers (11 of 21,278, 0.05%), and
  leave-one-wafer-out (pooled 2,137 of 25,198, 8.5%; per wafer 0.0%, 0.02%,
  5.5%, 26.3%). The paper reports both in Table 3.
- Re-ran `modpipe/range_rule_experiment.py` at seed 42 with `PYTHONHASHSEED=0`
  on the v2.1 pair. Output identical to the recorded run: T5 23 of 100, T7 25
  of 50, all other rows unchanged. This confirms the paper's Table 3 against
  the released harness rather than against a working copy.
- Retitled the header of `range_rule_experiment.py`. It previously read
  "camera-ready material only, not part of the submitted paper"; R7 is now
  reported as Table 3 of the submitted paper, as an extension to the frozen
  Table 2 taxonomy and never merged into Table 2's conditions.

Note on the R7 denominators, recorded here because the paper now states them:
20 of the 50 T7 seedings fell on values that were exactly zero, and the 6.895
scale operator leaves a zero unchanged, so those 20 mutations produce a graph
identical to the clean graph and no suite could detect them. Over the 30
seedings that alter a value the bounds detect 25. On the T5 side the operator
swaps values across the whole pressure family, so the 23 it catches are
cross-property accidents rather than same-range swaps.

Nothing else in the repository changed. The frozen tags `v2.0.2`, `v2.0.2.1`,
`v2.1` and `v2.1.1` are unchanged; published tags are never rewritten.

## v2.1.1 — 2026-07-26 (artifact revision; ontology unchanged at v2.1)

Competency-question repairs, so that the released harness matches the suite the
paper reports. The ontology and the knowledge graph are unchanged.

- CQ12 traversed `cmpo:Pad`, a class CMPO does not declare, and returned zero.
  The zero measured the query, not the graph. It now traverses `cmpo:Consumable`,
  under which pad and conditioning consumables sit, and returns the three
  synthetic pad and conditioner entities.
- CQ7 reported only the count for wafers typed exactly `cmpo:Wafer`. It now
  returns both scopes in one row: zero of the four PHM wafers, three of the
  seven instances of `cmpo:Wafer` and its subclasses.
- CQ3 was titled "carrier-head pressure zones" but the query returns every
  subclass of `cmpo:Pressure`, including chamber pressure, contact pressure and
  downforce. Retitled to "pressure-related parameter classes".
- CQ6 and CQ8 provenance labels now state their combined scope (PHM+synthetic
  and ontology+synthetic respectively) rather than implying a single source.
- `evaluation/results_v2.json` regenerated. E1 and E2 are byte-identical in
  every count; the only change is CQ12 moving from 0 rows to 3.
- `SHA256SUMS` refreshed.

## v2.1 — 2026-07-26 (ontology version reported in the SemIIM 2026 paper)

Renumbering and two corrections. No ontology term was added, removed or
renamed relative to v2.0.2, so any graph built against v2.0.2 remains valid.

Ontology:
- Renumbered 2.0.2 to 2.1 and renamed `ontology/cmpo-v2.0.2.ttl` to
  `ontology/schema_v2.1.ttl`. The 2.0.2 patch had declared a new object
  property (`cmpo:madeOnPlatform`), which under semantic versioning is a minor
  change rather than a patch; the number now reflects that. `owl:versionInfo`
  and `dcterms:modified` updated accordingly, and a changelog entry (R1) added
  to the file header. Logical content verified identical to 2.0.2 triple by
  triple: 1,383 triples, 165 classes, 54 object properties, 63 datatype
  properties.

Knowledge graph:
- Renamed `kg/kg_cmpo_v2.0.2.ttl` to `kg/kg_cmpo_v2.1.ttl`.
- Corrected two malformed subject IRIs. The SPC-limit and process-window
  triples had their subjects written as
  `<…/cmpo/instance#cmpo:AverageRemovalRate>` and
  `<…/cmpo/instance#cmpo:RetainingRingPressure>`: the prefixed names had been
  serialised as relative IRIs and resolved against the instance namespace, so
  both attached to nodes with no meaning. Subjects are now the parameter
  classes `cmpo:AverageRemovalRate` and `cmpo:RetainingRingPressure`, as
  `cmpo:hasSPCLimit` and `cmpo:hasProcessWindow` declare (domain
  `cmpo:CMPParameter`). Triple count unchanged at 252,873; exactly two triples
  differ. No competency question queried those triples, so no reported result
  changes.

Validation:
- Re-validated the renamed pair. Tier 1 reports the same four findings as
  v2.0.2 (three synthetic metrology tools without a tool identifier, one
  synthetic metrology step without a stage label); tier-2 rules report zero.
  Detection results for every experiment are unchanged.

Naming and tooling:
- One version number now runs across every artifact: `schema_v2.1.ttl`,
  `kg_cmpo_v2.1.ttl`, tag `v2.1`, paper `silos_semiim2026_v2.1.tex`. The rule,
  the version history and the words banned from filenames are documented in
  the working folder's `VERSIONING.md`.
- The `_find()` candidate lists in `modpipe/` now try the v2.1 filenames first
  and keep the v2.0.2 names as fallbacks, so the scripts run against either
  layout.
- `SHA256SUMS` refreshed; `CITATION.cff` version set to 2.1.

Note on the frozen tags: `v2.0.2` and `v2.0.2.1` are unchanged and still hold
the original filenames and the two malformed IRIs. Published tags are never
rewritten.

## v2.0.2 — 2026-07-23 (patch; superseded by v2.1)

Ontology:
- Declared `cmpo:madeOnPlatform` as an object property. Earlier KG builds
  used this term under a `sosa:` prefix, but it is not part of the SOSA
  vocabulary and was never declared; it is now a properly declared CMPO term
  (object properties 53 -> 54, ontology triples 1,377 -> 1,383).

Knowledge graph:
- Regenerated with the corrected term (25,258 platform triples renamed;
  252,873 triples total).

Evaluation:
- All experiments rerun against the corrected ontology/KG pair. Detection
  results are unchanged; the committed JSON files in `evaluation/` are from
  these reruns.
- Added the multi-seed repetition of the seeded-error study
  (`modpipe/multiseed_e2.py`, results in `evaluation/multiseed_e2_results.json`):
  seeds 7 and 123 reproduce the seed-42 detection counts exactly.
- Added the punning-fix baseline condition
  (`modpipe/punning_fix_baseline.py`).
- Corrected the CQ3 query translation: the canonical unit of a pressure
  zone is declared on the `cmpo:Pressure` family, which the original query
  did not reach; the corrected query binds it (row counts unchanged).
- Added `modpipe/run_all.py`, a single end-to-end command (generation,
  two-tier gate, persistence with the validation report beside the graph),
  and pinned exact dependency versions in `requirements.txt`.
- Script repairs after an external reproduction attempt: two baseline
  scripts had syntax errors introduced during the repository-relative path
  retrofit (a comment swallowed a closing parenthesis); the three auxiliary
  scripts now locate the harness at `modpipe/evaluate_v2.py` from the
  repository root; `evaluate_v2.py` creates `out/` before writing and
  prefers the freshly generated graph over the committed one. All six
  released scripts were then re-verified from a fresh clone: every
  committed result reproduces exactly.
- Added a CI workflow (`.github/workflows/ci.yml`), `SHA256SUMS`, and
  `CODE_OF_CONDUCT.md`.

Repository:
- All scripts run from a fresh clone with repository-relative paths.
- Added `CONSTRUCTION_HISTORY.md` (how the ontology was built, including the
  role of large language model assistance and the earlier BFO-aligned
  Schema v1, which is preserved as a future alignment source, not discarded).

## v2.0.1 — 2026-07-22 (first public release)

- Initial release of the artifact: CMPO v2.0.1 (165 classes, 53 object
  properties, 63 datatype properties), the ModPipe pipeline, the two-tier
  SHACL gate, the declarative mapping specification, the synthetic completion
  table, the generated knowledge graph, and the evaluation harness with
  committed results.
- External-baseline study against the published SOSA-SHACL suite
  (`modpipe/baseline_sosashacl.py`).
- Legacy audit (E0) of an earlier deployment (`legacy_audit/`).

## v2.0 — 2026 (internal, not released)

- Rebuild of the ontology on a SOSA/SSN observation backbone with
  QUDT-aligned units and OWL 2 punning for parameter classes, replacing the
  earlier BFO-aligned draft. Iterated internally as v2.0/v2.0.1 during paper
  preparation; the first state published here is v2.0.1.

## Schema v1 — 2025 (predecessor, not in this repository)

- First ontology draft, produced with large language model assistance using
  BFO as top-level ontology. Preserved as the source for a planned BFO
  alignment module; see `CONSTRUCTION_HISTORY.md`.
