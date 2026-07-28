# Graph-grounded validation questions, v1.0 (2026-07-23)

Twenty one-line validation statements produced by the portal's rule
suggester, then reviewed by a CMP process engineer and a student assistant,
who lightly corrected several wordings. Every statement was afterwards checked
against the released graph: each targeted class has instances and each
constrained property occurs in the data, so no statement can be vacuous. Occurrence counts are from a predicate inventory
of the released graph.

Predictions are written down BEFORE any run (freeze rule). Compare your
results against them; agreement and disagreement are both findings.

## The twenty statements

1. Every CMP observation must have exactly one numeric result value of
   type float.  [25,278 observations]
2. Every CMP observation's observed property must be declared in the CMPO
   parameter hierarchy.  [25,278]
3. Every CMP observation's feature of interest must be an IRI, not a
   literal value.  [25,278]
4. Every CMP observation must be linked to at least one platform (tool or
   chamber).  [50,452 platform links]
5. Every CMP observation must have exactly one raw timestamp and exactly
   one result time.  [25,274 of 25,278 carry them]
6. Every raw timestamp must be non-negative and lie within the campaign's
   recorded time range.  [25,274]
7. Every wafer must have exactly one wafer identifier, and no two wafers
   may share an identifier.  [7 wafers, 7 identifiers]
8. Every polishing step must have a stage label.  [6 steps, 5 labels]
9. Every tool must have a tool identifier.  [7 tools, 4 identifiers]
10. Every chamber must have a chamber number.  [7 chambers, 7 numbers]
11. Every pressure zone of the carrier must state its zone position.
    [6 zones, 6 positions]
12. Every value of a physically dimensioned quantity (pressures, rotation
    speeds, slurry flows, usage counters, removal rates) must be
    non-negative.  [the bulk of the 25,278 observations]
13. The upper control limit must be strictly greater than the lower
    control limit.  [1 SPC limit entity]
14. The control band must lie entirely inside the specification band.
    [1 SPC limit entity with all four limits]
15. A process window's maximum value must be strictly greater than its
    minimum value.  [1 process window]
16. Every lot must have a positive lot size, and the number of wafers
    linked to the lot must not exceed it.  [1 lot, size 25, 2 linked wafers]
17. Every wafer diameter must be one of the standard sizes 100, 150, 200,
    or 300 mm.  [1 diameter assertion]
18. Every edge exclusion width must be non-negative and smaller than half
    the wafer diameter.  [1 edge exclusion, 1 diameter]
19. Groove depth and groove width must be non-negative, and a pad that
    states a groove pattern must also state its pad type.  [1 each of
    grooveDepth, grooveWidth, hasGroovePattern, padType]
20. Every Preston coefficient and every selectivity ratio must be strictly
    positive.  [1 each]

## Pre-registered predictions (write results next to each after the run)

- Q4 FIRES on exactly 20 observations: 16 synthetic completion
  observations genuinely missing their platform link, plus 4 removal-rate
  observations that have no platform BY DESIGN (metrology, not the CMP
  tool). Matches the R6 rule finding of 2026-07-23 night.
- Q5 FIRES on the 4 removal-rate observations (no raw timestamp or result
  time), a by-design property of the removal-rate file.
- Q8 FIRES once: the synthetic metrology step missing its stage label (one
  of the four known E1 violations).
- Q9 FIRES three times: the three synthetic metrology tools missing tool
  identifiers (the other three known E1 violations).
- Q1, Q2, Q3, Q6, Q7, Q10-Q20: expected to PASS with their targets
  actually validated (non-vacuously).
- Any deviation from these predictions is a finding: either a data fact we
  missed or a defect in how the statements were compiled to SHACL.

## How to run without touching the paper

Option A (tests the portal's compiler too): paste the twenty statements
into the portal wizard, freeze the generated SHACL verbatim, validate
against the CMPO v2.0.2 instance file, export the report. Differences
between the report and the predictions then mix data effects with
compilation effects; keep the generated SHACL for the comparison study.

Option B (tests only the data): a reference SHACL suite for these statements,
drafted with AI assistance under author supervision and then executed against
the probe and corrected until every statement fired, validated with pySHACL or
GraphDB against the released KG plus ontology.

Results for both options are in `RESULTS_handwritten_suite.md` (the reference
suite against the released graph) and `README.md` (portal compilation study).
