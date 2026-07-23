# CMPO + ModPipe

The CMP Process Ontology (CMPO) and ModPipe, a modular pipeline that turns
chemical mechanical planarization (CMP) process tables into a SHACL-validated
knowledge graph. This repository is the artifact accompanying the paper
*"From Silos to Semantics: CMPO and a Validated Knowledge Graph for Chemical
Mechanical Planarization Process Data"* (submitted to SemIIM 2026,
co-located with ISWC 2026).

## Contents

| Folder | What it holds |
|---|---|
| `ontology/` | CMPO v2.0.2 (Turtle, 165 classes, SOSA/SSN backbone, QUDT-aligned units, changelog in the file header) and its specification document |
| `mapping/` | The declarative column-to-ontology mapping specification for the PHM 2016 CMP dataset (28 rows: role, CMPO term, mechanism, datatype, canonical unit per column) |
| `synthetic/` | The synthetic completion table (observations and entities for CMPO classes that the PHM tool does not log, with per-class coverage declaration; identifiers are visibly synthetic) |
| `modpipe/` | The pipeline (`modpipe.py`: ingestion, alignment, normalization, RDF generation) and the evaluation harness (`evaluate_v2.py`: gate run, seeded-error study, competency questions) |
| `shapes/` | The two-tier validation gate: `shapes_core.ttl` (node-local core constraints) and `shapes_sparql.ttl` (graph-level semantic rules) |
| `kg/` | The generated knowledge graph (252,873 triples; derived from the PHM 2016 test data plus the synthetic sample) |
| `evaluation/` | Raw results of the paper's experiments (`results_v2.json`), generation statistics, and source-data profile |
| `legacy_audit/` | The E0 audit of an earlier deployment (runs against the [KGPortal](https://github.com/MaheshikaWalpola/KGPortal) repository; see below) |
| `data/` | Empty by design; place the PHM 2016 CSVs here (see next section) |
| `docs/` | Notes on data scope (`DATA_SUFFICIENCY.md`) and on reading the evaluation scripts and results (`EVALUATION_NOTES.md`) |

## Data

The real process data is the wafer CMP dataset of the
[2016 PHM Society Data Challenge](https://phmsociety.org/conference/annual-conference-of-the-phm-society/annual-conference-of-the-prognostics-and-health-management-society-2016/phm-data-challenge-4/).
It is not redistributed here; download it from the PHM Society and place
`CMP-test-000.csv` and `CMP-test-removalrate.csv` in `data/`. The knowledge
graph in `kg/` is a derived artifact built from that dataset and from the
synthetic completion sample.

## Reproducing the paper's numbers

```bash
pip install -r requirements.txt
# run from the repository root
python3 modpipe/modpipe.py       # stages 1-4: profile, align, normalize, generate (about 17 s)
python3 modpipe/run_all.py       # or end-to-end: generation, two-tier gate, persistence with the
                                 # validation report written next to the graph (modpipe/out/)
python3 modpipe/evaluate_v2.py   # gate run, seeded-error study (seed 42), competency questions (about 80 s)
```

The external-baseline studies require the published SOSA-SHACL suite:
`git clone https://github.com/KnowWhereGraph/KWG-SHACL` in the repository
root, then run `python3 modpipe/baseline_sosashacl.py` (as-published and
type-materialized conditions, about 3 min) and
`python3 modpipe/punning_fix_baseline.py` (the punning-fix condition).
`python3 modpipe/multiseed_e2.py` repeats the seeded-error study under
additional seeds. Committed results for all runs are in `evaluation/`.

`evaluate_v2.py` evaluates the freshly generated graph
(`modpipe/out/kg_unvalidated.ttl`) when a generator run precedes it, and
otherwise the committed graph in `kg/`; the two are identical for the
released inputs. It writes `out/results_v2.json`; the committed copy in
`evaluation/` is the run reported in the paper. Seeding uses a fixed random
seed, so the detection table reproduces exactly.

The legacy audit (`legacy_audit/run_evaluation.py`) documents the E0
experiment of the paper: it validates the artifacts of an earlier deployment
and measures the vacuity of its shape suite. To run it, clone
[KGPortal](https://github.com/MaheshikaWalpola/KGPortal) and execute the
script from that repository's root; the committed `results.json` is the run
reported in the paper.

## Versioning

Ontology files carry their version in the file name (`ontology/cmpo-v2.0.2.ttl`),
and each repository release is tagged with the matching version (`v2.0.2`), so a
tag always pins one consistent ontology + knowledge graph + results state. The
version reported in the SemIIM 2026 paper is `v2.0.2`. The full history,
including the pre-release Schema v1 and v2.0 stages, is in `CHANGELOG.md`; how
the ontology was built is in `CONSTRUCTION_HISTORY.md`.

## Licenses

Code (`modpipe/`, `legacy_audit/`) is under the MIT license. The ontology,
shapes, mapping specification, synthetic table, and generated knowledge graph
are under CC BY 4.0. See `LICENSE`.

## Citing

See `CITATION.cff`. Citation details will be updated once the paper appears
on CEUR-WS.org.

## Acknowledgments

Developed in the WiProFlex project, funded by the European Social Fund Plus
(ESF+) and the Free State of Saxony under grant 100693458. The ontology was
drafted with large language model assistance and revised by the authors; the
construction history is documented in `CONSTRUCTION_HISTORY.md`, and the paper
contains the corresponding declaration.
