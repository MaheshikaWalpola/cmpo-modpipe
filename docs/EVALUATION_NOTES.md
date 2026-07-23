# Evaluation notes (tied to the released scripts)

Reading guide for the scripts in `modpipe/` and the committed results in
`evaluation/`. Everything below is reproducible from a fresh clone plus the
two PHM CSVs (see the main README).

## Detection criterion

The seeded-error study is differential: a validation run on the clean
subgraph establishes a baseline set of results, each mutation is applied,
and a seeded node counts as detected when a new (focus node, result path,
constraint component) triple appears whose focus node contains the seeded
node's local name. The baseline scripts additionally log a "generous"
variant that also matches the value node. See `evaluate_v2.py` and
`baseline_sosashacl.py`.

## Randomness

The 4,000-observation evaluation subgraph is drawn with a fixed seed (42),
so all reported numbers reproduce exactly. `multiseed_e2.py` repeats the
full seeded-error study with seeds 7 and 123; both reproduce the seed-42
detection counts exactly (`evaluation/multiseed_e2_results.json`).

## External baseline (SOSA-SHACL)

`baseline_sosashacl.py` runs the published SOSA-SHACL suite (KnowWhereGraph
KWG-SHACL) under the same protocol, in two configurations: A as published,
and B with rdf:type materialized over rdfs:subClassOf*. One mechanical
repair was required before pySHACL would accept the published suite: four
`sh:property` blank nodes carry an `sh:or` list but no `sh:path`, which
strict validators reject; the script hoists those `sh:or` lists to the
owning node shape (semantics unchanged, logged at run time).
`punning_fix_baseline.py` adds the condition in which punning-related
violations are excluded from the baseline noise.

## Reasoner check

CMPO v2.0.2 was checked with HermiT (via owlready2, after Turtle to RDF/XML
conversion): the ontology is consistent with zero unsatisfiable classes.

## Runtimes

On a commodity laptop-class container: pipeline about 17 s, evaluation
harness about 69 s, SOSA-SHACL baseline about 3 min. Runtime fields inside
the committed JSON files are from the recorded runs.
