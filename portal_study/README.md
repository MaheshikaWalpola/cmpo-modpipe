# portal_study/ — what an LLM compiler does to a validation gate

This folder holds the material for Section 6.5 (E4) of the SemIIM 2026 paper.
It answers one question: when twenty plain-English validation statements are
compiled into SHACL by a language model, how many of them end up actually
enforcing anything?

The answer, measured three times on the same twenty statements, is 11, 13 and
13 of 20 — runs 2 and 3 agreeing, run 1 failing on a different set — and under a SHACL engine in advanced mode, twice it is zero,
because a single malformed shape aborts the whole suite.

## Why an injection test and not `--metashacl`

Every defect found here produces well-formed SHACL. A shape can target a class
with no instances, use a property path that never occurs, or carry a constraint
keyword the engine does not recognise and silently ignores. `pyshacl
--metashacl` accepts all of these, and a validation run over clean data returns
the same green report it would return for a correct suite.

The only reliable check is to build a graph that violates every statement on
purpose and confirm that each shape fires on its own violation. That is
`probe20.ttl`: one deliberately violating node per statement, plus a control
node that is correct and must not fire.

## Files

| File | What it is |
|---|---|
| `questions_20.md` | The twenty validation statements, with the occurrence count of every targeted class and constrained property in the released graph, so that no statement can be vacuous for lack of data. Frozen 2026-07-23, before any run. |
| `runs/run1_portal_generated.ttl` | Portal output, run 1, verbatim |
| `runs/run2_portal_generated.ttl` | Portal output, run 2, verbatim |
| `runs/run3_portal_generated.ttl` | Portal output, run 3, verbatim |
| `shapes_corrected.ttl` | The same twenty statements after repair of the defects listed below |
| `shapes_handwritten.ttl` | An independent reference suite for the same twenty statements, drafted without reference to the portal output. The filename is historical: like the portal's suites it was machine-drafted, and what distinguishes it is that it was executed against the probe and corrected until every statement fired |
| `sparql_audit.rq` | The same twenty checks as standalone SPARQL, pasteable into GraphDB |
| `probe20.ttl` | The injection probe |
| `check_shapes.py` | The harness; reproduces every number below |
| `results.json` | Its output |
| `RESULTS_handwritten_suite.md` | Results of that reference suite against the released graph |
| `PROVENANCE.md` | Which repository and commit each artifact comes from |

## Reproducing

```bash
pip install -r requirements.txt
python3 portal_study/check_shapes.py
```

## Result

| Suite | Node shapes | Enforced (advanced off) | Enforced (advanced on) | Inert | Absent | False positives |
|---|---|---|---|---|---|---|
| Portal run 1 | 16 | 11 / 20 | 11 / 20 | 5, 6, 7, 13, 14 | 15, 16, 18, 19 | 1 |
| Portal run 2 | 17 | 13 / 20 | suite rejected | 7, 14, 15, 16 | 6, 13, 18 | 1 |
| Portal run 3 | 17 | 13 / 20 | suite rejected | 7, 14, 15, 16 | 6, 13, 18 | 1 |
| Repaired, execution-checked | 22 | 20 / 20 | 20 / 20 | — | — | 0 |
| Independent, execution-checked | 23 | 20 / 20 | 20 / 20 | — | — | 0 |

*Enforced* means the shape written for a statement fired on that statement's
own probe node. *Inert* means a shape exists but fired on nothing. *Absent*
means no shape was emitted for that statement at all.

**All five suites were machine-drafted.** The last two are not a human control:
they were produced with AI assistance under author supervision, then run
against `probe20.ttl` and corrected until all twenty statements fired. What
separates them from the three portal runs is that execution check, not their
authorship. The twenty English statements are a different matter — those were
reviewed and corrected by a CMP process engineer and a student assistant, and
neither reviewer saw any generated SHACL or the probe.

## The defects, and why each one is invisible

**Statements dropped in the merge.** The generator makes one model call per
statement and merges the results by parsing each fragment into one graph. A
fragment that does not parse is written to the server console and discarded;
the merged suite simply does not contain it. Three or four statements
disappeared this way per run: statements 15, 16, 18 and 19 in run 1, and
statements 6, 13 and 18 in runs 2 and 3, which coincided. The web
interface marks a statement green when the model call returns, not when its
output parses, so the user sees twenty green ticks and receives sixteen or
seventeen shapes.

**Constraint keywords that do not exist.** Run 3 expresses the uniqueness half
of statement 7 as `sh:uniqueConstraints [ sh:path cmpo:hasWaferId ;
sh:uniqueTrue true ]`. Neither term is in the SHACL vocabulary. The engine
ignores unrecognised vocabulary, so the probe's two wafers sharing one
identifier pass clean. An earlier run used `sh:uniqueLiteral`, equally
non-existent.

**Comparisons compiled to type checks.** Statements 14 and 15 state
relationships between two values — a control band inside a specification band,
a window maximum above its minimum. Both compile to nothing but
`sh:datatype xsd:float` on each endpoint. The probe's inverted SPC limits
(upper 10.0, lower 90.0) and inverted window (max 1.0, min 9.0) pass.

**A rule declaration that voids the suite.** Statement 16 is attached with
`sh:rule [ a sh:SPARQLConstraint ]`. `sh:rule` requires a `sh:TripleRule` or a
`sh:SPARQLRule`, and the SPARQL inside contains `FILTER(?waferCount > $this
cmpo:lotSize)`, which is not valid SPARQL. In advanced mode the engine rejects
the entire shapes graph over this one shape: all seventeen shapes stop
enforcing, not just this one. The portal never observes this because it calls
the validator with advanced mode off, which ignores rule declarations entirely.

**Strictness lost.** Statement 20 says "strictly positive" and compiles to
`sh:minInclusive 0.0`. The probe's Preston coefficient of exactly `0.0` passes.

**A range check that fires on everything.** Statement 2 compiles to
`sh:class cmpo:CMPParameter` on `sosa:observedProperty`. CMPO's parameter
classes are punned: they appear in individual position but are subclasses of
`cmpo:CMPParameter`, not instances of it. The constraint therefore fails on
every observation in the graph, corrupted or not. It produces violations, so it
looks alive; it distinguishes nothing.

**Over-broad targeting.** Statement 12 restricts physically dimensioned
quantities to non-negative values, and compiles to a constraint on every
`cmpo:CMPObservation`. The probe's negative zeta potential — a legitimately
negative measurement — is flagged. This is the one false positive in each
portal run.

## The reporting defect

The portal's own validation report, exported for a run of the corrected suite
over a 796,900-triple graph, states on one page:

> Rules Tested: 22 · Pass Rate: 100.0% · "All 22 validation rules passed
> successfully (100% compliance)" · "No failed test cases!"

and

> Violation Count: 52,028 · Affected Focus-Nodes: 51,604 · Gate Decision: Fail

Both are produced by the same run. The cause is an attribution gap, and it
reproduces exactly: applying the portal's pass-counting logic to this folder's
probe run gives 18 shapes reported, 18 scored as passed, a 100.0% pass rate,
21 violations, and `conforms = False`.

The validator reports `sh:sourceShape` as the *property* shape, which in
generated output is an anonymous blank node. The report builds its rule list
from node shapes and from subjects of `sh:targetClass`, so no blank node ever
matches an entry in that list; every named rule keeps a failure count of zero
and is scored as passed. The violations are counted in one place and attributed
in another. `check_shapes.py` resolves the property shape back to its owning
node shape, which is the fix.

## Scope

These are compilation effects, measured on one generator. They are not a claim
about language models in general, and the model behind the portal's inference
endpoint is selected by an environment variable that was not recorded per run.
What the study does show is that the failure is silent at every stage: the
interface reports success, the suite loads, validation returns a report, and
the report says 100% compliance. Nothing in the SHACL machinery distinguishes a
suite that checks twenty things from one that checks eleven.
