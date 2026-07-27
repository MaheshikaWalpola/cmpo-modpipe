# The twenty statements against the released graph

This note records what the twenty validation statements of `questions_20.md`
report when they are compiled by hand rather than by the portal, and executed
against the released artifacts: `kg/kg_cmpo_v2.1.ttl` and
`ontology/schema_v2.1.ttl`, 279,735 triples in union with the
`rdfs:subClassOf` type closure materialised.

It is the control condition for the compilation study in `README.md`. The
statements are the same; only the compiler changes.

## Freeze rule

Every statement was checked against the graph before being written, so that no
statement could be vacuous for lack of data: `questions_20.md` records the
occurrence count of each targeted class and constrained property. Predictions
for which statements would fire, on how many nodes, and on which nodes were
written down before any run. Agreement and disagreement are both results.

## Predictions

| Statement | Predicted | Reason |
|---|---|---|
| Q4 platform link | fires on exactly 20 | 16 synthetic completion observations genuinely missing the link, plus 4 removal-rate observations that have no platform by design (metrology, not the CMP tool) |
| Q5 timestamps | fires on 4 | the four removal-rate observations; the removal-rate file carries no timestamps |
| Q8 stage label | fires once | the synthetic metrology step, one of the four E1 violations |
| Q9 tool identifier | fires 3 times | the three synthetic metrology tools, the other three E1 violations |
| Q1–Q3, Q6, Q7, Q10–Q20 | pass, non-vacuously | populations as recorded in `questions_20.md` |

## Result

| Check | Predicted | Found | Focus nodes |
|---|---|---|---|
| Q4 platform link | 20 | **20** | 16 synthetic completion observations + 4 removal-rate observations |
| Q5 timestamps | 4 | **4** | the four removal-rate observations |
| Q8 stage label | 1 | **1** | `syn_step_metrology_001` |
| Q9 tool identifier | 3 | **3** | `syn_ellips_01`, `syn_profilo_01`, `syn_sem_01` |
| all other statements | 0 | **0** | — |

Four of four predicted firings at the exact predicted counts and on the exact
predicted nodes; sixteen of sixteen predicted passes. The Q4 and Q5 firings are
known by-design properties of the sources; Q8 and Q9 are the four violations
the paper's E1 already reports.

Reproduce with `portal_study/sparql_audit.rq` (each query returns the violating
nodes; an empty result means the statement holds), or with
`portal_study/check_shapes.py` for the injection test, which confirms that all
twenty statements enforce under this suite and under `shapes_corrected.ttl`.

## One practical note

`sparql_audit.rq` uses `rdf:type/rdfs:subClassOf*` property paths, so it needs
no inference ruleset. If the repository *also* materialises the type closure —
as the portal does before validating — a node reaches its ancestor class by
several routes at once, and the path yields one solution per route. Without
`DISTINCT`, a wafer with one identifier is then counted as having three, and a
correct graph reports violations. Every query here uses `DISTINCT` and
`COUNT(DISTINCT ...)`, so the counts above are identical with and without
materialisation. The mistake is easy to make and it fails in the direction that
manufactures violations rather than hiding them, which is the safer direction
but still wrong.
