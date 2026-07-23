# Changelog

Versioning covers two things at once: the CMPO ontology (file names carry the
version, e.g. `ontology/cmpo-v2.0.2.ttl`) and this repository as the paper's
artifact (git tags, e.g. `v2.0.2`). The two move together: a tagged repository
state contains exactly one ontology version, the knowledge graph generated
from it, and the evaluation results produced against that pair.

## v2.0.2 — 2026-07-23 (version reported in the SemIIM 2026 paper)

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
