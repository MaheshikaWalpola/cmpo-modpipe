# CMPO construction history

This note documents how the CMPO ontology and its companion artifacts were
built. It is the "construction history" referred to in the SemIIM 2026 paper
(Sections 1, 3, and 7 and the Declaration on Generative AI).

## How CMPO was drafted

CMPO was drafted in a structured dialogue between the first author and a large
language model, in three stages. At every stage the model produced the draft
and the first author reviewed it, checked class comments against fab
terminology, and removed or corrected mistaken proposals.

**Stage 1 — BFO-aligned draft.** The first attempt used Basic Formal Ontology
(BFO) as the top-level ontology. The model produced a draft organized around
CMP as the central concept. This structure did not fit the data: the
measurements in the source files describe wafers and process runs, not the
abstract process.

**Stage 2 — restructuring around the process and its wafers.** The model was
asked to rebuild the ontology with the wafer as the main element of the CMP
step, rather than building everything around the CMP concept itself.

**Stage 3 — SOSA/SSN rebuild (the released version).** The model was asked to
rebuild the ontology on the W3C SOSA/SSN observation vocabulary. This produced
the schema that the prototype portal used and that, after further revision,
became CMPO v2.0.1 as released here: every recorded value is a
sosa:Observation specialization, parameter classes sit under cmpo:CMPParameter,
and units are individuals aligned to QUDT.

## Data grounding

The class candidates came from three sources: the column inventory of the 2016
PHM Data Challenge CMP dataset (whose 28 column headers are preserved as
skos:altLabel on the matching terms), the CMP process literature (tool anatomy,
consumables, defects, parameter families), and the SOSA/SSN pattern.

## The synthetic completion sample

The PHM columns exercise only part of the ontology. To demonstrate coverage of
the remaining classes, a Python script compared the CMPO class inventory
against the PHM column names, identified the classes no column covers, and
generated a new CSV whose columns are those missing classes, filled with
synthetic values and visibly synthetic identifiers. Because no domain experts
were available, the generated sample was quality-checked with AI assistance;
expert review is planned. The sample demonstrates ontology coverage only and
is not physically representative CMP process data (see the paper's
Limitations).

## Responsibility

All artifacts were reviewed and revised by the authors, who take full
responsibility for their content. A controlled comparison of this LLM-assisted
construction process against manual ontology engineering remains planned
future work.
