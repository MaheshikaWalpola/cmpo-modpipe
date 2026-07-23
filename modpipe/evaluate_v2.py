#!/usr/bin/env python3
"""ModPipe evaluation on the CMPO v2.0.1 knowledge graph.

E1 Gate run: validate the full generated KG (union with the ontology so
   rdfs:subClassOf* paths resolve) against tier-1 (core) and tier-1+2
   (core + SPARQL) shape suites.
E2 Seeded-error study: 8 externally grounded error classes injected into
   a stratified subgraph; per-class detection by tier-1 vs tier-1+2.
E3 Competency questions (literature-derived, SOSA vocabulary) executed
   as SPARQL; answerability funnel.
Also computes ontology-coverage statistics of the generated KG.
Every number is computed; seed fixed for reproducibility.
"""
import json
import random
import time
from collections import Counter

import pandas as pd
from pyshacl import validate
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD

CMPO = Namespace("https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
INST = Namespace("https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo/instance#")
RNG = random.Random(42)
R = {}


import os as _os
def _find(*cands):
    for c in cands:
        if _os.path.exists(c): return c
    raise FileNotFoundError("none of: " + ", ".join(cands) + " -- run from the repository root")

def load():
    ont = Graph(); ont.parse(_find("ontology/cmpo-v2.0.2.ttl", "cmpo-v2.0.2.ttl"), format="turtle")
    kg = Graph(); kg.parse(_find("out/kg_unvalidated.ttl", "kg/kg_cmpo_v2.0.2.ttl", "kg_cmpo_v202.ttl"), format="turtle")
    core = Graph(); core.parse(_find("shapes/shapes_core.ttl", "shapes_core.ttl"), format="turtle")
    both = Graph(); both.parse(_find("shapes/shapes_core.ttl", "shapes_core.ttl"), format="turtle"); both.parse(_find("shapes/shapes_sparql.ttl", "shapes_sparql.ttl"), format="turtle")
    return ont, kg, core, both


def union(kg, ont):
    u = Graph()
    for t in kg: u.add(t)
    for t in ont: u.add(t)
    return u


TIER2_QUERIES = {
    "R1_negative_quantity": """
        PREFIX cmpo: <https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?this WHERE { ?this sosa:observedProperty ?p ; sosa:hasSimpleResult ?v .
            ?p rdfs:subClassOf* ?root .
            VALUES ?root { cmpo:Pressure cmpo:Velocity cmpo:SlurryFlowRate cmpo:UsageParameter cmpo:MaterialRemovalRate }
            FILTER (isNumeric(?v) && ?v < 0) }""",
    "R2_undeclared_property": """
        PREFIX cmpo: <https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#>
        PREFIX sosa: <http://www.w3.org/ns/sosa/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?this WHERE { ?this sosa:observedProperty ?p .
            FILTER NOT EXISTS { ?p rdfs:subClassOf* cmpo:CMPParameter } }""",
    "R3_duplicate_wafer_id": """
        PREFIX cmpo: <https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#>
        SELECT ?this WHERE { ?this cmpo:hasWaferId ?id . ?other cmpo:hasWaferId ?id .
            FILTER (?other != ?this) }""",
}


def tier2_audit(data):
    """Run the tier-2 semantic rules as direct SPARQL audit queries.
    Same semantics as the SHACL-SPARQL constraints in shapes_sparql.ttl,
    executed once per rule instead of once per focus node."""
    focus = set()
    counts = {}
    for name, q in TIER2_QUERIES.items():
        rows = list(data.query(q))
        counts[name] = len(rows)
        for r in rows:
            focus.add((str(r[0]), name, "SPARQLRule"))
    return counts, focus


def run_val(data, shapes, advanced=False):
    conforms, _, rt = validate(data, shacl_graph=shapes, inference="none")
    n = rt.count("Constraint Violation")
    focus = set()
    for block in rt.split("Constraint Violation in ")[1:]:
        comp = block.split(" ")[0]
        fn, path = "", ""
        for line in block.split("\n"):
            if "Focus Node:" in line: fn = line.split("Focus Node:")[1].strip()
            if "Result Path:" in line: path = line.split("Result Path:")[1].strip()
        focus.add((fn, path, comp))
    return conforms, n, focus


def experiment_1(ont, kg, core, both):
    print("== E1: validation gate on full KG ==")
    u = union(kg, ont)
    out = {"kg_triples": len(kg), "union_triples": len(u)}
    c1, n1, _ = run_val(u, core)
    print(f"  tier-1 core: conforms={c1}, violations={n1}")
    t2counts, _ = tier2_audit(u)
    n2 = n1 + sum(t2counts.values())
    print(f"  tier-2 audit rules: {t2counts}; tier-1+2 total violations={n2}")
    out["tier1"] = {"conforms": c1, "violations": n1}
    out["tier12"] = {"violations": n2, "tier2_rule_counts": t2counts}
    # coverage of the ontology by the generated KG
    classes_used = set(kg.objects(None, RDF.type))
    props_observed = set(kg.objects(None, SOSA.observedProperty))
    out["distinct_instantiated_classes"] = len([c for c in classes_used if str(c).startswith(str(CMPO))])
    out["distinct_observed_properties"] = len(props_observed)
    out["observations"] = len(set(kg.subjects(RDF.type, CMPO.CMPObservation)))
    out["wafers"] = len(set(kg.subjects(RDF.type, CMPO.Wafer)))
    print(f"  observations={out['observations']}, wafers={out['wafers']}, "
          f"instantiated classes={out['distinct_instantiated_classes']}, "
          f"observed properties={out['distinct_observed_properties']}")
    return out


def build_subgraph(kg, ont, n_obs=4000):
    obs = sorted(set(kg.subjects(RDF.type, CMPO.CMPObservation)), key=str)
    RNG.shuffle(obs)
    keep = set(obs[:n_obs])
    g = Graph()
    ctx = set()
    for o in keep:
        for p, v in kg.predicate_objects(o):
            g.add((o, p, v))
            if isinstance(v, URIRef): ctx.add(v)
    for c in ctx:
        for p, v in kg.predicate_objects(c):
            g.add((c, p, v))
    for t in ont: g.add(t)
    return g


PRESSURE_ROOTS = None

def pressure_obs(g, k):
    q = """PREFIX cmpo: <https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#>
           PREFIX sosa: <http://www.w3.org/ns/sosa/>
           PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
           SELECT ?o ?v WHERE { ?o sosa:observedProperty ?p ; sosa:hasSimpleResult ?v .
                                ?p rdfs:subClassOf* cmpo:Pressure . FILTER(?v >= 0) }"""
    rows = [(r[0], r[1]) for r in g.query(q)]
    RNG.shuffle(rows)
    return rows[:k]


def seed(g, op, k=50):
    removed, added, seeded = [], [], set()
    def rm(t): removed.append(t); Graph.remove(g, t)
    def ad(t): added.append(t); Graph.add(g, t)
    all_obs = [s for s in g.subjects(RDF.type, CMPO.CMPObservation)
               if (s, SOSA.hasSimpleResult, None) in g]
    RNG.shuffle(all_obs)
    if op == "T1_missing_value":
        for s in all_obs[:k]:
            for v in list(g.objects(s, SOSA.hasSimpleResult)): rm((s, SOSA.hasSimpleResult, v))
            seeded.add(s)
    elif op == "T2_datatype":
        for s in all_obs[:k]:
            for v in list(g.objects(s, SOSA.hasSimpleResult)):
                rm((s, SOSA.hasSimpleResult, v)); ad((s, SOSA.hasSimpleResult, Literal("N/A")))
            seeded.add(s)
    elif op == "T3_negative_value":
        for s, v in pressure_obs(g, k):
            rm((s, SOSA.hasSimpleResult, v))
            ad((s, SOSA.hasSimpleResult, Literal(-(abs(float(v)) + 1.0), datatype=XSD.float)))
            seeded.add(s)
    elif op == "T4_dangling_foi":
        for s in all_obs[:k]:
            for v in list(g.objects(s, SOSA.hasFeatureOfInterest)): rm((s, SOSA.hasFeatureOfInterest, v))
            ad((s, SOSA.hasFeatureOfInterest, Literal("missing_wafer")))
            seeded.add(s)
    elif op == "T5_plausible_swap":
        rows = pressure_obs(g, 2 * k)
        for (a, va), (b, vb) in zip(rows[:k], rows[k:2 * k]):
            rm((a, SOSA.hasSimpleResult, va)); ad((a, SOSA.hasSimpleResult, vb))
            rm((b, SOSA.hasSimpleResult, vb)); ad((b, SOSA.hasSimpleResult, va))
            seeded.add(a); seeded.add(b)
    elif op == "T6_undeclared_property":
        for s in all_obs[:k]:
            for v in list(g.objects(s, SOSA.observedProperty)): rm((s, SOSA.observedProperty, v))
            ad((s, SOSA.observedProperty, CMPO.CentreAirBagPresure))  # typo IRI, not declared
            seeded.add(s)
    elif op == "T7_unit_scale":
        for s, v in pressure_obs(g, k):
            rm((s, SOSA.hasSimpleResult, v))
            ad((s, SOSA.hasSimpleResult, Literal(float(v) * 6.895, datatype=XSD.float)))
            seeded.add(s)
    elif op == "T8_duplicate_wafer":
        wafers = [w for w in g.subjects(RDF.type, CMPO.Wafer)][:k]
        for w in wafers:
            dup = URIRef(str(w) + "_dup")
            wid = next(iter(g.objects(w, CMPO.hasWaferId)), None)
            ad((dup, RDF.type, CMPO.Wafer))
            if wid is not None: ad((dup, CMPO.hasWaferId, wid))
            seeded.add(dup)
    return (removed, added), seeded


def experiment_2(sub, core, both):
    print("== E2: seeded errors (k=50, seed=42) ==")
    base = {}
    _, n0, f0 = run_val(sub, core)
    _, f0b = tier2_audit(sub)
    base["tier1"] = f0
    base["tier12"] = f0 | f0b
    print(f"  clean baseline: tier1={n0} violations, tier2 extra={len(f0b)}")
    out = {}
    for op in ["T1_missing_value", "T2_datatype", "T3_negative_value", "T4_dangling_foi",
               "T5_plausible_swap", "T6_undeclared_property", "T7_unit_scale", "T8_duplicate_wafer"]:
        undo, seeded = seed(sub, op)
        row = {"seeded": len(seeded)}
        _, n, focus1 = run_val(sub, core)
        _, focus2 = tier2_audit(sub)
        for lbl, focus in [("tier1", focus1), ("tier12", focus1 | focus2)]:
            new = focus - base[lbl]
            det = sum(1 for s in seeded if any(str(s).rsplit('#', 1)[-1] in fn for fn, _, _ in new))
            row[lbl] = det
        removed, added = undo
        for t in added: Graph.remove(sub, t)
        for t in removed: Graph.add(sub, t)
        out[op] = row
        print(f"  {op}: seeded={row['seeded']} tier1={row['tier1']} tier12={row['tier12']}")
    return out


CQS = [
    ("CQ1", "Which process parameters were recorded for a given wafer?",
     "PHM16 documentation",
     """SELECT (COUNT(DISTINCT ?p) AS ?n) WHERE {
        ?o sosa:hasFeatureOfInterest ?w ; sosa:observedProperty ?p .
        ?w cmpo:hasWaferId ?id . FILTER(str(?id)="373446766") }"""),
    ("CQ2", "What was the average removal rate of a wafer per polishing step?",
     "PHM16 target variable",
     """SELECT ?step ?v WHERE {
        ?o sosa:observedProperty cmpo:AverageRemovalRate ;
           sosa:hasFeatureOfInterest ?w ; cmpo:duringStep ?step ; sosa:hasSimpleResult ?v .
        ?w cmpo:hasWaferId ?id . FILTER(str(?id)="373446766") } LIMIT 5"""),
    ("CQ3", "Which carrier-head pressure zones are modeled, with which canonical unit?",
     "Multi-zone head pressure (Luo & Dornfeld 2004)",
     """SELECT ?zone ?u WHERE {
        ?zone rdfs:subClassOf+ cmpo:Pressure .
        OPTIONAL { ?zone cmpo:canonicalUnit ?own }
        OPTIONAL { cmpo:Pressure cmpo:canonicalUnit ?fam }
        BIND(COALESCE(?own, ?fam) AS ?u) } LIMIT 20"""),
    ("CQ4", "What conditioning-related usage counters accompany observations of a wafer?",
     "Pad conditioning literature",
     """SELECT DISTINCT ?p WHERE {
        ?o sosa:hasFeatureOfInterest ?w ; sosa:observedProperty ?p .
        ?p rdfs:subClassOf* cmpo:UsageParameter .
        ?w cmpo:hasWaferId ?id . FILTER(str(?id)="373446766") } LIMIT 10"""),
    ("CQ5", "On which tools and chambers were observations made?",
     "PHM16 dataset fields",
     """SELECT DISTINCT ?plat WHERE { ?o a cmpo:CMPObservation ; cmpo:madeOnPlatform ?plat . } LIMIT 12"""),
    ("CQ6", "How many observations share the polishing step of a given wafer and stage?",
     "Run-to-run comparability (Winkler et al. 2025)",
     """SELECT (COUNT(?o) AS ?n) WHERE {
        ?o cmpo:duringStep ?st . ?st cmpo:stageLabel ?l . FILTER(str(?l)="A") }"""),
    ("CQ7", "For which wafers is a removal-rate observation missing?",
     "Completeness probe; PHM16 has unlabeled runs",
     """SELECT (COUNT(DISTINCT ?w) AS ?n) WHERE {
        ?w a cmpo:Wafer .
        FILTER NOT EXISTS { ?o sosa:observedProperty cmpo:AverageRemovalRate ;
                               sosa:hasFeatureOfInterest ?w . } }"""),
    ("CQ8", "Which slurry chemistry parameters are represented, and which have data?",
     "Slurry chemistry as MRR driver",
     """SELECT ?p (COUNT(?o) AS ?n) WHERE {
        ?p rdfs:subClassOf* cmpo:SlurryChemistryParameter .
        OPTIONAL { ?o sosa:observedProperty ?p } } GROUP BY ?p LIMIT 20"""),
    ("CQ9", "What is the timestamp range of the recorded observations?",
     "Traceability",
     """SELECT (MIN(?t) AS ?tmin) (MAX(?t) AS ?tmax) WHERE {
        ?o a cmpo:CMPObservation ; cmpo:rawTimestamp ?t . }"""),
    ("CQ10", "Which lots exist and which wafers belong to them?",
     "Fab traceability practice",
     """SELECT ?lot ?w WHERE { ?lot a cmpo:Lot . OPTIONAL { ?w cmpo:isPartOfLot ?lot } } LIMIT 5"""),
    ("CQ11", "Which contact pressure values were derived for the Preston model?",
     "Preston equation P-term (synthetic completion)",
     """SELECT ?o ?v WHERE {
        ?o sosa:observedProperty cmpo:ContactPressure ; sosa:hasSimpleResult ?v . } LIMIT 5"""),
    ("CQ12", "Which pad or conditioning entities are described, with which properties?",
     "Consumable state (conditioning literature)",
     """SELECT DISTINCT ?e ?cls WHERE {
        ?e a ?cls . ?cls rdfs:subClassOf* cmpo:Pad . } LIMIT 10"""),
]


def experiment_3(kg, ont):
    print("== E3: competency questions ==")
    u = union(kg, ont)
    out = []
    for cqid, text, prov, q in CQS:
        full = ("PREFIX cmpo: <https://vsr.informatik.tu-chemnitz.de/ontologies/cmpo#> "
                "PREFIX sosa: <http://www.w3.org/ns/sosa/> "
                "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> " + q)
        try:
            rows = list(u.query(full))
            nonempty = any(any(v is not None for v in r) for r in rows)
            out.append({"id": cqid, "q": text, "prov": prov, "rows": len(rows),
                        "answered": len(rows) > 0,
                        "sample": [str(v)[:60] for v in rows[0]] if rows else []})
            print(f"  {cqid}: rows={len(rows)} sample={[str(v)[:40] for v in rows[0]] if rows else []}")
        except Exception as e:
            out.append({"id": cqid, "q": text, "prov": prov, "error": str(e)[:100]})
            print(f"  {cqid}: FAILED {e}")
    return out


def main():
    t0 = time.time()
    ont, kg, core, both = load()
    R["E1"] = experiment_1(ont, kg, core, both)
    sub = build_subgraph(kg, ont)
    print(f"subgraph for E2: {len(sub)} triples (incl. ontology)")
    R["E2"] = experiment_2(sub, core, both)
    R["E3"] = experiment_3(kg, ont)
    R["runtime_s"] = round(time.time() - t0, 1)
    json.dump(R, open("out/results_v2.json", "w"), indent=2, default=str)
    print(f"done in {R['runtime_s']}s -> out/results_v2.json")


if __name__ == "__main__":
    main()
