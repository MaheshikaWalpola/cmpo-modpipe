# Data scope of the released knowledge graph

This note states exactly which source data the released knowledge graph is
built from, and why that scope matches the paper's claims.

## Source dataset

The real process data is the wafer CMP dataset of the 2016 PHM Society Data
Challenge. The full campaign comprises 370 measurement CSV files (training
and test) with roughly 829,000 process records, plus a separate validation
set of 186 files. Removal-rate labels cover 1,981 rows (1,699 distinct
wafers) in training and 424 rows (415 distinct wafers) in test.

## What this repository uses

- `CMP-test-000.csv`: 1,326 process records, 25 columns, 4 wafers.
- `CMP-test-removalrate.csv`: the 4 rows matching those wafers (of 424).
- The synthetic completion table (`synthetic/`): 80 observations plus
  entities for CMPO classes the PHM tool does not log, with a per-class
  coverage declaration; identifiers are visibly synthetic.

That is about 0.16% of the available records. The generated graph contains
252,873 triples with 25,278 observations, of which 25,198 are PHM-derived.

## Why this scope is sufficient for the paper's claims

The seeded-error study (Table 2 of the paper) is deterministic per seeded
node: each mutation either produces a differential violation or it does not,
independently of how many further conforming observations surround it. The
detection table would be identical with 4 wafers or 2,000. The coverage and
feasibility claims are explicitly scoped to the one file pair. Claims the
paper does not make — generality across the campaign, scalability,
statistical robustness — would need more data, and the paper says so.

## What full-campaign ingestion would take

~829,000 records at 19 observations each is roughly 15.8 million
observations, on the order of 150 million triples. The current pipeline
holds the graph in memory (rdflib); the full campaign needs a triple-store
backend. This is planned follow-up work, not a configuration change.

## Gate and CQ coverage at this scope

Tier 1 comprises 5 node shapes constraining 7 property paths; the 5 targeted
classes contain over 99% of all typed instances in the graph. Tier 2
comprises 3 graph-level SPARQL rules. The 12 competency questions were fixed
before any query was written and touch 19 distinct vocabulary terms; empty
answers are reported as boundaries of the current graph, not hidden.
