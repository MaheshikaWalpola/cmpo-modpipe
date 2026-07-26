# Graph-grounded 20-question suite — results, 2026-07-24

Camera-ready extension material. Nothing here touches the submitted paper.
Executed by Claude (agent) on Maheshika's instruction against the released
artifacts; the portal run (Option A) was performed by Maheshika on her
machine the same day.

## Inputs

- `kg/kg_cmpo_v2.0.2.ttl`, SHA-256 `84298e89...b27c5a` — matches the frozen
  verification record byte for byte.
- `ontology/cmpo-v2.0.2.ttl`, SHA-256 `91ef77b1...1ea3ce` — matches.
- Statements and predictions: `graph_grounded_20_questions.md`, frozen
  2026-07-23 before any run.

## Option B: hand-written suite against the released KG

Artifacts: `graph_grounded_shapes.ttl` (SHACL) and
`graph_grounded_sparql_audit.rq` (the same checks as GraphDB-pasteable
SPARQL audits). Execution: all 20 checks ran as SPARQL audits over the
KG + ontology union with the rdfs type closure materialized (rdflib 7.x);
the core-constraint shapes were additionally validated natively with
pySHACL, which reproduced the identical violation sets. The SPARQL-based
checks (Q2, Q6, Q12, Q7b, Q13–Q18) ran as SPARQL only; pySHACL executes
per-focus-node SPARQL constraints too slowly for 25,278 targets in this
environment.

Result: every one of the four predicted violations appeared, and nothing
else fired. All 20 statements validated non-vacuous populations
(25,278 observations, 7 wafers, 6 steps, 7 tools, 7 chambers, 6 zones,
1 lot).

| Check | Predicted | Found | Focus nodes |
|---|---|---|---|
| Q4 platform link | FIRES on exactly 20 | **20** | 16 synthetic completion observations + 4 removal-rate observations |
| Q5 timestamps | FIRES on 4 | **4** | the four removal-rate observations |
| Q8 stage label | FIRES once | **1** | `syn_step_metrology_001` |
| Q9 tool identifier | FIRES 3 times | **3** | `syn_ellips_01`, `syn_profilo_01`, `syn_sem_01` |
| Q1–Q3, Q6, Q7, Q10–Q20 | PASS non-vacuously | **all 0 violations** | populations as above |

The prediction sheet is confirmed in full: 4/4 predicted firings with exact
counts and exact focus nodes, 16/16 predicted passes. The Q4 and Q5 firings
are known by-design properties (metrology observations without CMP platform,
removal-rate file without timestamps); Q8 and Q9 are the four known E1
violations.

## Option A: portal wizard run (performed by Maheshika, 2026-07-24)

Artifacts received: `shacl.rtf` (the portal-generated SHACL) and
`validation_report_20q.pdf` (the portal's own report export — this also
closes freeze open item 1 for this run). Report headline: FAILED,
517 violations, data graph 603,709 triples.

Two findings before any number can be compared:

1. **Different data graph.** The 603,709-triple graph is the portal's own
   generated instance file, not the released `kg_cmpo_v2.0.2.ttl`
   (252,873 triples). Focus nodes such as `inst:parameter_806_B_00019_Tool`
   and `inst:wafer_4215773440` do not exist in the released KG, which
   contains 7 wafers and 7 tools. The portal graph appears to mint a tool
   and wafer node per parameter/row context; its 517 violations therefore
   describe the portal mapping pipeline, not the released graph. The two
   runs are not comparable row by row and must be reported separately.
2. **Defective compiled shapes.** The generated SHACL contains, verbatim:
   a second namespace `cmpo1: <https://tucid/cpmo/>` used for the
   selectivity, Preston, tool-id, and wafer-id shapes, whose target classes
   have no instances in either graph under that namespace (those four
   shapes are vacuous wherever they run); a timestamp range constraint
   `[25, 274]`, which reads as the statement's occurrence note "25,274 of
   25,278 carry them" misparsed as an interval; the platform link checked
   under `sosa:madeOnPlatform` although the property in both ontology and
   data is `cmpo:madeOnPlatform`; the non-existent SHACL keyword
   `sh:uniqueLiteral`; a lot-size SPARQL constraint attached with the
   invalid predicate `sh:SPARQLConstraint` (never executed); and no shapes
   at all for Q13–Q15 (SPC bands, process window), Q18 (edge exclusion),
   or Q19 (groove geometry) — five statements dropped silently.
3. **Internally inconsistent report.** The report lists every shape as
   "Pass" while declaring the overall run FAILED with 517 violations.

## What this supports for the paper

- The released KG conforms to all 20 expert-confirmed, graph-grounded
  statements except the four known and documented by-design or E1 cases,
  under a suite whose predictions were frozen before execution.
- The same 20 statements, pushed through the portal's LLM compiler,
  produced a suite with wrong namespaces, a hallucinated numeric range,
  invalid SHACL keywords, and five silently dropped statements — a
  concrete, quantified instance of the compilation-effects and vacuity
  argument (with the 2026-07-23 16-shape "All Shapes Conform" finding as
  the companion case).
- Both claims must state their data graph explicitly: released KG for
  Option B, portal-generated instance graph for Option A.

## Open questions for Maheshika

1. Confirm which repository/file the portal validated (assumed:
   the GraphDB workspace holding the portal-generated `instance_v2.1.ttl`).
   This also bears on the 269,343 vs 603,709 triple-count clarification in
   FREEZE_STATUS.md.
2. Confirm the 20 statements were pasted verbatim from
   `graph_grounded_20_questions.md` into the wizard, and whether they were
   submitted in one batch or one at a time.
3. `git rev-parse HEAD` in the running portal clone (freeze open item 2)
   so the compiled-shapes finding is pinned to a portal version.

## Provenance

Counts computed 2026-07-24 with rdflib 7.x SPARQL over the hash-verified
released artifacts, cross-checked with pySHACL 0.30/0.25-line for core
constraints; scripts and raw counts: `run_ggq_sparql.py`,
`ggq_optionB_results.json` (session archive), shapes and queries committed
alongside this note. Portal artifacts as received from Maheshika's machine;
the RTF was converted to plain Turtle before inspection. No file in the
frozen folders was modified.
